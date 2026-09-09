"""
MCP Server 入口
FastMCP 启动，注册所有 ERP 工具
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP
from mcp_server.server_config import config
from mcp_server.tools.suppliers_tools import register_supplier_tools
from mcp_server.tools.parts_tools import register_parts_tools
from mcp_server.tools.order_tools import register_order_tools
from mcp_server.tools.inventory_tools import register_inventory_tools

# 创建 MCP Server 实例
mcp = FastMCP(
    "Procurement-ERP",
    host=config.host,
    port=config.port,
)

# 注册所有工具
register_supplier_tools(mcp)
register_parts_tools(mcp)
register_order_tools(mcp)
register_inventory_tools(mcp)


def main():
    """启动 MCP Server"""
    print(f"🚀 MCP Server 启动: http://{config.host}:{config.port}")
    print(f"📡 ERP 后端: {config.erp_backend_url}")
    print(f"🔧 已注册工具: supplier_query, supplier_detail, part_query, part_search, part_by_supplier, order_create, order_update, order_search_details, inventory_warning")
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
