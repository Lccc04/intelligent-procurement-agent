"""
用户偏好记忆更新中间件
对话结束后自动提取用户偏好并持久化
"""
import json
from typing import Dict, Any, List
from agent.log_utils import log


class MemoryUpdateMiddleware:
    """用户偏好自动提取 + 持久化中间件"""

    def __init__(self, db=None):
        self.db = db  # 数据库实例，用于持久化偏好

    def after_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Agent 执行后提取用户偏好"""
        try:
            user_id = state.get("user_id", "default_user")
            messages = state.get("messages", [])

            if not messages:
                return state

            # 简单的偏好提取（实际项目中用 LLM 提取）
            preferences = self._extract_preferences(messages)

            if preferences and self.db:
                self.db.update_preferences(user_id, preferences)
                log.info(f"✅ 用户偏好已更新: user_id={user_id}, preferences={preferences}")

        except Exception as e:
            log.error(f"用户偏好更新失败: {e}")

        return state

    def _extract_preferences(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """从对话中提取用户偏好（简化版）"""
        preferences = {}
        recent_queries = []
        recent_suppliers = []

        for msg in messages:
            if isinstance(msg, dict):
                role = msg.get("role")
                content = msg.get("content", "")
            else:
                role = getattr(msg, "type", None)
                content = getattr(msg, "content", "")
            if role in {"user", "human"} and isinstance(content, str):
                recent_queries.append(content[:100])
                suppliers = ["博世", "大陆", "采埃孚", "福耀", "华翔"]
                for supplier in suppliers:
                    if supplier in content:
                        recent_suppliers.append(supplier)

        if recent_queries:
            preferences["recent_queries"] = recent_queries[-5:]  # 保留最近5条
        if recent_suppliers:
            preferences["recent_suppliers"] = list(set(recent_suppliers))

        return preferences
