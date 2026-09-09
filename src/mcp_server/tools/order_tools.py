"""
采购订单 MCP 工具
"""
from mcp.server.fastmcp import FastMCP
from mcp_server.http_base import http_client


def register_order_tools(mcp: FastMCP):
    """注册订单相关工具"""

    @mcp.tool()
    async def order_create(part_id: str, quantity: int, unit_price: float, supplier_id: str = "") -> str:
        """
        创建采购订单。

        Args:
            part_id: 物料ID（如 P001）
            quantity: 采购数量
            unit_price: 单价（元）
            supplier_id: 供应商ID（可选，不填则使用物料默认供应商）

        Returns:
            创建结果 JSON 字符串
        """
        try:
            data = {
                "part_id": part_id,
                "quantity": quantity,
                "unit_price": unit_price,
            }
            if supplier_id:
                data["supplier_id"] = supplier_id

            result = await http_client.post("/api/orders", data=data)
            import json
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"创建订单失败: {str(e)}"

    @mcp.tool()
    async def order_update(order_id: str, quantity: int = 0, unit_price: float = 0, status: str = "") -> str:
        """
        更新采购订单。

        Args:
            order_id: 订单ID（如 PO20260501001）
            quantity: 新的采购数量（0表示不修改）
            unit_price: 新的单价（0表示不修改）
            status: 新的订单状态（如：已完成、进行中、已取消）

        Returns:
            更新结果 JSON 字符串
        """
        try:
            data = {}
            if quantity > 0:
                data["quantity"] = quantity
            if unit_price > 0:
                data["unit_price"] = unit_price
            if status:
                data["status"] = status

            result = await http_client.put(f"/api/orders/{order_id}", data=data)
            import json
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"更新订单失败: {str(e)}"

    @mcp.tool()
    async def order_search_details(status: str = "", keyword: str = "") -> str:
        """
        查询订单列表及详情。

        Args:
            status: 订单状态筛选（如：已完成、进行中、待审批）
            keyword: 搜索关键词（订单号或物料名称）

        Returns:
            订单列表 JSON 字符串
        """
        try:
            result = await http_client.get("/api/orders", params={
                "status": status,
                "keyword": keyword,
            })
            import json
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"查询订单失败: {str(e)}"
