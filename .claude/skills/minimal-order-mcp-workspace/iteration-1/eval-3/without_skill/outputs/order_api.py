"""
Order API -- in-memory order database with REST endpoints.

Run with:
    python order_api.py
or:
    uvicorn order_api:app --host 127.0.0.1 --port 8000
"""

import os
from datetime import date, timedelta

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# =============================================================================
# In-memory sample data (7 orders)
# =============================================================================

SAMPLE_ORDERS: list[dict] = [
    {
        "order_id": "ORD-001",
        "customer_name": "Alice Johnson",
        "customer_email": "alice@example.com",
        "status": "delivered",
        "created_at": "2026-01-15",
        "total": 149.97,
        "items": [
            {"product": "Wireless Mouse", "quantity": 2, "unit_price": 29.99},
            {"product": "USB-C Hub", "quantity": 1, "unit_price": 89.99},
        ],
    },
    {
        "order_id": "ORD-002",
        "customer_name": "Bob Smith",
        "customer_email": "bob@example.com",
        "status": "shipped",
        "created_at": "2026-02-20",
        "total": 1299.00,
        "items": [
            {"product": 'Monitor 27"', "quantity": 1, "unit_price": 999.00},
            {"product": "HDMI Cable", "quantity": 2, "unit_price": 150.00},
        ],
    },
    {
        "order_id": "ORD-003",
        "customer_name": "Alice Johnson",
        "customer_email": "alice@example.com",
        "status": "pending",
        "created_at": "2026-03-10",
        "total": 45.51,
        "items": [
            {"product": "Notebook", "quantity": 3, "unit_price": 15.17},
        ],
    },
    {
        "order_id": "ORD-004",
        "customer_name": "Charlie Brown",
        "customer_email": "charlie@example.com",
        "status": "cancelled",
        "created_at": "2026-04-05",
        "total": 299.99,
        "items": [
            {"product": "Mechanical Keyboard", "quantity": 1, "unit_price": 299.99},
        ],
    },
    {
        "order_id": "ORD-005",
        "customer_name": "Diana Prince",
        "customer_email": "diana@example.com",
        "status": "delivered",
        "created_at": "2026-05-01",
        "total": 89.98,
        "items": [
            {"product": "Webcam HD", "quantity": 1, "unit_price": 89.98},
        ],
    },
    {
        "order_id": "ORD-006",
        "customer_name": "Bob Smith",
        "customer_email": "bob@example.com",
        "status": "pending",
        "created_at": "2026-05-15",
        "total": 549.50,
        "items": [
            {"product": "Standing Desk", "quantity": 1, "unit_price": 450.00},
            {"product": "Cable Management Tray", "quantity": 1, "unit_price": 99.50},
        ],
    },
    {
        "order_id": "ORD-007",
        "customer_name": "Eve Martinez",
        "customer_email": "eve@example.com",
        "status": "shipped",
        "created_at": "2026-06-01",
        "total": 78.50,
        "items": [
            {"product": "Laptop Stand", "quantity": 1, "unit_price": 49.99},
            {"product": "Mouse Pad", "quantity": 1, "unit_price": 28.51},
        ],
    },
]


# =============================================================================
# Data-access helpers (importable by the MCP server directly)
# =============================================================================

def _match_keyword(order: dict, keyword: str) -> bool:
    """Return True if *keyword* appears in any searchable field of *order*."""
    kw = keyword.lower()
    if kw in order["order_id"].lower():
        return True
    if kw in order["customer_name"].lower():
        return True
    if kw in order["customer_email"].lower():
        return True
    for item in order["items"]:
        if kw in item["product"].lower():
            return True
    return False


def search_orders(query: str, limit: int = 20) -> list[dict]:
    """Return orders whose text fields contain *query*."""
    return [o for o in SAMPLE_ORDERS if _match_keyword(o, query)][:limit]


def get_orders_by_customer(customer: str, limit: int = 20) -> list[dict]:
    """Return orders for a customer (partial match on name or email)."""
    c = customer.lower()
    return [
        o
        for o in SAMPLE_ORDERS
        if c in o["customer_name"].lower() or c in o["customer_email"].lower()
    ][:limit]


