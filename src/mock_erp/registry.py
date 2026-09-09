"""Several virtual ERP tenants for integration and multi-source testing."""
from __future__ import annotations

import copy
from typing import Any, Dict


ERP_PROFILES = [
    {"id": "erp-central", "name": "华东制造 ERP", "region": "上海", "currency": "CNY", "price_factor": 1.0, "stock_factor": 1.0},
    {"id": "erp-north", "name": "华北零部件 ERP", "region": "天津", "currency": "CNY", "price_factor": 0.96, "stock_factor": 0.72},
    {"id": "erp-south", "name": "华南维修网络 ERP", "region": "广州", "currency": "CNY", "price_factor": 1.08, "stock_factor": 1.35},
]


def get_erp_catalog():
    return [
        {
            "id": item["id"],
            "name": item["name"],
            "region": item["region"],
            "currency": item["currency"],
            "status": "online",
            "capabilities": ["suppliers", "parts", "orders", "inventory"],
        }
        for item in ERP_PROFILES
    ]


def get_erp_dataset(erp_id: str = "erp-central") -> Dict[str, Any]:
    from agent.tools.mock_tools import PARTS, SUPPLIERS, ORDERS

    profile = next((item for item in ERP_PROFILES if item["id"] == erp_id), None)
    if profile is None:
        raise ValueError(f"虚拟 ERP 不存在: {erp_id}")
    factor = profile["price_factor"]
    stock_factor = profile["stock_factor"]
    suppliers = copy.deepcopy(SUPPLIERS)
    parts = copy.deepcopy(PARTS)
    orders = copy.deepcopy(ORDERS)
    for part in parts:
        part["price"] = round(part["price"] * factor, 2)
        part["stock"] = max(0, round(part["stock"] * stock_factor))
    for order in orders:
        order["unit_price"] = round(order["unit_price"] * factor, 2)
        order["total"] = round(order["quantity"] * order["unit_price"], 2)
        order["erp_id"] = erp_id
    return {"erp": next(item for item in get_erp_catalog() if item["id"] == erp_id), "suppliers": suppliers, "parts": parts, "orders": orders}
