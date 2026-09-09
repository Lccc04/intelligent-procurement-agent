"""Focused regression checks for the new execution paths.

Run with ``PYTHONIOENCODING=utf-8 python src/test/regression_test.py``.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, "src")

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command

from agent.tools.async_tools import check_async_task, start_async_task
from agent.tools.mock_tools import ORDERS, order_create
from agent.tools.tool_registry import get_all_runtime_tools
from agent.subagents.loader import load_subagent_configs
from api_view.persistence import FileDB


class TestState(TypedDict):
    messages: Annotated[list, add_messages]


def test_tool_registry_and_configs():
    names = {tool.name for tool in get_all_runtime_tools()}
    assert {"read_file", "write_file", "execute_code", "chart_generator", "knowledge_search"} <= names
    assert {config["name"] for config in load_subagent_configs()} >= {"procurement-analyst", "procurement-order"}


def test_order_requires_approval_then_writes():
    def create_node(state):
        return {"messages": [order_create.invoke({"part_id": "P001", "quantity": 1, "unit_price": 280})]}

    graph = StateGraph(TestState)
    graph.add_node("create", create_node)
    graph.add_edge(START, "create")
    graph.add_edge("create", END)
    app = graph.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "regression-order"}}
    before = len(ORDERS)

    interrupted = app.invoke({"messages": []}, config=config)
    assert "__interrupt__" in interrupted
    assert len(ORDERS) == before

    completed = app.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config=config)
    assert "PO" in completed["messages"][-1].content
    assert len(ORDERS) == before + 1


def test_approval_statistics():
    store_path = Path(".agent_runtime/approval-regression.json")
    if store_path.exists():
        store_path.unlink()
    store = FileDB(str(store_path))
    try:
        triggered = store.record_approval_trigger(
            thread_id="approval-thread",
            user_id="approval-user",
            interrupt_data={
                "action_requests": [
                    {
                        "name": "order_create",
                        "description": "test approval",
                    }
                ]
            },
        )

        pending = store.get_approval_stats("approval-user")
        assert pending["total"] == 1
        assert pending["pending"] == 1
        assert pending["approved"] == 0

        resolved = store.record_approval_resolution(
            triggered["approval_id"],
            "approved",
        )
        assert resolved and resolved["status"] == "approved"

        completed = store.get_approval_stats("approval-user")
        assert completed["approved"] == 1
        assert completed["pending"] == 0
        assert completed["resolved"] == 1
        assert completed["response_rate"] == 100.0
        assert completed["by_action"] == {"order_create": 1}
    finally:
        if store_path.exists():
            store_path.unlink()


def test_approval_decisions():
    from api_view.api.chat import ChatStreamRequest, _approval_decision_status

    assert ChatStreamRequest(message="test", thread_id=None).thread_id is None
    assert _approval_decision_status({"decisions": [{"type": "approve"}]}) == "approved"
    assert _approval_decision_status({"decisions": [{"type": "reject"}]}) == "rejected"
    assert _approval_decision_status({"decisions": [{"type": "cancel"}]}) == "cancelled"


def test_async_report_and_charts():
    started = json.loads(start_async_task.invoke({
        "task_type": "procurement_analysis",
        "instruction": "回归测试制动系统分析",
        "user_id": "regression",
    }))
    task_id = started["task_id"]
    deadline = time.time() + 8
    result = None
    while time.time() < deadline:
        result = json.loads(check_async_task.invoke({"task_id": task_id}))
        if result.get("status") in {"completed", "failed"}:
            break
        time.sleep(0.1)
    assert result and result["status"] == "completed"
    assert result["result"]["report"]
    assert len(result["result"]["charts"]) == 2


if __name__ == "__main__":
    test_tool_registry_and_configs()
    test_order_requires_approval_then_writes()
    test_approval_statistics()
    test_approval_decisions()
    test_async_report_and_charts()
    print("regression tests passed")
