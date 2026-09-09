"""
沙箱生命周期管理
5 态：预热→缓存→Mongo→新建
基于 Docker SDK 的容器沙箱生命周期管理
"""
import time
import uuid
from typing import Dict, Any, Optional
from agent.log_utils import log
from agent.config import sandbox_config


class SandboxManager:
    """沙箱管理器 - 管理容器生命周期"""

    def __init__(self):
        self.container = None
        self.container_id = None
        self.status = "not_created"  # not_created / starting / running / stopped / error
        self.created_at = None
        self.user_id = None
        self._docker_client = None

    def _get_docker_client(self):
        """获取 Docker 客户端（懒加载）"""
        if self._docker_client is None:
            try:
                import docker
                self._docker_client = docker.from_env()
                log.info("✅ Docker 客户端连接成功")
            except Exception as e:
                log.warning(f"⚠️ Docker 客户端连接失败: {e}，沙箱功能将不可用")
                self._docker_client = None
        return self._docker_client

    def create(self, user_id: str = "default") -> bool:
        """创建沙箱容器"""
        client = self._get_docker_client()
        if not client:
            log.warning("⚠️ Docker 不可用，跳过沙箱创建")
            return False

        try:
            self.status = "starting"
            self.user_id = user_id

            log.info(f"🔧 正在创建沙箱容器: image={sandbox_config.image}")

            # 启动容器
            self.container = client.containers.run(
                sandbox_config.image,
                command="sleep infinity",  # 保持运行
                detach=True,
                mem_limit=sandbox_config.mem_limit,
                network_disabled=True,  # 禁网（安全）
                working_dir=sandbox_config.work_dir,
            )

            self.container_id = self.container.id
            self.status = "running"
            self.created_at = time.time()

            log.info(f"✅ 沙箱容器创建成功: id={self.container_id[:12]}")
            return True

        except Exception as e:
            log.error(f"❌ 沙箱容器创建失败: {e}")
            self.status = "error"
            return False

    def health_check(self) -> bool:
        """健康检查"""
        if not self.container or self.status != "running":
            return False

        try:
            self.container.reload()
            return self.container.status == "running"
        except Exception as e:
            log.error(f"沙箱健康检查失败: {e}")
            return False

    def execute(self, code: str, timeout: int = None) -> Dict[str, Any]:
        """在沙箱中执行代码"""
        if not self.container or self.status != "running":
            return {"code": -1, "error": "沙箱未运行"}

        try:
            timeout = timeout or sandbox_config.timeout

            # 将代码写入容器并执行
            exec_result = self.container.exec_run(
                f"python -c \"{code.replace('\"', '\\\"')}\"",
                timeout=timeout,
            )

            return {
                "code": exec_result.exit_code,
                "output": exec_result.output.decode("utf-8", errors="replace"),
            }
        except Exception as e:
            log.error(f"沙箱执行失败: {e}")
            return {"code": -1, "error": str(e)}

    def upload_file(self, local_path: str, container_path: str):
        """上传文件到沙箱"""
        if not self.container:
            return False
        try:
            with open(local_path, "rb") as f:
                self.container.put_archive(
                    path="/".join(container_path.split("/")[:-1]),
                    data=f.read(),
                )
            return True
        except Exception as e:
            log.error(f"文件上传失败: {e}")
            return False

    def download_file(self, container_path: str, local_path: str):
        """从沙箱下载文件"""
        if not self.container:
            return False
        try:
            bits, stat = self.container.get_archive(container_path)
            with open(local_path, "wb") as f:
                for chunk in bits:
                    f.write(chunk)
            return True
        except Exception as e:
            log.error(f"文件下载失败: {e}")
            return False

    def rebuild(self) -> bool:
        """重建沙箱（故障恢复）"""
        log.info("🔄 正在重建沙箱...")
        self.destroy()
        return self.create(self.user_id or "default")

    def destroy(self):
        """销毁沙箱容器"""
        if self.container:
            try:
                self.container.stop(timeout=5)
                self.container.remove()
                log.info(f"🗑️ 沙箱容器已销毁: id={self.container_id[:12]}")
            except Exception as e:
                log.error(f"沙箱销毁失败: {e}")
            finally:
                self.container = None
                self.container_id = None
                self.status = "not_created"


# 全局单例
_sandbox_manager = None


def get_sandbox_manager() -> SandboxManager:
    """获取沙箱管理器单例"""
    global _sandbox_manager
    if _sandbox_manager is None:
        _sandbox_manager = SandboxManager()
    return _sandbox_manager
