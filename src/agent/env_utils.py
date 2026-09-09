"""
环境变量加载工具
从 .env 文件加载配置到 os.environ
"""
import os
from dotenv import load_dotenv


def load_env(env_file: str = None):
    """加载环境变量"""
    if env_file and os.path.exists(env_file):
        load_dotenv(env_file)
    else:
        # 向上查找 .env 文件
        current = os.path.dirname(os.path.abspath(__file__))
        for _ in range(5):
            candidate = os.path.join(current, ".env")
            if os.path.exists(candidate):
                load_dotenv(candidate)
                break
            current = os.path.dirname(current)


def get_env(key: str, default: str = None) -> str:
    """获取环境变量"""
    return os.environ.get(key, default)
