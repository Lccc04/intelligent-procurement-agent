"""
Mock ERP 服务
模拟 Java ERP 系统的后端接口，提供供应商、物料、订单、库存等数据
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="Mock ERP Service")

# ===== 模拟数据 =====

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


# ===== 请求模型 =====

class OrderCreateRequest(BaseModel):
    part_id: str
    quantity: int
    unit_price: float
    supplier_id: Optional[str] = None


class OrderUpdateRequest(BaseModel):
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    status: Optional[str] = None


# ===== 接口 =====

@app.get("/api/suppliers")
async def query_suppliers(keyword: str = "", category: str = ""):
    """供应商查询"""
    result = SUPPLIERS
    if keyword:
        result = [s for s in result if keyword in s["name"] or keyword in s["category"]]
    if category:
        result = [s for s in result if s["category"] == category]
    return {"code": 0, "data": result, "total": len(result)}


@app.get("/api/suppliers/{supplier_id}")
async def get_supplier(supplier_id: str):
    """获取供应商详情"""
    for s in SUPPLIERS:
        if s["id"] == supplier_id:
            return {"code": 0, "data": s}
    raise HTTPException(status_code=404, detail="供应商不存在")


@app.get("/api/parts")
async def query_parts(keyword: str = "", category: str = "", supplier_id: str = ""):
    """物料查询"""
    result = PARTS
    if keyword:
        result = [p for p in result if keyword in p["name"] or keyword in p["spec"]]
    if category:
        result = [p for p in result if p["category"] == category]
    if supplier_id:
        result = [p for p in result if p["supplier_id"] == supplier_id]
    return {"code": 0, "data": result, "total": len(result)}


@app.get("/api/parts/{part_id}")
async def get_part(part_id: str):
    """获取物料详情"""
    for p in PARTS:
        if p["id"] == part_id:
            return {"code": 0, "data": p}
    raise HTTPException(status_code=404, detail="物料不存在")


@app.get("/api/parts/by_supplier/{supplier_id}")
async def get_parts_by_supplier(supplier_id: str):
    """按供应商查询物料"""
    result = [p for p in PARTS if p["supplier_id"] == supplier_id]
    return {"code": 0, "data": result, "total": len(result)}


@app.post("/api/orders")
async def create_order(req: OrderCreateRequest):
    """创建采购订单"""
    # 查找物料
    part = None
    for p in PARTS:
        if p["id"] == req.part_id:
            part = p
            break
    if not part:
        raise HTTPException(status_code=404, detail="物料不存在")

    supplier_id = req.supplier_id or part["supplier_id"]
    total = req.quantity * req.unit_price
    order_id = f"PO202605{len(ORDERS)+1:04d}"

    order = {
        "id": order_id,
        "part_id": req.part_id,
        "part_name": part["name"],
        "quantity": req.quantity,
        "unit_price": req.unit_price,
        "total": total,
        "supplier_id": supplier_id,
        "status": "待审批",
        "create_time": "2026-05-10 10:00:00",
    }
    ORDERS.append(order)
    return {"code": 0, "data": order, "message": "订单创建成功"}


@app.put("/api/orders/{order_id}")
async def update_order(order_id: str, req: OrderUpdateRequest):
    """更新订单"""
    for o in ORDERS:
        if o["id"] == order_id:
            if req.quantity:
                o["quantity"] = req.quantity
                o["total"] = req.quantity * o["unit_price"]
            if req.unit_price:
                o["unit_price"] = req.unit_price
                o["total"] = o["quantity"] * req.unit_price
            if req.status:
                o["status"] = req.status
            return {"code": 0, "data": o, "message": "订单更新成功"}
    raise HTTPException(status_code=404, detail="订单不存在")


@app.get("/api/orders")
async def search_orders(status: str = "", keyword: str = ""):
    """订单查询"""
    result = ORDERS
    if status:
        result = [o for o in result if o["status"] == status]
    if keyword:
        result = [o for o in result if keyword in o["part_name"] or keyword in o["id"]]
    return {"code": 0, "data": result, "total": len(result)}


@app.get("/api/orders/{order_id}")
async def get_order_detail(order_id: str):
    """订单详情"""
    for o in ORDERS:
        if o["id"] == order_id:
            return {"code": 0, "data": o}
    raise HTTPException(status_code=404, detail="订单不存在")


@app.get("/api/inventory/warning")
async def inventory_warning(threshold: int = 100):
    """库存预警"""
    warning = [p for p in PARTS if p["stock"] <= threshold]
    return {"code": 0, "data": warning, "total": len(warning)}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)
