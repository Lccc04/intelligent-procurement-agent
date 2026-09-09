"""
AgentLoader 单例
生命周期管理、MongoDB 连接、展示消息存取
"""
import uuid
from typing import Dict, Any, Optional
from agent.main_agent import get_main_agent, create_main_agent, precompute_agent_context
from agent.schema import ProcurementContext
from api_view.web_config import get_db
from agent.log_utils import log


class AgentLoader:
    """Agent 加载器单例，管理 Agent 生命周期和会话"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.agent = None
        self.db = get_db()
        log.info("✅ AgentLoader 初始化完成")

    def initialize(self):
        """初始化 Agent（懒加载）"""
        if self.agent is None:
            log.info("🚀 正在初始化主 Agent...")
            context = precompute_agent_context()
            self.agent = create_main_agent(context)
            log.info("✅ 主 Agent 初始化完成")
        return self.agent

    def get_agent(self):
        """获取 Agent 实例"""
        return self.initialize()

    def create_thread_id(self) -> str:
        """生成新的会话ID"""
        return f"thread_{uuid.uuid4().hex[:12]}"

    def create_config(self, thread_id: str) -> Dict[str, Any]:
        """创建 LangGraph 配置（含 thread_id）"""
        return {
            "configurable": {
                "thread_id": thread_id,
            }
        }

    # ===== 展示消息存取 =====
    def save_display_messages(self, thread_id: str, messages: list):
        """保存展示消息到数据库（中断时保存现场）"""
        self.db.save_display_messages(thread_id, messages)

    def get_display_messages(self, thread_id: str) -> list:
        """获取展示消息"""
        return self.db.get_messages(thread_id)

    def add_display_message(self, thread_id: str, role: str, content: str, **kwargs):
        """添加一条展示消息"""
        self.db.add_message(thread_id, role, content, **kwargs)

    # ===== 会话管理 =====
    def ensure_session(self, thread_id: str, user_id: str, username: str):
        """确保会话存在，不存在则创建"""
        if not self.db.get_session(thread_id):
            self.db.create_session(thread_id, user_id, username)
            log.info(f"📝 创建新会话: {thread_id}")

    def get_session(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """获取会话"""
        return self.db.get_session(thread_id)

    def mark_interrupted(self, thread_id: str, interrupt_data: Dict[str, Any]):
        """标记会话为中断状态"""
        self.db.update_session(
            thread_id,
            interrupted=True,
            interrupt_data=interrupt_data,
        )

    def clear_interrupted(self, thread_id: str):
        """清除中断状态"""
        self.db.update_session(
            thread_id,
            interrupted=False,
            interrupt_data=None,
        )

    # ===== 用户偏好 =====
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """获取用户偏好"""
        return self.db.get_preferences(user_id)

    def update_user_preferences(self, user_id: str, prefs: Dict[str, Any]):
        """更新用户偏好"""
        self.db.update_preferences(user_id, prefs)


# 全局单例
agent_loader = AgentLoader()


def get_agent_loader() -> AgentLoader:
    """获取 AgentLoader 单例"""
    return agent_loader
