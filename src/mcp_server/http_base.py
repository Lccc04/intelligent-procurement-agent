"""
HTTP 基础客户端
httpx AsyncClient（连接池、超时）
"""
import httpx
from mcp_server.server_config import config


class HttpBase:
    """HTTP 客户端基类"""

    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=config.erp_backend_url,
            timeout=config.timeout,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )

    async def get(self, path: str, params: dict = None) -> dict:
        """GET 请求"""
        resp = await self.client.get(path, params=params or {})
        resp.raise_for_status()
        return resp.json()

    async def post(self, path: str, data: dict = None) -> dict:
        """POST 请求"""
        resp = await self.client.post(path, json=data or {})
        resp.raise_for_status()
        return resp.json()

    async def put(self, path: str, data: dict = None) -> dict:
        """PUT 请求"""
        resp = await self.client.put(path, json=data or {})
        resp.raise_for_status()
        return resp.json()

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 全局实例
http_client = HttpBase()
