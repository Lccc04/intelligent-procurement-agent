"""
异步子 Agent 工具
start_async_task - 启动后台异步任务
check_async_task - 查询异步任务状态
"""
from langchain_core.tools import tool
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor
import uuid
import json
import time

from agent.tools.mock_tools import PARTS, SUPPLIERS


# 全局异步任务存储
_async_tasks: Dict[str, Dict[str, Any]] = {}
_task_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="procurement-task")


@tool
def start_async_task(task_type: str, instruction: str, user_id: str = "default") -> str:
    """
    启动异步后台任务，立即返回 task_id。
    用于耗时较长的采购分析任务，不阻塞主对话。

    Args:
        task_type: 任务类型，如 "procurement_analysis"
        instruction: 详细的任务指令，描述分析需求
        user_id: 用户ID

    Returns:
        包含 task_id 和状态的 JSON 字符串
    """
    task_id = f"task_{uuid.uuid4().hex[:8]}"

    # 初始化任务
    _async_tasks[task_id] = {
        "task_id": task_id,
        "task_type": task_type,
        "instruction": instruction,
        "user_id": user_id,
        "status": "running",
        "result": None,
        "created_at": time.time(),
        "completed_at": None,
    }

    # 工具可能由 LangGraph 放到线程池中执行，因此不能依赖当前线程存在
    # asyncio event loop；使用独立线程池提交后台任务，保持调用立即返回。
    _task_executor.submit(_run_async_task, task_id, instruction)

    return json.dumps({
        "code": 0,
        "message": "异步任务已启动",
        "task_id": task_id,
        "status": "running",
        "hint": "任务正在后台执行，您可以继续对话。使用 check_async_task 查询状态，或等待前端自动轮询。"
    }, ensure_ascii=False, indent=2)


@tool
def check_async_task(task_id: str) -> str:
    """
    查询异步任务状态和结果。

    Args:
        task_id: 任务ID（由 start_async_task 返回）

    Returns:
        任务状态和结果的 JSON 字符串
    """
    task = _async_tasks.get(task_id)
    if not task:
        return json.dumps({
            "code": -1,
            "message": "任务不存在",
            "task_id": task_id
        }, ensure_ascii=False)

    return json.dumps({
        "code": 0,
        "task_id": task["task_id"],
        "status": task["status"],
        "task_type": task["task_type"],
        "created_at": task["created_at"],
        "completed_at": task["completed_at"],
        "result": task["result"],
    }, ensure_ascii=False, indent=2)


def _run_async_task(task_id: str, instruction: str):
    """
    后台执行异步任务（模拟实现）
    实际项目中这里会调用采购分析子 Agent
    """
    try:
        # 模拟分析过程（实际项目中这里是真正的 Agent 执行）
        time.sleep(3)  # 模拟耗时

        brake_parts = [p for p in PARTS if p["category"] == "制动系统"]
        supplier_map = {s["id"]: s for s in SUPPLIERS}
        price_rows = "\n".join(
            f"| {p['id']} | {p['name']} | {p['spec']} | {p['unit']} | {p['price']:.2f} | "
            f"{p['stock']} | {supplier_map.get(p['supplier_id'], {}).get('name', p['supplier_id'])} |"
            for p in brake_parts
        )
        avg_price = sum(p["price"] for p in brake_parts) / len(brake_parts) if brake_parts else 0
        max_price_part = max(brake_parts, key=lambda p: p["price"]) if brake_parts else None
        min_price_part = min(brake_parts, key=lambda p: p["price"]) if brake_parts else None
        warning_parts = [p for p in PARTS if p["stock"] <= 100]

        conclusions = []
        if brake_parts:
            conclusions.append(f"制动系统共有 {len(brake_parts)} 个演示物料，当前平均单价为 {avg_price:.2f} CNY。")
        if max_price_part and min_price_part:
            conclusions.append(
                f"当前单价最高的是 {max_price_part['name']}（{max_price_part['price']:.2f} CNY），"
                f"最低的是 {min_price_part['name']}（{min_price_part['price']:.2f} CNY）。"
            )
        conclusions.append("当前 Mock ERP 只提供单时点价格快照，没有历史价格序列，因此不能判断真实上涨、下降或稳定趋势。")

        conclusion_text = "\n".join(f"{idx}. {item}" for idx, item in enumerate(conclusions, start=1))
        price_chart_data = {p["name"]: p["price"] for p in brake_parts}
        stock_chart_data = {
            "充足": len([p for p in PARTS if p["stock"] > 100]),
            "预警": len(warning_parts),
        }

        # 生成模拟分析结果。报告必须标注数据边界，避免把快照写成趋势。
        result = {
            "report": f"""# 采购分析报告

## 分析任务
{instruction}

## 数据来源
- 来源：mock_erp 演示数据
- 范围：当前价格/库存快照
- 限制：未提供历史价格、采购批次价格或外部市场报价，不能据此断言价格趋势

## 当前价格对比
| 物料ID | 物料名称 | 规格 | 单位 | 当前单价(CNY) | 库存 | 供应商 |
|---|---|---|---|---:|---:|---|
{price_rows}

## 可确认结论
{conclusion_text}

## 需要补充的数据
- 至少两个以上时间点的采购价格或报价记录
- 供应商历史报价单或订单明细
- 质量、交期、退货率等供应商绩效数据

## 采购建议
- 基于当前快照，可优先关注高单价物料的议价空间。
- 在没有历史价格前，不建议直接采取“锁价防上涨”的结论。
- 后续接入真实 ERP 历史订单后，再生成价格趋势折线图和涨跌幅分析。
""",
            "charts": [
                {"type": "bar", "title": "制动系统物料当前单价对比", "data": price_chart_data},
                {"type": "pie", "title": "物料库存快照分布", "data": stock_chart_data},
            ],
            "source": "mock_erp",
            "data_scope": "current_snapshot",
            "limitations": [
                "演示数据，不代表真实 ERP 生产数据",
                "未提供历史价格序列，不能判断上涨、下降或稳定趋势",
            ],
        }

        _async_tasks[task_id]["status"] = "completed"
        _async_tasks[task_id]["result"] = result
        _async_tasks[task_id]["completed_at"] = time.time()

    except Exception as e:
        _async_tasks[task_id]["status"] = "failed"
        _async_tasks[task_id]["result"] = {"error": str(e)}
        _async_tasks[task_id]["completed_at"] = time.time()


def get_all_async_tasks() -> Dict[str, Dict[str, Any]]:
    """获取所有异步任务"""
    return _async_tasks
