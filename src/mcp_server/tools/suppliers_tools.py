"""
供应商查询 MCP 工具
"""
from mcp.server.fastmcp import FastMCP
from mcp_server.http_base import http_client


def register_supplier_tools(mcp: FastMCP):
    """注册供应商相关工具"""

    @mcp.tool()
    async def supplier_query(keyword: str = "", category: str = "") -> str:
        """
        查询供应商信息。

        Args:
            keyword: 搜索关键词（供应商名称或类别）
            category: 供应商类别（如：制动系统、电子电气、传动系统等）

        Returns:
            供应商列表 JSON 字符串
        """
        try:
            result = await http_client.get("/api/suppliers", params={
                "keyword": keyword,
                "category": category,
            })
            import json
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"查询供应商失败: {str(e)}"

    @mcp.tool()
    async def supplier_detail(supplier_id: str) -> str:
        """
        获取供应商详细信息。

        Args:
            supplier_id: 供应商ID（如 S001）

        Returns:
            供应商详情 JSON 字符串
        """
        try:
            result = await http_client.get(f"/api/suppliers/{supplier_id}")
            import json
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"获取供应商详情失败: {str(e)}"
