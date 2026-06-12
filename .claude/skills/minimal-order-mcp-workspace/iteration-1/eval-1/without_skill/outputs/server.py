#!/usr/bin/env python3
"""
MCP server that exposes order-query tools via stdio transport.

Run this script directly and register it with Claude Code (or any MCP
client) to let an AI agent query the in-memory order store.

Tools exposed
-------------
- search_orders      : keyword search across order_id / customer_name / email
- get_order          : fetch a single order by its ID
- list_orders        : paginated list with optional status filter
- get_orders_by_customer : orders for a given customer (partial match)
- get_orders_by_date     : orders within an ISO date range
- get_order_stats        : aggregate stats for a period
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationCapabilities
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ---------------------------------------------------------------------------
# Import the in-memory order API
# ---------------------------------------------------------------------------
try:
    from order_api import (
        get_order,
        search_orders,
        list_orders,
        get_orders_by_customer,
        get_orders_by_date,
        get_order_stats,
    )
except ImportError:
    # When running from a different working directory
    sys.path.insert(0, ".")
    from order_api import (  # type: ignore[no-redef]
        get_order,
        search_orders,
        list_orders,
        get_orders_by_customer,
        get_orders_by_date,
        get_order_stats,
    )


# ---------------------------------------------------------------------------
# MCP server setup
# ---------------------------------------------------------------------------

server = Server("order-server")


# ---------------------------------------------------------------------------
# Tool definitions (for discovery)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    Tool(
        name="search_orders",
        description="Search orders by keyword -- matches across order number, "
        "customer name, and other text fields.  Returns up to `limit` results.\n\n"
        "Use this as a first step when you don't have an exact order ID.  Once you "
        "find the right order, call get_order with its ID for full details.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search keyword to look for in orders.",
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
        name="get_order",
        description="Fetch a single order by its unique ID.  Returns the full "
        "order record including line items, totals, customer info, and status.\n\n"
        "If you don't know the ID, use search_orders or list_orders first.",
        inputSchema={
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The unique order ID (e.g. ORD-1001).",
                },
            },
            "required": ["order_id"],
        },
    ),
    Tool(
        name="list_orders",
        description="List orders with optional status filtering and pagination.\n\n"
        "`status` accepts values like \"pending\", \"shipped\", \"delivered\", "
        "\"cancelled\", or \"all\" (default) to include every status.\n"
        "Use `offset` to page through results (e.g. 0, then 20, then 40).",
        inputSchema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by order status, or \"all\" for every status.",
                    "default": "all",
                },
                "limit": {
                    "type": "integer",
                    "description": "Page size.",
                    "default": 20,
                },
                "offset": {
                    "type": "integer",
                    "description": "Zero-based offset for pagination.",
                    "default": 0,
                },
            },
        },
    ),
    Tool(
        name="get_orders_by_customer",
        description="Get orders placed by a specific customer.  `customer` can be "
        "a name, email, or customer ID -- the API matches partial inputs.\n\n"
        "If you only have a partial name, this still works.  Use search_orders "
        "as an alternative when you're not sure whether the text is a customer name "
        "or an order number.",
        inputSchema={
            "type": "object",
            "properties": {
                "customer": {
                    "type": "string",
                    "description": "Customer name, email, or ID (partial match supported).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return.",
                    "default": 20,
                },
            },
            "required": ["customer"],
        },
    ),
    Tool(
        name="get_orders_by_date",
        description="Get orders created within a date range.  Dates must be ISO "
        "format (YYYY-MM-DD, e.g. \"2026-01-01\").  The range is inclusive.\n\n"
        "Use this when you need orders from a specific time window -- for example "
        "\"all orders from last week\" or \"orders placed in Q1\".",
        inputSchema={
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": "Start date in ISO format (YYYY-MM-DD), inclusive.",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in ISO format (YYYY-MM-DD), inclusive.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return.",
                    "default": 50,
                },
            },
            "required": ["start_date", "end_date"],
        },
    ),
    Tool(
        name="get_order_stats",
        description="Get aggregate order statistics for a time period.\n\n"
        "`period` accepts: \"today\", \"yesterday\", \"this_week\", \"this_month\", "
        "\"last_month\", or \"all\".\n"
        "Returns total count, total revenue, and a breakdown by order status.\n"
        "Call this first for a high-level overview before drilling into details.",
        inputSchema={
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Time period for statistics.",
                    "default": "today",
                },
            },
        },
    ),
]


# ---------------------------------------------------------------------------
# Tool handler registry
# ---------------------------------------------------------------------------

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Return the list of tools this server provides."""
    return TOOL_DEFINITIONS


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any]
) -> list[TextContent]:
    """Dispatch tool calls to the appropriate handler."""
    try:
        if name == "search_orders":
            results = search_orders(
                query=arguments["query"],
                limit=arguments.get("limit", 20),
            )
            return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]

        elif name == "get_order":
            order = get_order(order_id=arguments["order_id"])
            if order is None:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": f"Order '{arguments['order_id']}' not found."}, ensure_ascii=False),
                )]
            return [TextContent(type="text", text=json.dumps(order, ensure_ascii=False, indent=2))]

        elif name == "list_orders":
            results = list_orders(
                status=arguments.get("status", "all"),
                limit=arguments.get("limit", 20),
                offset=arguments.get("offset", 0),
            )
            return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]

        elif name == "get_orders_by_customer":
            results = get_orders_by_customer(
                customer=arguments["customer"],
                limit=arguments.get("limit", 20),
            )
            return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]

        elif name == "get_orders_by_date":
            results = get_orders_by_date(
                start_date=arguments["start_date"],
                end_date=arguments["end_date"],
                limit=arguments.get("limit", 50),
            )
            return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]

        elif name == "get_order_stats":
            stats = get_order_stats(period=arguments.get("period", "today"))
            return [TextContent(type="text", text=json.dumps(stats, ensure_ascii=False, indent=2))]

        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"}, ensure_ascii=False),
            )]

    except Exception as exc:
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(exc)}, ensure_ascii=False),
        )]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    """Run the MCP server over stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationCapabilities(
                sampling={},
                experimental={},
                roots={},
            ),
            notification_options=NotificationOptions(
                tools_changed=False,
                resources_changed=False,
                prompts_changed=False,
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
