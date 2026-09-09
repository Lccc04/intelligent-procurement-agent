"""
主 Agent 入口
create_main_agent() + precompute_agent_context()
基于 LangGraph 实现的采购智能体执行入口
"""
import os
import sys
from typing import Annotated, Dict, Any, List, Optional, NotRequired
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph.message import add_messages

from agent.config import llm_config
from agent.schema import ProcurementContext, UserPreferences
from agent.log_utils import log
from agent.memory.prompts import MAIN_AGENT_SYSTEM_PROMPT
from agent.tools.mock_tools import get_all_mock_tools
from agent.tools.tool_registry import get_all_runtime_tools
from agent.tools.planning_tools import write_todos
from agent.tools.hitl_tools import request_order_info
from agent.tools.async_tools import start_async_task, check_async_task
from agent.tools.subagent_tools import task
from agent.middleware_config import AgentMiddlewareStack
from agent.checkpoint import PersistentCheckpointSaver
from api_view.web_config import get_db


# 全局 Agent 实例
_main_agent = None
_checkpointer = PersistentCheckpointSaver(get_db())


class MainAgentState(TypedDict):
    messages: Annotated[list, add_messages]
    remaining_steps: NotRequired[int]
    user_id: NotRequired[str]
    username: NotRequired[str]
    user_context: NotRequired[Dict[str, Any]]


def _get_llm():
    """获取 LLM 实例"""
    return ChatOpenAI(
        model=llm_config.model,
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
        temperature=llm_config.temperature,
        max_tokens=llm_config.max_tokens,
    )


def _build_system_prompt(user_context: ProcurementContext = None) -> str:
    """构建系统提示词，注入用户上下文"""
    prompt = MAIN_AGENT_SYSTEM_PROMPT

    if user_context:
        prefs = user_context.preferences
        user_info = f"""
## 当前用户信息
- user_id: {user_context.user_id}
- username: {user_context.username}
- 偏好图表类型: {prefs.preferred_chart_type}
- 偏好货币: {prefs.preferred_currency}
- 偏好语言: {prefs.preferred_language}
- 最近查询供应商: {', '.join(prefs.recent_suppliers) if prefs.recent_suppliers else '无'}
"""
        prompt += user_info

    return prompt


def precompute_agent_context(
    user_id: str = "default_user",
    username: str = "用户",
    preferences: Dict[str, Any] = None
) -> ProcurementContext:
    """
    预计算 Agent 上下文
    加载用户偏好、初始化上下文对象
    """
    user_prefs = UserPreferences()
    if preferences:
        user_prefs = UserPreferences(**preferences)

    context = ProcurementContext(
        user_id=user_id,
        username=username,
        preferences=user_prefs,
    )

    log.info(f"✅ 预计算 Agent 上下文: user_id={user_id}, username={username}")
    return context


def create_main_agent(user_context: ProcurementContext = None):
    """
    创建主 Agent 实例
    集成所有工具：MCP 工具、规划工具、子 Agent 委派、异步任务、HITL
    """
    global _main_agent

    if _main_agent is not None:
        return _main_agent

    log.info("🔧 正在创建主 Agent...")

    # 1. 加载 MCP 工具（优先），失败则用 Mock 工具。
    try:
        # 尝试加载 MCP 工具（异步，这里简化为直接用 mock）
        mcp_tools = get_all_mock_tools()
        log.info(f"✅ 加载 {len(mcp_tools)} 个业务工具")
    except Exception as e:
        log.warning(f"⚠️ MCP 工具加载失败，使用 Mock 工具: {e}")
        mcp_tools = get_all_mock_tools()

    # 2. 组装所有工具
    all_tools = [
        *get_all_runtime_tools(),  # 业务、文件、技能、图表和 RAG 接口
        write_todos,          # 任务规划
        task,                 # 子 Agent 委派（同步）
        start_async_task,     # 异步任务启动
        check_async_task,     # 异步任务查询
        request_order_info,   # HITL 订单信息补充
    ]

    unique_tools = {item.name: item for item in all_tools}
    all_tools = list(unique_tools.values())
    log.info(f"✅ 主 Agent 共加载 {len(all_tools)} 个工具")

    # 3. 构建系统提示词
    system_prompt = _build_system_prompt(user_context)

    # 4. 将 7 个运行时中间件挂到 LangGraph 模型前后钩子。
    middleware_stack = AgentMiddlewareStack(get_db(), user_context)

    # 5. 创建 LangGraph ReAct Agent
    _main_agent = create_react_agent(
        model=_get_llm(),
        tools=all_tools,
        prompt=system_prompt,
        state_schema=MainAgentState,
        pre_model_hook=middleware_stack.before_model,
        post_model_hook=middleware_stack.after_model,
        checkpointer=_checkpointer,
        version="v2",
    )

    log.info("✅ 主 Agent 创建完成")
    return _main_agent


def get_main_agent():
    """获取主 Agent 单例"""
    if _main_agent is None:
        return create_main_agent()
    return _main_agent


def reset_main_agent():
    """重置主 Agent（用于测试或配置变更）"""
    global _main_agent
    _main_agent = None
    log.info("🔄 主 Agent 已重置")


async def chat_with_agent(
    message: str,
    user_id: str = "default_user",
    username: str = "用户",
    thread_id: str = None,
    resume_data: Dict[str, Any] = None,
):
    """
    与主 Agent 对话（便捷函数）

    Args:
        message: 用户消息
        user_id: 用户ID
        username: 用户名
        thread_id: 会话ID（用于多轮对话和中断恢复）
        resume_data: 中断恢复数据（当从中断恢复时传入）

    Returns:
        Agent 执行结果
    """
    agent = get_main_agent()

    # 配置
    config = {}
    if thread_id:
        config["configurable"] = {"thread_id": thread_id}

    # 构造输入
    if resume_data:
        # 中断恢复
        from langgraph.types import Command
        input_data = Command(resume=resume_data)
    else:
        input_data = {
            "messages": [("user", message)],
            "user_id": user_id,
            "username": username,
        }

    # 执行
    result = await agent.ainvoke(input_data, config=config)
    return result
