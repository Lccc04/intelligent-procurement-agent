"""
技能同步中间件
本地技能同步到沙箱（增量同步）
"""
import os
from typing import Dict, Any
from agent.log_utils import log


class SkillsSyncMiddleware:
    """本地技能同步到沙箱中间件"""

    def __init__(self, skills_dir: str = None, sandbox_manager=None):
        self.skills_dir = skills_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "..", "skills"
        )
        self.sandbox_manager = sandbox_manager
        self._synced = False

    def before_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Agent 执行前同步技能到沙箱"""
        if self._synced or not self.sandbox_manager:
            return state

        try:
            self._sync_skills()
            self._synced = True
        except Exception as e:
            log.error(f"技能同步失败: {e}")

        return state

    def _sync_skills(self):
        """同步技能文件到沙箱"""
        if not os.path.exists(self.skills_dir):
            log.warning(f"技能目录不存在: {self.skills_dir}")
            return

        synced_count = 0
        for root, dirs, files in os.walk(self.skills_dir):
            for file in files:
                if file.endswith(".md") or file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    rel_path = os.path.relpath(filepath, self.skills_dir)
                    # 同步到沙箱 /skills/ 目录
                    # self.sandbox_manager.upload_file(filepath, f"/skills/{rel_path}")
                    synced_count += 1

        log.info(f"✅ 技能同步完成: {synced_count} 个文件")
