"""
/api/history CRUD + 展示消息存取
历史会话列表 / 消息查询 / 会话删除
"""
from fastapi import APIRouter
from typing import List, Dict, Any
from api_view.agent_loader import get_agent_loader
from api_view.web_config import get_db

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/sessions")
async def list_sessions(user_id: str = None):
    """获取会话列表"""
    loader = get_agent_loader()
    sessions = loader.db.list_sessions(user_id)

    # 格式化输出
    result = []
    for s in sessions:
        messages = loader.get_display_messages(s["thread_id"])
        last_message = messages[-1]["content"][:100] if messages else ""
        result.append({
            "thread_id": s["thread_id"],
            "user_id": s.get("user_id"),
            "username": s.get("username"),
            "created_at": s.get("created_at"),
            "updated_at": s.get("updated_at"),
            "interrupted": s.get("interrupted", False),
            "message_count": len(messages),
            "last_message": last_message,
        })

    return {"code": 0, "data": result, "total": len(result)}


@router.get("/{thread_id}/messages")
async def get_messages(thread_id: str):
    """获取会话的所有消息"""
    loader = get_agent_loader()
    messages = loader.get_display_messages(thread_id)
    return {"code": 0, "data": messages, "total": len(messages)}


@router.delete("/{thread_id}")
async def delete_session(thread_id: str):
    """删除会话"""
    loader = get_agent_loader()
    loader.db.delete_session(thread_id)
    return {"code": 0, "message": "会话已删除", "thread_id": thread_id}


@router.get("/{thread_id}")
async def get_session_detail(thread_id: str):
    """获取会话详情"""
    loader = get_agent_loader()
    session = loader.get_session(thread_id)
    if not session:
        return {"code": -1, "message": "会话不存在"}

    messages = loader.get_display_messages(thread_id)
    return {
        "code": 0,
        "data": {
            **session,
            "messages": messages,
            "message_count": len(messages),
        }
    }
