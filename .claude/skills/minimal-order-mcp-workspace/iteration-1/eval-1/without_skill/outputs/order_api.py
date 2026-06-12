"""
In-memory order database with query functions.

Provides a simple order store with seed data and functions to search,
list, and retrieve orders.  All data lives in memory -- no external
database required.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta
from typing import Any

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

_SEED_ORDERS: list[dict[str, Any]] = [
    {
        "order_id": "ORD-1001",
        "customer_name": "张三",
        "customer_email": "zhangsan@example.com",
        "status": "delivered",
        "amount": 299.00,
        "items": ["无线耳机", "充电线"],
        "created_at": "2026-06-01T10:30:00",
    },
    {
        "order_id": "ORD-1002",
        "customer_name": "李四",
        "customer_email": "lisi@example.com",
        "status": "shipped",
        "amount": 1599.50,
        "items": ["机械键盘", "鼠标垫"],
        "created_at": "2026-06-03T14:15:00",
    },
    {
        "order_id": "ORD-1003",
        "customer_name": "王五",
        "customer_email": "wangwu@example.com",
        "status": "pending",
        "amount": 89.00,
        "items": ["USB 集线器"],
        "created_at": "2026-06-08T09:00:00",
    },
    {
        "order_id": "ORD-1004",
        "customer_name": "张三",
        "customer_email": "zhangsan@example.com",
        "status": "pending",
        "amount": 450.00,
        "items": ["显示器支架", "桌面台灯"],
        "created_at": "2026-06-10T16:45:00",
    },
    {
        "order_id": "ORD-1005",
        "customer_name": "赵六",
        "customer_email": "zhaoliu@example.com",
        "status": "cancelled",
        "amount": 1280.00,
        "items": ["27寸显示器"],
        "created_at": "2026-06-05T11:20:00",
    },
    {
        "order_id": "ORD-1006",
        "customer_name": "孙七",
        "customer_email": "sunqi@example.com",
        "status": "delivered",
        "amount": 59.90,
        "items": ["笔记本散热架"],
        "created_at": "2026-06-02T08:00:00",
    },
    {
        "order_id": "ORD-1007",
        "customer_name": "李四",
        "customer_email": "lisi@example.com",
        "status": "shipped",
        "amount": 349.00,
        "items": ["蓝牙音箱"],
        "created_at": "2026-06-09T13:30:00",
    },
    {
        "order_id": "ORD-1008",
        "customer_name": "周八",
        "customer_email": "zhouba@example.com",
        "status": "delivered",
        "amount": 2199.00,
        "items": ["办公椅", "升降桌"],
        "created_at": "2026-06-04T15:00:00",
    },
]

# In-memory store -- a shallow copy of the seed data so callers get their
# own list to mutate without side effects.
_orders: list[dict[str, Any]] = copy.deepcopy(_SEED_ORDERS)


# ---------------------------------------------------------------------------
# Public query API
# ---------------------------------------------------------------------------

def get_order(order_id: str) -> dict[str, Any] | None:
    """Return a single order by its ID, or None if not found."""
    for order in _orders:
        if order["order_id"] == order_id:
            return copy.deepcopy(order)
    return None


def search_orders(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Search orders by keyword -- matches order_id, customer_name, and
    customer_email (case-insensitive partial match)."""
    q = query.lower()
    results: list[dict[str, Any]] = []
    for order in _orders:
        if (
            q in order["order_id"].lower()
            or q in order["customer_name"].lower()
            or q in order["customer_email"].lower()
        ):
            results.append(copy.deepcopy(order))
            if len(results) >= limit:
                break
    return results


def list_orders(
    status: str = "all", limit: int = 20, offset: int = 0
) -> list[dict[str, Any]]:
    """List orders with optional status filter and pagination."""
    if status == "all":
        filtered = list(_orders)
    else:
        filtered = [o for o in _orders if o["status"] == status]

    page = filtered[offset : offset + limit]
    return copy.deepcopy(page)


def get_orders_by_customer(customer: str, limit: int = 20) -> list[dict[str, Any]]:
    """Get orders for a customer by name, email, or ID (partial match)."""
    c = customer.lower()
    results: list[dict[str, Any]] = []
    for order in _orders:
        if (
            c in order["customer_name"].lower()
            or c in order["customer_email"].lower()
            or c in order["order_id"].lower()  # in case they pass an order ID
        ):
            results.append(copy.deepcopy(order))
            if len(results) >= limit:
                break
    return results


def get_orders_by_date(
    start_date: str, end_date: str, limit: int = 50
) -> list[dict[str, Any]]:
    """Get orders created within a date range (inclusive, ISO format)."""
    results: list[dict[str, Any]] = []
    for order in _orders:
        created = order["created_at"][:10]  # "YYYY-MM-DD"
        if start_date <= created <= end_date:
            results.append(copy.deepcopy(order))
            if len(results) >= limit:
                break
    return results


def get_order_stats(period: str = "today") -> dict[str, Any]:
    """Return aggregate statistics for a given period.

    ``period`` accepts: "today", "yesterday", "this_week", "this_month",
    "last_month", or "all".
    """
    now = datetime.now()
    start: datetime

    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "yesterday":
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start = today_start - timedelta(days=1)
        end = today_start
    elif period == "this_week":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
            days=now.weekday()
        )
    elif period == "this_month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "last_month":
        first_of_this = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start = (first_of_this - timedelta(days=1)).replace(day=1)
        end = first_of_this
    else:  # "all"
        start = datetime.min

    # Filter orders within the period
    if period == "yesterday":
        filtered = [
            o
            for o in _orders
            if start.isoformat()[:10] <= o["created_at"][:10] < end.isoformat()[:10]
        ]
    elif period == "last_month":
        filtered = [
            o
            for o in _orders
            if start.isoformat()[:10] <= o["created_at"][:10] < end.isoformat()[:10]
        ]
    elif period == "all":
        filtered = list(_orders)
    else:
        start_str = start.strftime("%Y-%m-%d")
        filtered = [o for o in _orders if o["created_at"][:10] >= start_str]

    total_count = len(filtered)
    total_revenue = sum(o["amount"] for o in filtered)

    status_breakdown: dict[str, int] = {}
    for o in filtered:
        status_breakdown[o["status"]] = status_breakdown.get(o["status"], 0) + 1

    return {
        "period": period,
        "total_orders": total_count,
        "total_revenue": round(total_revenue, 2),
        "status_breakdown": status_breakdown,
    }
