"""
/api/chat/stream (SSE)、resume、state、history
核心：SSE 流式对话 + 中断检测 + 中断恢复 + 展示消息持久化
"""
import json
import asyncio
from typing import AsyncGenerator, Dict, Any
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api_view.agent_loader import get_agent_loader
from api_view.web_config import get_db
from agent.log_utils import log

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ===== 请求模型 =====

class ChatStreamRequest(BaseModel):
    message: str
    user_id: str = "default_user"
    username: str = "用户"
    thread_id: str = None


class ResumeRequest(BaseModel):
    resume: Dict[str, Any]


# ===== SSE 事件格式 =====

def sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """构造 SSE 事件"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def sse_done(thread_id: str = None, interrupted: bool = False, **kwargs) -> str:
    """构造 SSE done 事件"""
    data = {"thread_id": thread_id, "interrupted": interrupted, **kwargs}
    return sse_event("done", data)


def unpack_stream_chunk(chunk):
    """兼容 LangGraph 旧版 tuple 和 v2 dict 流式事件格式。"""
    if isinstance(chunk, dict):
        return chunk.get("type"), chunk.get("data")
    if isinstance(chunk, tuple) and len(chunk) >= 2:
        return chunk[0], chunk[1]
    return None, None


# ===== 核心流式对话 =====

@router.post("/stream")
async def chat_stream(request: ChatStreamRequest):
    """
    流式对话接口（SSE）
    双流模式：messages（内容输出）+ values（中断检测）
    """
    loader = get_agent_loader()
    agent = loader.get_agent()
    db = get_db()

    # 处理 thread_id
    thread_id = request.thread_id or loader.create_thread_id()
    loader.ensure_session(thread_id, request.user_id, request.username)

    # 保存用户消息
    loader.add_display_message(thread_id, "user", request.message)

    # 创建配置
    config = loader.create_config(thread_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # 发送 thread_id 事件
            yield sse_event("thread_id", {"thread_id": thread_id})

            # 构造输入
            input_data = {
                "messages": [("user", request.message)]
            }

            # 流式执行 Agent（双模式：messages + values）
            full_content = ""
            current_tool_name = None
            current_tool_args = ""

            async for chunk in agent.astream(
                input=input_data,
                config=config,
                stream_mode=["messages", "values"],
                subgraphs=True,
                version="v2",
            ):
                chunk_type, chunk_data = unpack_stream_chunk(chunk)

                # ===== 流 B：values - 中断检测（必须先处理） =====
                if chunk_type == "values":
                    values_data = chunk_data
                    if isinstance(values_data, dict) and values_data.get("interrupts"):
                        for interrupt in values_data["interrupts"]:
                            interrupt_value = interrupt.get("value", {}) if hasattr(interrupt, "get") else {}

                            # 判断中断类型
                            if isinstance(interrupt_value, dict) and "action_requests" in interrupt_value:
                                interrupt_type = "hitl_approval"
                            elif isinstance(interrupt_value, dict) and interrupt_value.get("type") == "order_info_request":
                                interrupt_type = "order_info_supplement"
                            else:
                                interrupt_type = "unknown"

                            # 发送中断事件
                            yield sse_event("interrupt", {
                                "interrupt_type": interrupt_type,
                                "data": interrupt_value if isinstance(interrupt_value, dict) else {"value": str(interrupt_value)},
                            })

                            # 标记会话中断
                            loader.mark_interrupted(thread_id, {
                                "type": interrupt_type,
                                "data": interrupt_value,
                            })

                            # 保存当前展示消息
                            display_messages = loader.get_display_messages(thread_id)
                            if full_content:
                                display_messages.append({"role": "assistant", "content": full_content})
                            loader.save_display_messages(thread_id, display_messages)

                            # 发送 done 事件并结束流
                            yield sse_done(thread_id=thread_id, interrupted=True)
                            return

                # ===== 流 A：messages - 内容输出 =====
                if chunk_type == "messages":
                    msg_chunk = chunk_data
                    if not isinstance(msg_chunk, (tuple, list)) or len(msg_chunk) == 0:
                        continue

                    msg = msg_chunk[0]

                    # 工具调用块
                    if hasattr(msg, "tool_call_chunks") and msg.tool_call_chunks:
                        for tc in msg.tool_call_chunks:
                            if tc.get("name"):
                                current_tool_name = tc["name"]
                                yield sse_event("tool_start", {"tool": current_tool_name})
                            if tc.get("args"):
                                current_tool_args += tc["args"]
                                yield sse_event("tool_args", {"tool": current_tool_name, "args": tc["args"]})

                    # 工具结果
                    elif hasattr(msg, "type") and msg.type == "tool":
                        tool_name = getattr(msg, "name", "unknown")
                        tool_content = getattr(msg, "content", "")
                        if isinstance(tool_content, list):
                            tool_content = str(tool_content[0]) if tool_content else ""
                        yield sse_event("tool_result", {"tool": tool_name, "content": tool_content[:500]})
                        yield sse_event("tool_end", {"tool": tool_name})
                        current_tool_name = None
                        current_tool_args = ""

                    # 纯文本 token
                    elif hasattr(msg, "content") and msg.content:
                        content = msg.content
                        if isinstance(content, str):
                            full_content += content
                            yield sse_event("token", {"content": content})

            # 保存最终回复
            if full_content:
                loader.add_display_message(thread_id, "assistant", full_content)

            # 发送完成事件
            yield sse_done(thread_id=thread_id, interrupted=False, content=full_content)

        except Exception as e:
            log.error(f"SSE 流式对话异常: {e}")
            import traceback
            traceback.print_exc()
            yield sse_event("error", {"message": str(e)})
            yield sse_done(thread_id=thread_id, interrupted=False, error=str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ===== 中断恢复 =====

@router.post("/{thread_id}/resume")
async def chat_resume(thread_id: str, request: ResumeRequest):
    """
    从中断处恢复执行
    用于 HITL 审批后继续，或订单信息补充后继续
    """
    loader = get_agent_loader()
    agent = loader.get_agent()
    db = get_db()

    # 检查会话是否存在
    session = loader.get_session(thread_id)
    if not session:
        return {"code": -1, "message": "会话不存在"}

    # 清除中断状态
    loader.clear_interrupted(thread_id)

    config = loader.create_config(thread_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # 加载中断前的消息
            existing_messages = loader.get_display_messages(thread_id)

            # 构造恢复输入
            from langgraph.types import Command
            input_data = Command(resume=request.resume)

            full_content = ""

            async for chunk in agent.astream(
                input=input_data,
                config=config,
                stream_mode=["messages", "values"],
                subgraphs=True,
                version="v2",
            ):
                chunk_type, chunk_data = unpack_stream_chunk(chunk)

                # 中断检测
                if chunk_type == "values":
                    values_data = chunk_data
                    if isinstance(values_data, dict) and values_data.get("interrupts"):
                        for interrupt in values_data["interrupts"]:
                            interrupt_value = interrupt.get("value", {}) if hasattr(interrupt, "get") else {}
                            if isinstance(interrupt_value, dict) and "action_requests" in interrupt_value:
                                interrupt_type = "hitl_approval"
                            elif isinstance(interrupt_value, dict) and interrupt_value.get("type") == "order_info_request":
                                interrupt_type = "order_info_supplement"
                            else:
                                interrupt_type = "unknown"

                            yield sse_event("interrupt", {
                                "interrupt_type": interrupt_type,
                                "data": interrupt_value if isinstance(interrupt_value, dict) else {"value": str(interrupt_value)},
                            })
                            loader.mark_interrupted(thread_id, {"type": interrupt_type, "data": interrupt_value})
                            yield sse_done(thread_id=thread_id, interrupted=True)
                            return

                # 内容输出
                if chunk_type == "messages":
                    msg_chunk = chunk_data
                    if not isinstance(msg_chunk, (tuple, list)) or len(msg_chunk) == 0:
                        continue
                    msg = msg_chunk[0]

                    if hasattr(msg, "tool_call_chunks") and msg.tool_call_chunks:
                        for tc in msg.tool_call_chunks:
                            if tc.get("name"):
                                yield sse_event("tool_start", {"tool": tc["name"]})
                            if tc.get("args"):
                                yield sse_event("tool_args", {"tool": tc.get("name", ""), "args": tc["args"]})

                    elif hasattr(msg, "type") and msg.type == "tool":
                        tool_name = getattr(msg, "name", "unknown")
                        tool_content = getattr(msg, "content", "")
                        if isinstance(tool_content, list):
                            tool_content = str(tool_content[0]) if tool_content else ""
                        yield sse_event("tool_result", {"tool": tool_name, "content": tool_content[:500]})
                        yield sse_event("tool_end", {"tool": tool_name})

                    elif hasattr(msg, "content") and msg.content:
                        content = msg.content
                        if isinstance(content, str):
                            full_content += content
                            yield sse_event("token", {"content": content})

            if full_content:
                loader.add_display_message(thread_id, "assistant", full_content)

            yield sse_done(thread_id=thread_id, interrupted=False, content=full_content)

        except Exception as e:
            log.error(f"恢复执行异常: {e}")
            import traceback
            traceback.print_exc()
            yield sse_event("error", {"message": str(e)})
            yield sse_done(thread_id=thread_id, interrupted=False, error=str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ===== 会话状态查询 =====

@router.get("/{thread_id}/state")
async def chat_state(thread_id: str):
    """查询会话状态（是否中断、中断类型等）"""
    loader = get_agent_loader()
    session = loader.get_session(thread_id)
    if not session:
        return {"code": -1, "message": "会话不存在"}

    return {
        "code": 0,
        "thread_id": thread_id,
        "interrupted": session.get("interrupted", False),
        "interrupt_data": session.get("interrupt_data"),
        "user_id": session.get("user_id"),
        "created_at": session.get("created_at"),
        "updated_at": session.get("updated_at"),
    }


# ===== 异步任务状态查询 =====

@router.get("/async-task/{task_id}")
async def get_async_task_status(task_id: str):
    """查询异步任务状态"""
    from agent.tools.async_tools import _async_tasks
    task = _async_tasks.get(task_id)
    if not task:
        return {"code": -1, "message": "任务不存在", "task_id": task_id}
    return {"code": 0, **task}
