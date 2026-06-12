"""
Order Management REST API with FastAPI.

Endpoints:
  GET /orders         -- list/search/filter orders
  GET /orders/{id}    -- get a single order by ID
  GET /stats          -- aggregate order statistics

Query parameters for GET /orders:
  search    : keyword match across order number, customer name, notes
  customer  : filter by customer name/email (partial match)
  start_date: ISO date, inclusive (YYYY-MM-DD)
  end_date  : ISO date, inclusive (YYYY-MM-DD)
  status    : pending | shipped | delivered | cancelled | all (default)
  limit     : results per page (default 20, max 100)
  offset    : pagination offset (default 0)
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_ORDERS: list[dict] = [
    {
        "id": "ORD-1001",
        "order_number": "ORD-1001",
        "customer_name": "Acme Corp",
        "customer_email": "orders@acmecorp.com",
        "status": "delivered",
        "created_at": "2026-05-01T10:30:00",
        "updated_at": "2026-05-05T14:00:00",
        "total": 1499.97,
        "currency": "USD",
        "items": [
            {"sku": "WDG-001", "name": "Widget Pro", "qty": 3, "unit_price": 499.99},
        ],
        "notes": "Standard delivery, left at front door",
    },
    {
        "id": "ORD-1002",
        "order_number": "ORD-1002",
        "customer_name": "Globex Industries",
        "customer_email": "procurement@globex.com",
        "status": "shipped",
        "created_at": "2026-05-15T09:15:00",
        "updated_at": "2026-05-16T11:00:00",
        "total": 8750.00,
        "currency": "USD",
        "items": [
            {"sku": "SRV-200", "name": "Server Rack 42U", "qty": 5, "unit_price": 1750.00},
        ],
        "notes": "Loading dock delivery required",
    },
    {
        "id": "ORD-1003",
        "order_number": "ORD-1003",
        "customer_name": "Initech",
        "customer_email": "admin@initech.com",
        "status": "pending",
        "created_at": "2026-06-01T08:00:00",
        "updated_at": "2026-06-01T08:00:00",
        "total": 299.50,
        "currency": "USD",
        "items": [
            {"sku": "CBL-050", "name": "USB-C Cable 2m", "qty": 10, "unit_price": 14.99},
            {"sku": "ADP-010", "name": "Power Adapter 65W", "qty": 5, "unit_price": 29.99},
        ],
        "notes": "",
    },
    {
        "id": "ORD-1004",
        "order_number": "ORD-1004",
        "customer_name": "Acme Corp",
        "customer_email": "orders@acmecorp.com",
        "status": "pending",
        "created_at": "2026-06-10T16:45:00",
        "updated_at": "2026-06-10T16:45:00",
        "total": 6200.00,
        "currency": "USD",
        "items": [
            {"sku": "LAP-300", "name": "Laptop 15\" i7", "qty": 4, "unit_price": 1550.00},
        ],
        "notes": "Rush order -- needed by Friday",
    },
    {
        "id": "ORD-1005",
        "order_number": "ORD-1005",
        "customer_name": "Umbrella Corp",
        "customer_email": "sales@umbrellacorp.biz",
        "status": "cancelled",
        "created_at": "2026-05-20T12:00:00",
        "updated_at": "2026-05-21T09:30:00",
        "total": 420.00,
        "currency": "USD",
        "items": [
            {"sku": "MON-015", "name": "Monitor Stand", "qty": 12, "unit_price": 35.00},
        ],
        "notes": "Cancelled by customer -- duplicate order",
    },
    {
        "id": "ORD-1006",
        "order_number": "ORD-1006",
        "customer_name": "Globex Industries",
        "customer_email": "procurement@globex.com",
        "status": "delivered",
        "created_at": "2026-04-10T07:30:00",
        "updated_at": "2026-04-14T10:00:00",
        "total": 3400.00,
        "currency": "USD",
        "items": [
            {"sku": "SWT-001", "name": "Network Switch 48-port", "qty": 2, "unit_price": 1700.00},
        ],
        "notes": "Installed in server room B",
    },
    {
        "id": "ORD-1007",
        "order_number": "ORD-1007",
        "customer_name": "Initech",
        "customer_email": "admin@initech.com",
        "status": "shipped",
        "created_at": "2026-06-05T14:20:00",
        "updated_at": "2026-06-06T08:00:00",
        "total": 189.90,
        "currency": "USD",
        "items": [
            {"sku": "MOU-007", "name": "Ergonomic Mouse", "qty": 3, "unit_price": 63.30},
        ],
        "notes": "",
    },
    {
        "id": "ORD-1008",
        "order_number": "ORD-1008",
        "customer_name": "Hooli",
        "customer_email": "purchasing@hooli.com",
        "status": "delivered",
        "created_at": "2026-03-28T11:00:00",
        "updated_at": "2026-04-02T16:00:00",
        "total": 12500.00,
        "currency": "USD",
        "items": [
            {"sku": "SRV-400", "name": "GPU Server Node", "qty": 1, "unit_price": 12500.00},
        ],
        "notes": "White-glove installation requested",
    },
]

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Order Management API",
    version="1.0.0",
    description="REST API for searching, filtering, and managing orders.",
)


# ----- Models -----

class OrderItem(BaseModel):
    sku: str
    name: str
    qty: int
    unit_price: float


class Order(BaseModel):
    id: str
    order_number: str
    customer_name: str
    customer_email: str
    status: str
    created_at: str
    updated_at: str
    total: float
    currency: str
    items: list[OrderItem]
    notes: str


class OrderListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    orders: list[Order]


class StatsResponse(BaseModel):
    period: str
    total_orders: int
    total_revenue: float
    by_status: dict[str, int]


# ----- Helpers -----

def _match_order(order: dict, search: Optional[str], customer: Optional[str],
                 start_date: Optional[date], end_date: Optional[date],
                 status: Optional[str]) -> bool:
    """Return True if *order* satisfies all filter criteria."""
    # Status filter
    if status and status != "all":
        if order["status"] != status:
            return False

    # Keyword search in order_number, customer_name, notes
    if search:
        q = search.lower()
        haystack = " ".join([
            order["order_number"],
            order["customer_name"],
            order["notes"],
        ]).lower()
        if q not in haystack:
            return False

    # Customer filter (partial match on name or email)
    if customer:
        c = customer.lower()
        if c not in order["customer_name"].lower() and c not in order["customer_email"].lower():
            return False

    # Date range filter (created_at)
    order_date = datetime.fromisoformat(order["created_at"]).date()
    if start_date and order_date < start_date:
        return False
    if end_date and order_date > end_date:
        return False

    return True


# ----- Endpoints -----

@app.get("/orders", response_model=OrderListResponse)
def list_orders(
    search: Optional[str] = Query(None, description="Keyword search across order number, customer, notes"),
    customer: Optional[str] = Query(None, description="Filter by customer name or email (partial match)"),
    start_date: Optional[date] = Query(None, description="Earliest creation date (ISO, inclusive)"),
    end_date: Optional[date] = Query(None, description="Latest creation date (ISO, inclusive)"),
    status: Optional[str] = Query("all", description="Order status: pending|shipped|delivered|cancelled|all"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
):
    matched = [
        o for o in SAMPLE_ORDERS
        if _match_order(o, search, customer, start_date, end_date, status)
    ]
    page = matched[offset : offset + limit]
    return OrderListResponse(
        total=len(matched),
        limit=limit,
        offset=offset,
        orders=[Order(**o) for o in page],
    )


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    for o in SAMPLE_ORDERS:
        if o["id"] == order_id:
            return Order(**o)
    raise HTTPException(status_code=404, detail=f"Order '{order_id}' not found")


@app.get("/stats", response_model=StatsResponse)
def get_stats(
    period: str = Query("all", description="Period: today|yesterday|this_week|this_month|last_month|all"),
):
    now = datetime.utcnow().date()
    today = now

    if period == "today":
        start = today
        end = today
    elif period == "yesterday":
        from datetime import timedelta
        start = end = today - timedelta(days=1)
    elif period == "this_week":
        from datetime import timedelta
        start = today - timedelta(days=today.weekday())
        end = today
    elif period == "this_month":
        start = today.replace(day=1)
        end = today
    elif period == "last_month":
        first_of_this = today.replace(day=1)
        from datetime import timedelta
        last_day_prev = first_of_this - timedelta(days=1)
        start = last_day_prev.replace(day=1)
        end = last_day_prev
    else:  # "all"
        start = date.min
        end = date.max

    filtered = []
    for o in SAMPLE_ORDERS:
        order_date = datetime.fromisoformat(o["created_at"]).date()
        if start <= order_date <= end:
            filtered.append(o)

    by_status: dict[str, int] = {}
    total_rev = 0.0
    for o in filtered:
        by_status[o["status"]] = by_status.get(o["status"], 0) + 1
        total_rev += o["total"]

    return StatsResponse(
        period=period,
        total_orders=len(filtered),
        total_revenue=round(total_rev, 2),
        by_status=by_status,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import uvicorn
    host = os.environ.get("ORDER_API_HOST", "127.0.0.1")
    port = int(os.environ.get("ORDER_API_PORT", "8080"))
    uvicorn.run("order_api:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()
