"""
沙箱健康检查中间件
ping 沙箱 → 不可达 → 触发重建
"""
from typing import Dict, Any
from agent.log_utils import log


class SandboxHealthMiddleware:
    """沙箱健康哨兵中间件"""

    def __init__(self, sandbox_manager=None):
        self.sandbox_manager = sandbox_manager
        self.failure_count = 0
        self.max_failures = 3

    def before_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Agent 执行前检查沙箱健康状态"""
        if not self.sandbox_manager:
            return state

        try:
            is_healthy = self.sandbox_manager.health_check()
            if not is_healthy:
                self.failure_count += 1
                log.warning(f"⚠️ 沙箱健康检查失败 ({self.failure_count}/{self.max_failures})")

                if self.failure_count >= self.max_failures:
                    log.info("🔄 触发沙箱重建...")
                    self.sandbox_manager.rebuild()
                    self.failure_count = 0
            else:
                self.failure_count = 0
        except Exception as e:
            log.error(f"沙箱健康检查异常: {e}")

        return state
