"""
HITL 人工介入工具
request_order_info - 请求用户补充订单信息
"""
from langchain_core.tools import tool
from langgraph.types import interrupt
import json


@tool
def request_order_info(missing_fields: list, current_info: dict = None) -> str:
    """
    请求用户补充订单信息。当创建订单所需的数据不完整时调用此工具，
    会暂停 Agent 执行，等待用户补充信息后继续。

    Args:
        missing_fields: 缺失的字段列表，如 ["part_id", "quantity"]
        current_info: 当前已有的订单信息（可选）

    Returns:
        用户补充的信息（由 interrupt 机制注入）
    """
    # 构造中断数据
    interrupt_data = {
        "type": "order_info_request",
        "missing_fields": missing_fields,
        "current_info": current_info or {},
        "message": f"请补充以下订单信息：{', '.join(missing_fields)}"
    }

    # 触发中断，等待用户回复
    user_response = interrupt(interrupt_data)

    # 用户回复后从这里继续
    if isinstance(user_response, dict):
        return json.dumps({
            "code": 0,
            "message": "信息补充成功",
            "data": user_response
        }, ensure_ascii=False)
    else:
        return json.dumps({
            "code": 0,
            "message": "收到用户回复",
            "data": {"supplement": str(user_response)}
        }, ensure_ascii=False)
