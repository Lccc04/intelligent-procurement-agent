"""
持久化技能恢复中间件
下次沙箱创建时恢复用户已分配的技能
"""
from typing import Dict, Any, List
from agent.log_utils import log


class UserSkillsRestoreMiddleware:
    """持久化技能恢复中间件"""

    def __init__(self, db=None, sandbox_manager=None):
        self.db = db
        self.sandbox_manager = sandbox_manager

    def before_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """沙箱创建后恢复用户技能"""
        if not self.db or not self.sandbox_manager:
            return state

        try:
            user_id = state.get("user_id", "default_user")
            # 从数据库获取用户已分配的技能
            user_skills = self._get_user_skills(user_id)
            if user_skills:
                log.info(f"🔄 恢复用户技能: user_id={user_id}, skills={user_skills}")
                # 恢复到沙箱
                # for skill in user_skills:
                #     self.sandbox_manager.restore_skill(skill)
        except Exception as e:
            log.error(f"用户技能恢复失败: {e}")

        return state

    def _get_user_skills(self, user_id: str) -> List[str]:
        """获取用户已分配的技能列表"""
        # 实际项目中从数据库查询
        return []
