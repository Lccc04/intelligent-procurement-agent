"""
子 Agent 委派工具
task - 主 Agent 委派任务给子 Agent
"""
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from typing import Dict, Any, List
import json

from agent.config import llm_config
from agent.log_utils import log
from agent.subagents.loader import load_subagent_configs, resolve_subagent_tools
from agent.tools.mock_tools import get_all_mock_tools
from agent.tools.hitl_tools import request_order_info


# 子 Agent 实例缓存
_subagent_instances: Dict[str, Any] = {}


def _get_llm():
    """获取 LLM 实例"""
    return ChatOpenAI(
        model=llm_config.model,
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
        temperature=llm_config.temperature,
    )


def _create_subagent(config: Dict[str, Any], available_tools: list):
    """根据配置创建子 Agent 实例"""
    name = config.get("name")
    system_prompt = config.get("system_prompt", "")

    # 解析工具
    tools = resolve_subagent_tools(config, available_tools)

    # 创建 Agent
    agent = create_react_agent(
        model=_get_llm(),
        tools=tools,
        prompt=system_prompt,
    )

    log.info(f"✅ 创建子 Agent: {name}，工具数: {len(tools)}")
    return agent


def _ensure_subagents_loaded():
    """确保所有子 Agent 已加载"""
    if not _subagent_instances:
        configs = load_subagent_configs()
        available_tools = [
            *get_all_mock_tools(),
            request_order_info,
        ]
        for config in configs:
            name = config.get("name")
            if name and name not in _subagent_instances:
                # 采购分析专家走异步，不在这里创建同步实例
                if name == "procurement-analyst":
                    continue
                _subagent_instances[name] = _create_subagent(config, available_tools)


@tool
async def task(subagent_name: str, instruction: str, user_id: str = "default", username: str = "用户") -> str:
    """
    委派任务给子 Agent 执行。每次调用创建独立上下文，
    执行完返回单个报告。支持特殊化配置。

    Args:
        subagent_name: 子 Agent 名称，如 "procurement-order"
        instruction: 详细的任务指令
        user_id: 用户ID
        username: 用户名

    Returns:
        子 Agent 执行结果
    """
    _ensure_subagents_loaded()

    if subagent_name not in _subagent_instances:
        available = list(_subagent_instances.keys())
        return json.dumps({
            "code": -1,
            "message": f"子 Agent '{subagent_name}' 不存在，可用的子 Agent: {available}",
        }, ensure_ascii=False)

    if subagent_name == "procurement-analyst":
        return json.dumps({
            "code": -1,
            "message": "采购分析专家必须使用 start_async_task 启动异步任务，不能用 task 同步调用",
        }, ensure_ascii=False)

    try:
        agent = _subagent_instances[subagent_name]

        # 构造输入，传递用户上下文
        full_instruction = f"""
用户信息：
- user_id: {user_id}
- username: {username}

任务指令：
{instruction}
"""

        # 执行子 Agent
        result = await agent.ainvoke({
            "messages": [("user", full_instruction)]
        })

        # 提取最终回复
        messages = result.get("messages", [])
        final_response = ""
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content and not hasattr(msg, 'tool_calls'):
                final_response = msg.content
                break

        return json.dumps({
            "code": 0,
            "subagent": subagent_name,
            "result": final_response,
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        log.error(f"子 Agent {subagent_name} 执行失败: {e}")
        return json.dumps({
            "code": -1,
            "subagent": subagent_name,
            "error": str(e),
        }, ensure_ascii=False)


def get_available_subagents() -> List[str]:
    """获取可用的子 Agent 列表"""
    _ensure_subagents_loaded()
    return list(_subagent_instances.keys())
