"""
沙箱创建 + Python 环境初始化
"""
from typing import List
from agent.backends.sandbox_manager import get_sandbox_manager
from agent.log_utils import log


def setup_sandbox(user_id: str = "default", packages: List[str] = None):
    """
    初始化沙箱环境
    1. 创建容器
    2. 安装必要的 Python 包
    3. 创建工作目录
    """
    manager = get_sandbox_manager()

    # 创建容器
    if not manager.create(user_id):
        log.warning("⚠️ 沙箱创建失败，将使用本地执行")
        return False

    # 安装 Python 包
    if packages:
        log.info(f"📦 正在安装 Python 包: {packages}")
        pkg_str = " ".join(packages)
        result = manager.execute(f"pip install {pkg_str} -q")
        if result["code"] == 0:
            log.info("✅ Python 包安装完成")
        else:
            log.warning(f"⚠️ Python 包安装失败: {result.get('error', result.get('output', ''))}")

    # 创建工作目录
    manager.execute("mkdir -p /workspace /skills /analysis /data")

    return True


def ensure_sandbox_ready(user_id: str = "default"):
    """确保沙箱就绪，未创建则创建"""
    manager = get_sandbox_manager()
    if manager.health_check():
        return True
    return setup_sandbox(user_id)
