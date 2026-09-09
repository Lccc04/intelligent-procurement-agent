"""
MCP 工具加载客户端
连接 MCP Server，加载所有工具并转换为 LangChain Tool
"""
import asyncio
from typing import List
from langchain_core.tools import Tool
from mcp import ClientSession
from mcp.client.sse import sse_client
from agent.config import mcp_config
from agent.log_utils import log


class MCPClient:
    """MCP 客户端，用于连接 MCP Server 并加载工具"""

    def __init__(self, server_url: str = None):
        self.server_url = server_url or f"http://{mcp_config.host}:{mcp_config.port}/sse"
        self._tools: List[Tool] = []
        self._session = None
        self._stream = None

    async def connect(self):
        """连接 MCP Server"""
        try:
            self._stream = sse_client(self.server_url)
            read, write, _ = await self._stream.__aenter__()
            self._session = ClientSession(read, write)
            await self._session.initialize()
            log.info(f"✅ MCP Server 连接成功: {self.server_url}")
        except Exception as e:
            log.warning(f"⚠️ MCP Server 连接失败: {e}，将使用本地 Mock 工具")
            self._session = None

    async def load_tools(self) -> List[Tool]:
        """加载所有 MCP 工具"""
        if self._session is None:
            log.info("使用本地 Mock 工具（MCP Server 未连接）")
            return self._get_mock_tools()

        try:
            available_tools = await self._session.list_tools()
            tools = []
            for mcp_tool in available_tools.tools:
                langchain_tool = self._convert_mcp_tool(mcp_tool)
                tools.append(langchain_tool)
            log.info(f"✅ 从 MCP Server 加载 {len(tools)} 个工具")
            self._tools = tools
            return tools
        except Exception as e:
            log.error(f"加载 MCP 工具失败: {e}")
            return self._get_mock_tools()

    def _convert_mcp_tool(self, mcp_tool) -> Tool:
        """将 MCP 工具转换为 LangChain Tool"""
        async def _call(**kwargs):
            result = await self._session.call_tool(mcp_tool.name, kwargs)
            if result.content:
                return result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
            return str(result)

        return Tool(
            name=mcp_tool.name,
            description=mcp_tool.description,
            func=_call,
            coroutine=_call,
        )

    def _get_mock_tools(self) -> List[Tool]:
        """获取本地 Mock 工具（当 MCP Server 不可用时）"""
        from agent.tools.mock_tools import get_all_mock_tools
        return get_all_mock_tools()

    async def close(self):
        """关闭连接"""
        if self._session:
            await self._session.close()
        if self._stream:
            await self._stream.__aexit__(None, None, None)


# 全局单例
_mcp_client = None


async def get_mcp_client() -> MCPClient:
    """获取 MCP 客户端单例"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
        await _mcp_client.connect()
    return _mcp_client


async def load_mcp_tools() -> List[Tool]:
    """加载 MCP 工具（便捷函数）"""
    client = await get_mcp_client()
    return await client.load_tools()
