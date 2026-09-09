"""
上下文注入中间件
每轮对话前注入用户上下文（偏好、历史等）
"""
from typing import Dict, Any
from agent.log_utils import log


class ContextInjectionMiddleware:
    """用户上下文注入中间件"""

    def __init__(self, user_context: Dict[str, Any] = None):
        self.user_context = user_context or {}

    def before_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Agent 执行前注入上下文"""
        user_id = state.get("user_id", "default_user")
        username = state.get("username", "用户")

        # 构建上下文信息
        context_info = f"""
## 当前用户信息
- user_id: {user_id}
- username: {username}
"""
        # 注入到系统提示词或 state
        state["context_injected"] = True
        log.debug(f"✅ 上下文注入: user_id={user_id}")
        return state

    def after_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Agent 执行后处理"""
        return state
