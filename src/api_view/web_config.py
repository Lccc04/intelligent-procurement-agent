"""
MongoDB 连接配置
（简化版：使用内存存储代替 MongoDB，保证项目可直接运行）
"""
from typing import Dict, Any, List, Optional
import json
import time


class InMemoryDB:
    """内存数据库（替代 MongoDB，用于开发和演示）"""

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}  # thread_id -> session
        self.messages: Dict[str, List[Dict[str, Any]]] = {}  # thread_id -> messages
        self.preferences: Dict[str, Dict[str, Any]] = {}  # user_id -> preferences

    # ===== 会话管理 =====
    def create_session(self, thread_id: str, user_id: str, username: str):
        """创建会话"""
        self.sessions[thread_id] = {
            "thread_id": thread_id,
            "user_id": user_id,
            "username": username,
            "created_at": time.time(),
            "updated_at": time.time(),
            "interrupted": False,
            "interrupt_data": None,
        }
        self.messages[thread_id] = []

    def get_session(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """获取会话"""
        return self.sessions.get(thread_id)

    def update_session(self, thread_id: str, **kwargs):
        """更新会话"""
        if thread_id in self.sessions:
            self.sessions[thread_id].update(kwargs)
            self.sessions[thread_id]["updated_at"] = time.time()

    def list_sessions(self, user_id: str = None) -> List[Dict[str, Any]]:
        """列出会话"""
        result = list(self.sessions.values())
        if user_id:
            result = [s for s in result if s.get("user_id") == user_id]
        return sorted(result, key=lambda x: x["updated_at"], reverse=True)

    def delete_session(self, thread_id: str):
        """删除会话"""
        self.sessions.pop(thread_id, None)
        self.messages.pop(thread_id, None)

    # ===== 消息管理 =====
    def add_message(self, thread_id: str, role: str, content: str, **kwargs):
        """添加消息"""
        msg = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            **kwargs
        }
        if thread_id not in self.messages:
            self.messages[thread_id] = []
        self.messages[thread_id].append(msg)

    def get_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """获取消息列表"""
        return self.messages.get(thread_id, [])

    def save_display_messages(self, thread_id: str, messages: List[Dict[str, Any]]):
        """保存展示消息（中断时保存现场）"""
        self.messages[thread_id] = messages

    # ===== 用户偏好 =====
    def get_preferences(self, user_id: str) -> Dict[str, Any]:
        """获取用户偏好"""
        return self.preferences.get(user_id, {
            "preferred_output": "markdown",
            "preferred_chart_type": "bar",
            "preferred_currency": "CNY",
            "preferred_language": "zh-CN",
            "recent_suppliers": [],
            "recent_queries": [],
        })

    def update_preferences(self, user_id: str, prefs: Dict[str, Any]):
        """更新用户偏好"""
        current = self.get_preferences(user_id)
        current.update(prefs)
        self.preferences[user_id] = current


# 全局单例
db = InMemoryDB()


def get_db() -> InMemoryDB:
    """获取数据库实例"""
    return db
