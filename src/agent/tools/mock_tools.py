"""
本地 Mock 工具
当 MCP Server 不可用时，使用这些本地工具保证项目可运行
直接调用 Mock ERP 的数据
"""
import json
from typing import List
from langchain_core.tools import tool

# ===== Mock 数据（与 Mock ERP 保持一致） =====

SUPPLIERS = [
    {"id": "S001", "name": "博世汽车部件有限公司", "category": "制动系统", "rating": 4.8, "country": "德国", "contact": "021-12345678"},
    {"id": "S002", "name": "大陆集团电子系统", "category": "电子电气", "rating": 4.6, "country": "德国", "contact": "021-23456789"},
    {"id": "S003", "name": "采埃孚传动技术", "category": "传动系统", "rating": 4.7, "country": "德国", "contact": "021-34567890"},
    {"id": "S004", "name": "宁波华翔电子", "category": "内饰件", "rating": 4.3, "country": "中国", "contact": "0574-45678901"},
    {"id": "S005", "name": "福耀玻璃工业集团", "category": "玻璃", "rating": 4.9, "country": "中国", "contact": "0591-56789012"},
]

PARTS = [
    {"id": "P001", "name": "前刹车片", "category": "制动系统", "spec": "大众迈腾B8", "unit": "套", "price": 280.00, "supplier_id": "S001", "stock": 500},
    {"id": "P002", "name": "后刹车片", "category": "制动系统", "spec": "大众迈腾B8", "unit": "套", "price": 220.00, "supplier_id": "S001", "stock": 600},
    {"id": "P003", "name": "刹车盘", "category": "制动系统", "spec": "大众迈腾B8前", "unit": "个", "price": 450.00, "supplier_id": "S001", "stock": 200},
    {"id": "P004", "name": "ECU控制单元", "category": "电子电气", "spec": "发动机管理", "unit": "个", "price": 1280.00, "supplier_id": "S002", "stock": 50},
    {"id": "P005", "name": "车身控制模块", "category": "电子电气", "spec": "BCM", "unit": "个", "price": 860.00, "supplier_id": "S002", "stock": 80},
    {"id": "P006", "name": "变速箱离合器", "category": "传动系统", "spec": "7速双离合", "unit": "个", "price": 3200.00, "supplier_id": "S003", "stock": 30},
    {"id": "P007", "name": "前挡风玻璃", "category": "玻璃", "spec": "大众迈腾B8", "unit": "块", "price": 1200.00, "supplier_id": "S005", "stock": 100},
    {"id": "P008", "name": "仪表台总成", "category": "内饰件", "spec": "黑色", "unit": "个", "price": 2400.00, "supplier_id": "S004", "stock": 40},
]

ORDERS = [
    {"id": "PO20260501001", "part_id": "P001", "part_name": "前刹车片", "quantity": 100, "unit_price": 280.00, "total": 28000.00, "supplier_id": "S001", "status": "已完成", "create_time": "2026-05-01 10:30:00"},
    {"id": "PO20260503002", "part_id": "P004", "part_name": "ECU控制单元", "quantity": 20, "unit_price": 1280.00, "total": 25600.00, "supplier_id": "S002", "status": "已完成", "create_time": "2026-05-03 14:20:00"},
    {"id": "PO20260508003", "part_id": "P007", "part_name": "前挡风玻璃", "quantity": 50, "unit_price": 1200.00, "total": 60000.00, "supplier_id": "S005", "status": "进行中", "create_time": "2026-05-08 09:15:00"},
]


def _mock_response(data, total: int = None, message: str = None, **extra) -> str:
    """统一包装 Mock ERP 返回，显式暴露来源和数据限制。"""
    payload = {
        "code": 0,
        "data": data,
        "source": "mock_erp",
        "data_scope": "current_snapshot",
        "limitations": [
            "演示数据，不代表真实 ERP 生产数据",
            "当前 Mock 数据不包含历史价格序列，不能直接推断上涨、下降或稳定趋势",
        ],
        **extra,
    }
    if total is not None:
        payload["total"] = total
    if message:
        payload["message"] = message
    return json.dumps(payload, ensure_ascii=False, indent=2)


@tool
def supplier_query(keyword: str = "", category: str = "") -> str:
    """
    查询供应商信息。

    Args:
        keyword: 搜索关键词（供应商名称或类别）
        category: 供应商类别（如：制动系统、电子电气、传动系统等）
    """
    result = SUPPLIERS
    if keyword:
        result = [s for s in result if keyword in s["name"] or keyword in s["category"]]
    if category:
        result = [s for s in result if s["category"] == category]
    return _mock_response(result, total=len(result))


