"""Persistent asynchronous sub-agent task service."""
from __future__ import annotations

import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

from langchain_core.tools import tool

from api_view.web_config import get_db
from agent.tools.mock_tools import PARTS, SUPPLIERS


_async_tasks: Dict[str, Dict[str, Any]] = {
    task["task_id"]: task for task in get_db().list_tasks(limit=200)
}
_running_task_ids: set[str] = set()
_task_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="procurement-task")


def _submit(task: Dict[str, Any]):
    task_id = task["task_id"]
    if task_id in _running_task_ids:
        return
    _running_task_ids.add(task_id)
    _task_executor.submit(_run_async_task, task_id, task.get("instruction", ""), task.get("user_id", "default"))


@tool
def start_async_task(task_type: str, instruction: str, user_id: str = "default") -> str:
    """启动后台分析子 Agent，立即返回 task_id；任务状态可通过轮询接口恢复。"""
    if not instruction.strip():
        return json.dumps({"code": -1, "message": "任务指令不能为空"}, ensure_ascii=False)
    task = {
        "task_id": f"task_{uuid.uuid4().hex[:10]}",
        "task_type": task_type,
        "instruction": instruction,
        "user_id": user_id,
        "status": "queued",
        "stage": "queued",
        "progress": 0,
        "result": None,
        "artifacts": [],
        "created_at": time.time(),
        "updated_at": time.time(),
        "completed_at": None,
    }
    _async_tasks[task["task_id"]] = task
    get_db().create_task(task)
    _submit(task)
    return json.dumps({
        "code": 0,
        "message": "异步任务已启动",
        "task_id": task["task_id"],
        "status": task["status"],
        "progress": task["progress"],
        "hint": "任务正在后台执行，前端会自动轮询并展示报告和图表。",
    }, ensure_ascii=False)


@tool
def check_async_task(task_id: str) -> str:
    """查询任务状态、进度、报告和图表附件。"""
    task = get_db().get_task(task_id) or _async_tasks.get(task_id)
    if not task:
        return json.dumps({"code": -1, "message": "任务不存在", "task_id": task_id}, ensure_ascii=False)
    _async_tasks[task_id] = task
    return json.dumps({"code": 0, **task}, ensure_ascii=False)


def _update(task_id: str, **updates):
    get_db().update_task(task_id, **updates)
    current = _async_tasks.get(task_id, {}).copy()
    current.update(updates)
    current["updated_at"] = time.time()
    _async_tasks[task_id] = current


def _register_artifact(path, name, kind, user_id):
    artifact_id = f"artifact_{uuid.uuid4().hex[:10]}"
    artifact = {
        "artifact_id": artifact_id,
        "name": name,
        "path": path,
        "local_path": str(path),
        "kind": kind,
        "user_id": user_id,
        "created_at": time.time(),
        "download_url": f"/api/artifacts/{artifact_id}/download",
    }
    return get_db().create_artifact(artifact)


def _run_async_task(task_id: str, instruction: str, user_id: str):
    """Run the configured analyst workflow with deterministic demo data."""
    try:
        _update(task_id, status="running", stage="loading_data", progress=12)
        time.sleep(float(os.getenv("ANALYSIS_DELAY", "0.35")))
        brake_parts = [part for part in PARTS if part["category"] == "制动系统"]
        supplier_map = {supplier["id"]: supplier for supplier in SUPPLIERS}

        _update(task_id, stage="calculating_metrics", progress=48)
        time.sleep(float(os.getenv("ANALYSIS_DELAY", "0.35")))
        price_rows = "\n".join(
            f"| {part['id']} | {part['name']} | {part['spec']} | {part['unit']} | {part['price']:.2f} | "
            f"{part['stock']} | {supplier_map.get(part['supplier_id'], {}).get('name', part['supplier_id'])} |"
            for part in brake_parts
        )
        avg_price = sum(part["price"] for part in brake_parts) / len(brake_parts) if brake_parts else 0
        max_part = max(brake_parts, key=lambda part: part["price"]) if brake_parts else None
        min_part = min(brake_parts, key=lambda part: part["price"]) if brake_parts else None
        warning_parts = [part for part in PARTS if part["stock"] <= 100]
        conclusions = []
        if brake_parts:
            conclusions.append(f"制动系统共有 {len(brake_parts)} 个演示物料，当前平均单价为 {avg_price:.2f} CNY。")
        if max_part and min_part:
            conclusions.append(f"当前单价最高的是 {max_part['name']}（{max_part['price']:.2f} CNY），最低的是 {min_part['name']}（{min_part['price']:.2f} CNY）。")
        conclusions.append("当前数据是单时点快照，没有历史价格序列，不能判断真实上涨、下降或稳定趋势。")

        _update(task_id, stage="writing_report", progress=82)
        time.sleep(float(os.getenv("ANALYSIS_DELAY", "0.35")))
        report = f"""# 采购分析报告

## 分析任务
{instruction}

## 数据来源与边界
- 来源：mock_erp 演示数据
- 范围：当前价格/库存快照
- 限制：未提供历史价格、采购批次价格或外部市场报价，不能据此断言价格趋势

## 当前价格对比
| 物料ID | 物料名称 | 规格 | 单位 | 当前单价(CNY) | 库存 | 供应商 |
|---|---|---|---|---:|---:|---|
{price_rows}

## 可确认结论
{chr(10).join(f"{index}. {item}" for index, item in enumerate(conclusions, 1))}

## 采购建议
- 基于当前快照，可优先关注高单价物料的议价空间。
- 在补齐历史报价前，不建议直接采取“锁价防上涨”的结论。
- 接入真实 ERP 历史订单后，再生成价格趋势折线图和涨跌幅分析。
"""
        user_root = __import__("agent.tools.file_tools", fromlist=["_user_root"])._user_root(user_id)
        report_path = user_root / "analysis" / f"report_{task_id}.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        report_artifact = _register_artifact(f"/analysis/{report_path.name}", report_path.name, "report", user_id)

        price_chart = {part["name"]: part["price"] for part in brake_parts}
        stock_chart = {
            "充足": len([part for part in PARTS if part["stock"] > 100]),
            "预警": len(warning_parts),
        }
        charts = [
            {"type": "bar", "title": "制动系统物料当前单价对比", "data": price_chart},
            {"type": "pie", "title": "物料库存快照分布", "data": stock_chart},
        ]
        result = {
            "report": report,
            "charts": charts,
            "source": "mock_erp",
            "data_scope": "current_snapshot",
            "limitations": ["演示数据，不代表真实 ERP 生产数据", "未提供历史价格序列，不能判断趋势"],
            "artifacts": [report_artifact],
        }
        _update(task_id, status="completed", stage="completed", progress=100, result=result, artifacts=[report_artifact], completed_at=time.time())
    except Exception as exc:
        _update(task_id, status="failed", stage="failed", progress=100, result={"error": str(exc)}, completed_at=time.time())
    finally:
        _running_task_ids.discard(task_id)


def recover_pending_tasks():
    """Re-queue tasks left in running/queued state by a previous process."""
    for task in get_db().list_tasks(limit=200):
        _async_tasks[task["task_id"]] = task
        if task.get("status") in {"queued", "running"}:
            _update(task["task_id"], status="queued", stage="recovered", progress=min(task.get("progress", 0), 80))
            _submit(_async_tasks[task["task_id"]])


def get_all_async_tasks() -> Dict[str, Dict[str, Any]]:
    return {task["task_id"]: task for task in get_db().list_tasks(limit=200)}
