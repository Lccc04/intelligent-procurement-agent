"""
Planning 工具 - write_todos
创建并管理结构化任务清单，用于规划复杂目标
"""
from langchain_core.tools import tool
from typing import List, Dict, Any, Literal
import json


# 全局任务清单存储（实际项目中存在 LangGraph State 里）
_todos_store: Dict[str, List[Dict[str, Any]]] = {}


@tool
def write_todos(
    todos: List[Dict[str, Any]],
    merge: bool = True,
    thread_id: str = "default"
) -> str:
    """
    创建并管理一个结构化的任务清单，用于规划复杂目标。
    可以一次性创建完整列表，或者增量更新现有列表。
    每一步执行完成后必须更新对应任务的状态。

    Args:
        todos: 要应用的任务列表。如果提供空数组则清空所有任务。
               每个任务包含：id（唯一标识）、content（任务描述）、
               status（pending/in_progress/completed/cancelled）、
               depends_on（前置依赖的任务ID列表，可选）
        merge: 是否与现有列表合并（默认True），否则全量替换
        thread_id: 会话ID，用于隔离不同会话的任务清单

    Returns:
        更新后的任务清单 JSON 字符串
    """
    current = _todos_store.get(thread_id, [])

    if not todos:
        # 清空任务
        _todos_store[thread_id] = []
        return json.dumps({"code": 0, "message": "任务清单已清空", "todos": []}, ensure_ascii=False, indent=2)

    if merge and current:
        # 合并模式：按 id 更新，新增的追加
        current_map = {t["id"]: t for t in current}
        for new_todo in todos:
            todo_id = new_todo.get("id")
            if todo_id and todo_id in current_map:
                # 更新已有任务
                current_map[todo_id].update(new_todo)
            else:
                # 新增任务
                current.append(new_todo)
        _todos_store[thread_id] = current
    else:
        # 全量替换
        _todos_store[thread_id] = todos

    result = _todos_store[thread_id]

    # 统计状态
    stats = {
        "total": len(result),
        "pending": len([t for t in result if t.get("status") == "pending"]),
        "in_progress": len([t for t in result if t.get("status") == "in_progress"]),
        "completed": len([t for t in result if t.get("status") == "completed"]),
        "cancelled": len([t for t in result if t.get("status") == "cancelled"]),
    }

    return json.dumps({
        "code": 0,
        "message": "任务清单已更新",
        "stats": stats,
        "todos": result
    }, ensure_ascii=False, indent=2)


def get_todos(thread_id: str = "default") -> List[Dict[str, Any]]:
    """获取指定会话的任务清单"""
    return _todos_store.get(thread_id, [])


def clear_todos(thread_id: str = "default"):
    """清空指定会话的任务清单"""
    if thread_id in _todos_store:
        del _todos_store[thread_id]
