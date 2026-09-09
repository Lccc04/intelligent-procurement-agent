"""
数据模型
ProcurementContext、UserPreferences、ChatRequest
"""
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class UserPreferences(BaseModel):
    """用户偏好"""
    preferred_output: str = "markdown"
    preferred_chart_type: str = "bar"
    preferred_currency: str = "CNY"
    preferred_language: str = "zh-CN"
    recent_suppliers: List[str] = Field(default_factory=list)
    recent_queries: List[str] = Field(default_factory=list)


class ProcurementContext(BaseModel):
    """采购上下文"""
    user_id: str = "default_user"
    username: str = "用户"
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    thread_id: Optional[str] = None


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str
    user_id: str = "default_user"
    username: str = "用户"
    thread_id: Optional[str] = None


class ResumeRequest(BaseModel):
    """中断恢复请求"""
    resume: Dict[str, Any]


class TodoItem(BaseModel):
    """任务清单项"""
    id: str
    content: str
    status: Literal["pending", "in_progress", "completed", "cancelled"] = "pending"
    depends_on: List[str] = Field(default_factory=list)


class AgentState(BaseModel):
    """Agent 状态（LangGraph State）"""
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    todos: List[TodoItem] = Field(default_factory=list)
    user_context: Optional[ProcurementContext] = None
    interrupt_data: Optional[Dict[str, Any]] = None
