"""
沙箱熔断器中间件
连续失败时熔断，防止级联故障
"""
import time
from typing import Dict, Any
from agent.log_utils import log


class SandboxCircuitBreakerMiddleware:
    """沙箱熔断器中间件"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold  # 失败阈值
        self.recovery_timeout = recovery_timeout    # 恢复超时（秒）
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed / open / half-open

    def before_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行前检查熔断器状态"""
        if self.state == "open":
            # 检查是否过了恢复时间
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.recovery_timeout:
                self.state = "half-open"
                log.info("🔄 熔断器进入半开状态，尝试恢复")
            else:
                log.warning("⛔ 熔断器打开中，拒绝沙箱操作")
                state["sandbox_blocked"] = True
        return state

    def record_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            log.error(f"💥 熔断器打开！连续失败 {self.failure_count} 次")

    def record_success(self):
        """记录成功"""
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0
            log.info("✅ 熔断器恢复关闭状态")
        elif self.state == "closed":
            self.failure_count = max(0, self.failure_count - 1)
