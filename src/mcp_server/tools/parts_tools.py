"""
物料查询 MCP 工具
"""
from mcp.server.fastmcp import FastMCP
from mcp_server.http_base import http_client


def register_parts_tools(mcp: FastMCP):
    """注册物料相关工具"""

    @mcp.tool()
    async def part_query(keyword: str = "", category: str = "") -> str:
        """
        查询物料信息。

        Args:
            keyword: 搜索关键词（物料名称或规格）
            category: 物料类别（如：制动系统、电子电气等）

        Returns:
            物料列表 JSON 字符串
        """
        try:
            result = await http_client.get("/api/parts", params={
                "keyword": keyword,
                "category": category,
            })
            import json
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"查询物料失败: {str(e)}"

    @mcp.tool()
    async def part_search(keyword: str) -> str:
        """
        模糊搜索物料（按名称或规格）。

        Args:
            keyword: 搜索关键词

        Returns:
            物料列表 JSON 字符串
        """
        try:
            result = await http_client.get("/api/parts", params={"keyword": keyword})
            import json
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"搜索物料失败: {str(e)}"

    @mcp.tool()
    async def part_by_supplier(supplier_id: str) -> str:
        """
        按供应商查询其供应的物料列表。

        Args:
            supplier_id: 供应商ID（如 S001）

        Returns:
            物料列表 JSON 字符串
        """
        try:
            result = await http_client.get(f"/api/parts/by_supplier/{supplier_id}")
            import json
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"按供应商查询物料失败: {str(e)}"
