"""
Synchronous HTTP client for the Order Management REST API.

Usage::

    from api_client import OrderApiClient

    client = OrderApiClient()                         # reads ORDER_API_URL from env
    client = OrderApiClient(base_url="http://localhost:8080")

    # List orders with filters
    resp = client.list_orders(search="Acme", limit=10)
    for order in resp["orders"]:
        print(order["order_number"], order["total"])

    # Single order
    order = client.get_order("ORD-1001")

    # By customer
    resp = client.get_orders_by_customer("Globex")

    # By date range
    resp = client.get_orders_by_date("2026-05-01", "2026-05-31")

    # Stats
    stats = client.get_order_stats("this_month")
"""

from __future__ import annotations

import os
from datetime import date
from typing import Any, Optional

import httpx


class OrderApiError(Exception):
    """Raised when the API returns a non-2xx status."""


class OrderApiClient:
    """Thin wrapper around the order-management REST API."""

    def __init__(self, base_url: Optional[str] = None) -> None:
        self.base_url = (base_url or os.environ.get("ORDER_API_URL", "http://127.0.0.1:8080")).rstrip("/")
        self._client = httpx.Client(timeout=httpx.Timeout(30.0))

    # -- helpers ---------------------------------------------------------

    def _get(self, path: str, params: Optional[dict] = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        resp = self._client.get(url, params=params)
        if resp.status_code >= 400:
            raise OrderApiError(f"{resp.status_code} {resp.reason_phrase}: {resp.text}")
        return resp.json()

    # -- public methods ---------------------------------------------------

    def list_orders(
        self,
        search: Optional[str] = None,
        customer: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: str = "all",
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search and filter orders."""
        params: dict[str, Any] = {"status": status, "limit": limit, "offset": offset}
        if search:
            params["search"] = search
        if customer:
            params["customer"] = customer
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return self._get("/orders", params)

    def get_order(self, order_id: str) -> dict[str, Any]:
        """Fetch a single order by ID."""
        return self._get(f"/orders/{order_id}")

    def get_orders_by_customer(self, customer: str, limit: int = 20) -> dict[str, Any]:
        """List orders for a given customer (partial match)."""
        return self._get("/orders", {"customer": customer, "limit": limit})

    def get_orders_by_date(self, start_date: str, end_date: str, limit: int = 50) -> dict[str, Any]:
        """List orders within a date range (ISO dates, inclusive)."""
        return self._get("/orders", {"start_date": start_date, "end_date": end_date, "limit": limit})

    def get_order_stats(self, period: str = "all") -> dict[str, Any]:
        """Get aggregate statistics for a time period."""
        return self._get("/stats", {"period": period})

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "OrderApiClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
