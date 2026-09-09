"""
Docker 沙箱后端封装
注入 SANDBOX_PATH 环境变量
"""
import os
from typing import Dict, Any, Optional
from agent.backends.sandbox_manager import SandboxManager, get_sandbox_manager
from agent.log_utils import log


class CustomOpenSandbox:
    """
    为 Agent 提供统一沙箱操作接口，底层使用 Docker SDK
    """

    def __init__(self, manager: SandboxManager = None):
        self.manager = manager or get_sandbox_manager()
        self.sandbox_path = os.environ.get("SANDBOX_PATH", "/workspace")

    async def execute(self, code: str, timeout: int = None) -> Dict[str, Any]:
        """执行代码"""
        return self.manager.execute(code, timeout)

    async def read_file(self, path: str) -> str:
        """读取文件"""
        result = self.manager.execute(f"cat {path}")
        return result.get("output", "")

    async def write_file(self, path: str, content: str):
        """写入文件"""
        escaped = content.replace("'", "'\\''")
        self.manager.execute(f"echo '{escaped}' > {path}")

    async def list_files(self, path: str = ".") -> list:
        """列出文件"""
        result = self.manager.execute(f"ls -la {path}")
        output = result.get("output", "")
        return [line for line in output.split("\n") if line.strip()]

    async def health_check(self) -> bool:
        """健康检查"""
        return self.manager.health_check()

    def get_sandbox_path(self) -> str:
        """获取沙箱工作路径"""
        return self.sandbox_path
