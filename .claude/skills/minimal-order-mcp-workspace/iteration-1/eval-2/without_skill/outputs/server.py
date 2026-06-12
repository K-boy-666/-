"""
MCP Server for the Order Management API.

Wraps the REST API as MCP tools so Claude (or any MCP host) can
search, filter, and inspect orders.

Run via stdio transport (default for MCP)::

    python server.py

Or point it at a custom API host::

    ORDER_API_URL=http://localhost:8080 python server.py

Tools exposed:

  search_orders         -- keyword search across orders
  get_order             -- fetch a single order by ID
  get_orders_by_customer-- filter by customer name/email
  get_orders_by_date    -- filter by date range
  list_orders           -- paginated list with optional status filter
  get_order_stats       -- aggregate statistics for a period
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server

from api_client import OrderApiClient, OrderApiError

# ---------------------------------------------------------------------------
# MCP server setup
# ---------------------------------------------------------------------------

server = Server("order-management")

# Lazily-initialised client -- reuse across tool calls
_client: OrderApiClient | None = None


def _get_client() -> OrderApiClient:
    global _client
    if _client is None:
        _client = OrderApiClient()
    return _client


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@server.tool()
def search_orders(query: str, limit: int = 20) -> str:
    """Search orders by keyword -- matches across order number, customer name,
    and notes.  Returns up to `limit` results.

    Use this as a first step when you don't have an exact order ID.  Once you
    find the right order, call get_order with its ID for full details.
    """
    client = _get_client()
    try:
        data = client.list_orders(search=query, limit=limit)
        return _format_list(data)
    except OrderApiError as exc:
        return f"API error: {exc}"


@server.tool()
def get_order(order_id: str) -> str:
    """Fetch a single order by its unique ID.  Returns the full order record
    including line items, totals, customer info, and status.

    If you don't know the ID, use search_orders or list_orders first.
    """
    client = _get_client()
    try:
        data = client.get_order(order_id)
        return _format_order(data)
    except OrderApiError as exc:
        return f"API error: {exc}"


@server.tool()
def get_orders_by_customer(customer: str, limit: int = 20) -> str:
    """Get orders placed by a specific customer.  `customer` can be a name,
    email, or customer ID -- the API matches partial inputs.

    If you only have a partial name, this still works.  Use search_orders
    as an alternative when you're not sure whether the text is a customer name
    or an order number.
    """
    client = _get_client()
    try:
        data = client.get_orders_by_customer(customer, limit=limit)
        return _format_list(data)
    except OrderApiError as exc:
        return f"API error: {exc}"


@server.tool()
def get_orders_by_date(start_date: str, end_date: str, limit: int = 50) -> str:
    """Get orders created within a date range.  Dates must be ISO format
    (YYYY-MM-DD, e.g. \"2026-01-01\").  The range is inclusive.

    Use this when you need orders from a specific time window -- for example
    \"all orders from last week\" or \"orders placed in Q1\".
    """
    client = _get_client()
    try:
        data = client.get_orders_by_date(start_date, end_date, limit=limit)
        return _format_list(data)
    except OrderApiError as exc:
        return f"API error: {exc}"


@server.tool()
def list_orders(status: str = "all", limit: int = 20, offset: int = 0) -> str:
    """List orders with optional status filtering and pagination.

    `status` accepts values like \"pending\", \"shipped\", \"delivered\", \"cancelled\",
    or \"all\" (default) to include every status.
    Use `offset` to page through results (e.g. 0, then 20, then 40).
    """
    client = _get_client()
    try:
        data = client.list_orders(status=status, limit=limit, offset=offset)
        return _format_list(data)
    except OrderApiError as exc:
        return f"API error: {exc}"


@server.tool()
def get_order_stats(period: str = "today") -> str:
    """Get aggregate order statistics for a time period.

    `period` accepts: \"today\", \"yesterday\", \"this_week\", \"this_month\",
    \"last_month\", or \"all\".
    Returns total count, total revenue, and a breakdown by order status.
    Call this first for a high-level overview before drilling into details.
    """
    client = _get_client()
    try:
        data = client.get_order_stats(period)
        formatted = (
            f"Period: {data['period']}\n"
            f"Total orders: {data['total_orders']}\n"
            f"Total revenue: ${data['total_revenue']:,.2f}\n"
            f"By status:\n"
        )
        for status, count in sorted(data.get("by_status", {}).items()):
            formatted += f"  - {status}: {count}\n"
        return formatted
    except OrderApiError as exc:
        return f"API error: {exc}"


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _format_list(data: dict[str, Any]) -> str:
    total = data["total"]
    offset = data["offset"]
    orders = data["orders"]
    page_size = len(orders)

    if not orders:
        return f"No orders found (total: {total})."

    lines = [f"Showing {offset + 1}-{offset + page_size} of {total} orders:\n"]
    for o in orders:
        lines.append(_format_order_summary(o))
    return "\n".join(lines)


def _format_order_summary(o: dict[str, Any]) -> str:
    return (
        f"  {o['order_number']} | {o['status']:>9} | "
        f"${o['total']:>10,.2f} | "
        f"{o['customer_name']} | {o['created_at'][:10]}"
    )


def _format_order(data: dict[str, Any]) -> str:
    lines = [
        f"Order: {data['order_number']}",
        f"Status: {data['status']}",
        f"Customer: {data['customer_name']} <{data['customer_email']}>",
        f"Created: {data['created_at']}",
        f"Updated: {data['updated_at']}",
        f"Total: ${data['total']:,.2f} {data['currency']}",
        f"Notes: {data['notes'] or '(none)'}",
        "",
        "Items:",
    ]
    for item in data["items"]:
        lines.append(
            f"  {item['sku']}  {item['name']}  "
            f"qty {item['qty']}  @ ${item['unit_price']:.2f}  = "
            f"${item['qty'] * item['unit_price']:.2f}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point -- stdio transport
# ---------------------------------------------------------------------------

async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