@tool
def supplier_detail(supplier_id: str) -> str:
    """
    获取供应商详细信息。

    Args:
        supplier_id: 供应商ID（如 S001）
    """
    for s in SUPPLIERS:
        if s["id"] == supplier_id:
            return _mock_response(s)
    return json.dumps({"code": -1, "message": "供应商不存在"}, ensure_ascii=False)


@tool
def part_query(keyword: str = "", category: str = "") -> str:
    """
    查询物料信息。

    Args:
        keyword: 搜索关键词（物料名称或规格）
        category: 物料类别（如：制动系统、电子电气等）
    """
    result = PARTS
    if keyword:
        result = [p for p in result if keyword in p["name"] or keyword in p["spec"]]
    if category:
        result = [p for p in result if p["category"] == category]
    return _mock_response(result, total=len(result))


@tool
def part_search(keyword: str) -> str:
    """
    模糊搜索物料（按名称或规格）。

    Args:
        keyword: 搜索关键词
    """
    result = [p for p in PARTS if keyword in p["name"] or keyword in p["spec"]]
    return _mock_response(result, total=len(result))


@tool
def part_by_supplier(supplier_id: str) -> str:
    """
    按供应商查询其供应的物料列表。

    Args:
        supplier_id: 供应商ID（如 S001）
    """
    result = [p for p in PARTS if p["supplier_id"] == supplier_id]
    return _mock_response(result, total=len(result))


@tool
def order_create(part_id: str, quantity: int, unit_price: float, supplier_id: str = "") -> str:
    """
    创建采购订单。

    Args:
        part_id: 物料ID（如 P001）
        quantity: 采购数量
        unit_price: 单价（元）
        supplier_id: 供应商ID（可选，不填则使用物料默认供应商）
    """
    part = None
    for p in PARTS:
        if p["id"] == part_id:
            part = p
            break
    if not part:
        return json.dumps({"code": -1, "message": "物料不存在"}, ensure_ascii=False)

    sid = supplier_id or part["supplier_id"]
    total = quantity * unit_price
    order_id = f"PO202605{len(ORDERS)+1:04d}"

    order = {
        "id": order_id,
        "part_id": part_id,
        "part_name": part["name"],
        "quantity": quantity,
        "unit_price": unit_price,
        "total": total,
        "supplier_id": sid,
        "status": "待审批",
        "create_time": "2026-05-10 10:00:00",
    }
    ORDERS.append(order)
    return _mock_response(order, message="订单创建成功")


@tool
def order_update(order_id: str, quantity: int = 0, unit_price: float = 0, status: str = "") -> str:
    """
    更新采购订单。

    Args:
        order_id: 订单ID（如 PO20260501001）
        quantity: 新的采购数量（0表示不修改）
        unit_price: 新的单价（0表示不修改）
        status: 新的订单状态（如：已完成、进行中、已取消）
    """
    for o in ORDERS:
        if o["id"] == order_id:
            if quantity > 0:
                o["quantity"] = quantity
                o["total"] = quantity * o["unit_price"]
            if unit_price > 0:
                o["unit_price"] = unit_price
                o["total"] = o["quantity"] * unit_price
            if status:
                o["status"] = status
            return _mock_response(o, message="订单更新成功")
    return json.dumps({"code": -1, "message": "订单不存在"}, ensure_ascii=False)


@tool
def order_search_details(status: str = "", keyword: str = "") -> str:
    """
    查询订单列表及详情。

    Args:
        status: 订单状态筛选（如：已完成、进行中、待审批）
        keyword: 搜索关键词（订单号或物料名称）
    """
    result = ORDERS
    if status:
        result = [o for o in result if o["status"] == status]
    if keyword:
        result = [o for o in result if keyword in o["part_name"] or keyword in o["id"]]
    return _mock_response(result, total=len(result))


@tool
def inventory_warning(threshold: int = 100) -> str:
    """
    查询库存预警信息。

    Args:
        threshold: 库存预警阈值（库存低于此值则预警，默认100）
    """
    warning = [p for p in PARTS if p["stock"] <= threshold]
    return _mock_response(warning, total=len(warning), threshold=threshold)


def get_all_mock_tools() -> List:
    """获取所有 Mock 工具"""
    return [
        supplier_query,
        supplier_detail,
        part_query,
        part_search,
        part_by_supplier,
        order_create,
        order_update,
        order_search_details,
        inventory_warning,
    ]
