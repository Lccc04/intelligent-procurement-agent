"""
库存预警 MCP 工具
"""
from mcp.server.fastmcp import FastMCP
from mcp_server.http_base import http_client


def register_inventory_tools(mcp: FastMCP):
    """注册库存相关工具"""

    @mcp.tool()
    async def inventory_warning(threshold: int = 100) -> str:
        """
        查询库存预警信息。

        Args:
            threshold: 库存预警阈值（库存低于此值则预警，默认100）

        Returns:
            库存预警列表 JSON 字符串
        """
        try:
            result = await http_client.get("/api/inventory/warning", params={
                "threshold": threshold,
            })
            import json
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"查询库存预警失败: {str(e)}"
