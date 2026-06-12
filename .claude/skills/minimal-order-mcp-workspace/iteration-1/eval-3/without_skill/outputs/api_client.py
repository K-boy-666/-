"""
HTTP client for the Order REST API -- async and sync flavours.

Usage (async):
    client = OrderApiClient()
    orders = await client.search_orders("Alice")

Usage (sync):
    client = OrderApiClient()
    orders = client.search_orders_sync("Alice")
"""

from __future__ import annotations

import os

import httpx


class OrderApiClient:
    """Async HTTP client for the Order Database REST API.

    Reads API_HOST / API_PORT from the environment (defaults to
    127.0.0.1:8000).  Every method has a ``*_sync`` counterpart that uses
    ``httpx.Client`` instead of ``httpx.AsyncClient``.
    """

    def __init__(self, base_url: str | None = None) -> None:
        if base_url is not None:
            self.base_url = base_url.rstrip("/")
        else:
            host = os.getenv("API_HOST", "127.0.0.1")
            port = os.getenv("API_PORT", "8000")
            self.base_url = f"http://{host}:{port}"

    # ------------------------------------------------------------------
    # Async methods
    # ------------------------------------------------------------------

    async def search_orders(self, query: str, limit: int = 20) -> list[dict]:
        """Full-text search across order fields."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/orders/search",
                params={"query": query, "limit": limit},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_orders_by_customer(
        self, customer: str, limit: int = 20
    ) -> list[dict]:
        """Orders for a customer (partial match on name or email)."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/orders/customer/{customer}",
                params={"limit": limit},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_orders_by_date(
        self, start_date: str, end_date: str, limit: int = 50
    ) -> list[dict]:
        """Orders within [start_date, end_date] (inclusive, ISO format)."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/orders/date",
                params={
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": limit,
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def list_orders(
        self, status: str = "all", limit: int = 20, offset: int = 0
    ) -> list[dict]:
        """List orders with optional status filter and pagination."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/orders",
                params={"status": status, "limit": limit, "offset": offset},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_order(self, order_id: str) -> dict:
        """Fetch a single order by its unique ID."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/orders/{order_id}")
            resp.raise_for_status()
            return resp.json()

    async def get_order_stats(self, period: str = "all") -> dict:
        """Aggregate statistics for a time period."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/stats", params={"period": period}
            )
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Sync wrappers
    # ------------------------------------------------------------------

    def search_orders_sync(self, query: str, limit: int = 20) -> list[dict]:
        with httpx.Client() as client:
            resp = client.get(
                f"{self.base_url}/orders/search",
                params={"query": query, "limit": limit},
            )
            resp.raise_for_status()
            return resp.json()

    def get_orders_by_customer_sync(
        self, customer: str, limit: int = 20
    ) -> list[dict]:
        with httpx.Client() as client:
            resp = client.get(
                f"{self.base_url}/orders/customer/{customer}",
                params={"limit": limit},
            )
            resp.raise_for_status()
            return resp.json()

    def get_orders_by_date_sync(
        self, start_date: str, end_date: str, limit: int = 50
    ) -> list[dict]:
        with httpx.Client() as client:
            resp = client.get(
                f"{self.base_url}/orders/date",
                params={
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": limit,
                },
            )
            resp.raise_for_status()
            return resp.json()

    def list_orders_sync(
        self, status: str = "all", limit: int = 20, offset: int = 0
    ) -> list[dict]:
        with httpx.Client() as client:
            resp = client.get(
                f"{self.base_url}/orders",
                params={"status": status, "limit": limit, "offset": offset},
            )
            resp.raise_for_status()
            return resp.json()

    def get_order_sync(self, order_id: str) -> dict:
        with httpx.Client() as client:
            resp = client.get(f"{self.base_url}/orders/{order_id}")
            resp.raise_for_status()
            return resp.json()

    def get_order_stats_sync(self, period: str = "all") -> dict:
        with httpx.Client() as client:
            resp = client.get(
                f"{self.base_url}/stats", params={"period": period}
            )
            resp.raise_for_status()
            return resp.json()
