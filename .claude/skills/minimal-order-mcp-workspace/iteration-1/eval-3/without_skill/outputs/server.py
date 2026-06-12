"""
MCP server -- exposes order-database tools to Claude via stdio.

Uses the in-memory data layer from ``order_api`` directly so no separate
API process is required.  The REST API (order_api.py) and HTTP client
(api_client.py) are available when you need HTTP exposure.
"""

from __future__ import annotations

import asyncio
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from order_api import (
    search_orders as _search_orders,
    get_orders_by_customer as _get_orders_by_customer,
    get_orders_by_date as _get_orders_by_date,
    get_order as _get_order,
    get_order_stats as _get_order_stats,
    list_orders as _list_orders,
)

server = Server("order-server")


# -- list_tools -----------------------------------------------------------

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_orders",
            description=(
                "Search orders by keyword -- matches across order number, "
                "customer name, and other text fields.  Returns up to "
                "`limit` results.\n\n"
                "Use this as a first step when you don't have an exact "
                "order ID.  Once you find the right order, call get_order "
                "with its ID for full details."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keyword to match against order fields.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return.",
                        "default": 20,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_orders_by_customer",
            description=(
                "Get orders placed by a specific customer.  `customer` can "
                "be a name, email, or customer ID -- the API matches "
                "partial inputs.\n\n"
                "If you only have a partial name, this still works.  Use "
                "search_orders as an alternative when you're not sure "
                "whether the text is a customer name or an order number."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "customer": {
                        "type": "string",
                        "description": "Customer name, email, or ID (partial match).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results.",
                        "default": 20,
                    },
                },
                "required": ["customer"],
            },
        ),
        Tool(
            name="get_orders_by_date",
            description=(
                "Get orders created within a date range.  Dates must be "
                "ISO format (YYYY-MM-DD, e.g. \"2026-01-01\").  The range "
                "is inclusive.\n\n"
                "Use this when you need orders from a specific time "
                "window -- for example \"all orders from last week\" or "
                "\"orders placed in Q1\"."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in ISO format (YYYY-MM-DD).",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in ISO format (YYYY-MM-DD).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results.",
                        "default": 50,
                    },
                },
                "required": ["start_date", "end_date"],
            },
        ),
        Tool(
            name="get_order",
            description=(
                "Fetch a single order by its unique ID.  Returns the full "
                "order record including line items, totals, customer info, "
                "and status.\n\n"
                "If you don't know the ID, use search_orders or "
                "list_orders first."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The unique order ID (e.g., ORD-001).",
                    },
                },
                "required": ["order_id"],
            },
        ),
        Tool(
            name="get_order_stats",
            description=(
                "Get aggregate order statistics for a time period.\n\n"
                "`period` accepts: \"today\", \"yesterday\", \"this_week\", "
                "\"this_month\", \"last_month\", or \"all\".\n"
                "Returns total count, total revenue, and a breakdown by "
                "order status.\n"
                "Call this first for a high-level overview before "
                "drilling into details."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "description": (
                            "Time period: today, yesterday, this_week, "
                            "this_month, last_month, or all."
                        ),
                        "default": "today",
                    },
                },
            },
        ),
        Tool(
            name="list_orders",
            description=(
                "List orders with optional status filtering and "
                "pagination.\n\n"
                "`status` accepts values like \"pending\", \"shipped\", "
                "\"delivered\", \"cancelled\", or \"all\" (default) to "
                "include every status.\n"
                "Use `offset` to page through results (e.g. 0, then 20, "
                "then 40)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": (
                            "Filter by status: pending, shipped, delivered, "
                            "cancelled, or all."
                        ),
                        "default": "all",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Page size.",
                        "default": 20,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of records to skip.",
                        "default": 0,
                    },
                },
            },
        ),
    ]


# -- call_tool ------------------------------------------------------------

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "search_orders":
            result = _search_orders(
                arguments["query"], arguments.get("limit", 20)
            )
        elif name == "get_orders_by_customer":
            result = _get_orders_by_customer(
                arguments["customer"], arguments.get("limit", 20)
            )
        elif name == "get_orders_by_date":
            result = _get_orders_by_date(
                arguments["start_date"],
                arguments["end_date"],
                arguments.get("limit", 50),
            )
        elif name == "get_order":
            result = _get_order(arguments["order_id"])
            if result is None:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": f"Order {arguments['order_id']!r} not found"},
                            indent=2,
                        ),
                    )
                ]
        elif name == "get_order_stats":
            result = _get_order_stats(arguments.get("period", "all"))
        elif name == "list_orders":
            result = _list_orders(
                arguments.get("status", "all"),
                arguments.get("limit", 20),
                arguments.get("offset", 0),
            )
        else:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"error": f"Unknown tool: {name!r}"}, indent=2
                    ),
                )
            ]

        return [
            TextContent(
                type="text", text=json.dumps(result, indent=2, default=str)
            )
        ]
    except Exception as exc:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": str(exc)}, indent=2),
            )
        ]


# -- entry point ----------------------------------------------------------

async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
