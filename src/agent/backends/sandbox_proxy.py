"""
沙箱代理层（热替换）
18 个方法显式委托
当沙箱故障时，可以无缝替换后端而不影响上层调用
"""
from typing import Dict, Any, List, Optional
from agent.backends.custom_opensandbox import CustomOpenSandbox
from agent.backends.sandbox_manager import get_sandbox_manager
from agent.log_utils import log


class SandboxBackendProxy:
    """
    沙箱后端代理
    提供稳定的接口，底层支持热替换
    """

    def __init__(self):
        self._backend = None
        self._init_backend()

    def _init_backend(self):
        """初始化后端"""
        try:
            manager = get_sandbox_manager()
            self._backend = CustomOpenSandbox(manager)
            log.info("✅ 沙箱代理初始化完成")
        except Exception as e:
            log.warning(f"⚠️ 沙箱代理初始化失败: {e}，将使用本地执行模式")
            self._backend = None

    def replace_backend(self, new_backend):
        """热替换后端（故障恢复时使用）"""
        old_backend = self._backend
        self._backend = new_backend
        log.info("🔄 沙箱后端已热替换")
        return old_backend

    def is_available(self) -> bool:
        """检查沙箱是否可用"""
        return self._backend is not None

    # ===== 显式委托的方法 =====

    async def execute(self, code: str, timeout: int = None) -> Dict[str, Any]:
        """执行代码"""
        if not self._backend:
            return {"code": -1, "error": "沙箱不可用，使用本地执行"}
        return await self._backend.execute(code, timeout)

    async def read_file(self, path: str) -> str:
        """读取文件"""
        if not self._backend:
            return ""
        return await self._backend.read_file(path)

    async def write_file(self, path: str, content: str):
        """写入文件"""
        if self._backend:
            await self._backend.write_file(path, content)

    async def list_files(self, path: str = ".") -> list:
        """列出文件"""
        if not self._backend:
            return []
        return await self._backend.list_files(path)

    async def health_check(self) -> bool:
        """健康检查"""
        if not self._backend:
            return False
        return await self._backend.health_check()

    def get_sandbox_path(self) -> str:
        """获取沙箱路径"""
        if self._backend:
            return self._backend.get_sandbox_path()
        return "/tmp"

    # 更多方法可以按需添加...


# 全局单例
_sandbox_proxy = None


def get_sandbox_proxy() -> SandboxBackendProxy:
    """获取沙箱代理单例"""
    global _sandbox_proxy
    if _sandbox_proxy is None:
        _sandbox_proxy = SandboxBackendProxy()
    return _sandbox_proxy
