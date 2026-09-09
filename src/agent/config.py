"""
全局配置
LLM、Store、Checkpointer、沙箱连接参数
"""
import os
from agent.env_utils import load_env

# 加载环境变量
load_env()


class LLMConfig:
    """LLM 配置"""
    model: str = os.getenv("LLM_MODEL", "deepseek-chat")
    api_key: str = os.getenv("LLM_API_KEY", "")
    base_url: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    temperature: float = 0.1
    max_tokens: int = 4096


class MongoDBConfig:
    """MongoDB 配置"""
    url: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name: str = os.getenv("MONGODB_DB", "procurement_agent")


class MCPServerConfig:
    """MCP Server 配置"""
    host: str = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port: int = int(os.getenv("MCP_SERVER_PORT", "8001"))
    erp_backend_url: str = os.getenv("ERP_BACKEND_URL", "http://127.0.0.1:8002")


class APIConfig:
    """FastAPI 配置"""
    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8000"))


class SandboxConfig:
    """沙箱配置"""
    image: str = os.getenv("SANDBOX_IMAGE", "python:3.11-slim")
    mem_limit: str = os.getenv("SANDBOX_MEM_LIMIT", "512m")
    timeout: int = int(os.getenv("SANDBOX_TIMEOUT", "30"))
    work_dir: str = "/workspace"


class AsyncAgentConfig:
    """异步 Agent 配置"""
    protocol_url: str = os.getenv("ASYNC_AGENT_PROTOCOL_URL", "http://127.0.0.1:2024")
    analyst_graph_id: str = "procurement_analyst_async"


# 全局配置实例
llm_config = LLMConfig()
mongo_config = MongoDBConfig()
mcp_config = MCPServerConfig()
api_config = APIConfig()
sandbox_config = SandboxConfig()
async_agent_config = AsyncAgentConfig()
