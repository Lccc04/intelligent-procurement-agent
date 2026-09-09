"""
MCP Server 配置
ERP 后端地址 + MCP 监听配置
"""
import os
from dotenv import load_dotenv

load_dotenv()


class ServerConfig:
    host: str = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port: int = int(os.getenv("MCP_SERVER_PORT", "8001"))
    erp_backend_url: str = os.getenv("ERP_BACKEND_URL", "http://127.0.0.1:8002")
    timeout: float = 10.0


config = ServerConfig()