def get_orders_by_date(start_date: str, end_date: str, limit: int = 50) -> list[dict]:
    """Return orders whose `created_at` falls within [start, end] (inclusive)."""
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    return [
        o
        for o in SAMPLE_ORDERS
        if start <= date.fromisoformat(o["created_at"]) <= end
    ][:limit]


def get_order(order_id: str) -> dict | None:
    """Return a single order by its unique ID, or None."""
    for o in SAMPLE_ORDERS:
        if o["order_id"] == order_id:
            return o
    return None


def get_order_stats(period: str = "all") -> dict:
    """Return aggregate statistics for a time period.

    *period* may be: ``"today"``, ``"yesterday"``, ``"this_week"``,
    ``"this_month"``, ``"last_month"``, or ``"all"``.
    """
    today = date.today()

    if period == "today":
        filtered = [
            o for o in SAMPLE_ORDERS
            if date.fromisoformat(o["created_at"]) == today
        ]
    elif period == "yesterday":
        yesterday = today - timedelta(days=1)
        filtered = [
            o for o in SAMPLE_ORDERS
            if date.fromisoformat(o["created_at"]) == yesterday
        ]
    elif period == "this_week":
        monday = today - timedelta(days=today.weekday())
        filtered = [
            o for o in SAMPLE_ORDERS
            if monday <= date.fromisoformat(o["created_at"]) <= today
        ]
    elif period == "this_month":
        filtered = [
            o
            for o in SAMPLE_ORDERS
            if date.fromisoformat(o["created_at"]).month == today.month
            and date.fromisoformat(o["created_at"]).year == today.year
        ]
    elif period == "last_month":
        if today.month == 1:
            last_month = 12
            last_year = today.year - 1
        else:
            last_month = today.month - 1
            last_year = today.year
        filtered = [
            o
            for o in SAMPLE_ORDERS
            if date.fromisoformat(o["created_at"]).month == last_month
            and date.fromisoformat(o["created_at"]).year == last_year
        ]
    else:  # "all"
        filtered = list(SAMPLE_ORDERS)

    total_orders = len(filtered)
    total_revenue = sum(o["total"] for o in filtered)
    by_status: dict[str, int] = {}
    for o in filtered:
        by_status[o["status"]] = by_status.get(o["status"], 0) + 1

    return {
        "period": period,
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "by_status": by_status,
    }


def list_orders(status: str = "all", limit: int = 20, offset: int = 0) -> list[dict]:
    """Return orders, optionally filtered by status, with pagination."""
    if status == "all":
        filtered = list(SAMPLE_ORDERS)
    else:
        filtered = [o for o in SAMPLE_ORDERS if o["status"] == status]
    return filtered[offset : offset + limit]


# =============================================================================
# FastAPI application
# =============================================================================

app = FastAPI(
    title="Order Database API",
    version="0.1.0",
    description="Minimal in-memory order database with search, filtering, and statistics.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/orders/search")
async def api_search_orders(
    query: str = Query(..., description="Search keyword"),
    limit: int = Query(20, ge=1, le=100),
):
    return search_orders(query, limit)


@app.get("/orders/customer/{customer}")
async def api_get_orders_by_customer(
    customer: str,
    limit: int = Query(20, ge=1, le=100),
):
    return get_orders_by_customer(customer, limit)


@app.get("/orders/date")
async def api_get_orders_by_date(
    start_date: str = Query(..., description="ISO date, e.g. 2026-01-01"),
    end_date: str = Query(..., description="ISO date, e.g. 2026-12-31"),
    limit: int = Query(50, ge=1, le=200),
):
    return get_orders_by_date(start_date, end_date, limit)


@app.get("/orders")
async def api_list_orders(
    status: str = Query(
        "all", description="pending | shipped | delivered | cancelled | all"
    ),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return list_orders(status, limit, offset)


@app.get("/orders/{order_id}")
async def api_get_order(order_id: str):
    order = get_order(order_id)
    if order is None:
        raise HTTPException(
            status_code=404, detail=f"Order {order_id!r} not found"
        )
    return order


@app.get("/stats")
async def api_get_order_stats(
    period: str = Query(
        "all",
        description="today | yesterday | this_week | this_month | last_month | all",
    ),
):
    valid = {"today", "yesterday", "this_week", "this_month", "last_month", "all"}
    if period not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period. Choose from: {', '.join(sorted(valid))}",
        )
    return get_order_stats(period)


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("order_api:app", host=host, port=port, reload=True)
