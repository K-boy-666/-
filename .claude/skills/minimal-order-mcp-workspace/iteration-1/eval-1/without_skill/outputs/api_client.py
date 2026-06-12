#!/usr/bin/env python3
"""
Stand-alone CLI client for the order API -- useful for testing without MCP.

Usage
-----
  python api_client.py search <keyword>
  python api_client.py get <order_id>
  python api_client.py list [--status <status>] [--limit <n>] [--offset <n>]
  python api_client.py customer <name>
  python api_client.py date <start> <end>
  python api_client.py stats [--period <period>]
"""

from __future__ import annotations

import argparse
import json
import sys

from order_api import (
    get_order,
    search_orders,
    list_orders,
    get_orders_by_customer,
    get_orders_by_date,
    get_order_stats,
)


def _print(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Order API CLI client")
    sub = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = sub.add_parser("search", help="Search orders by keyword")
    p_search.add_argument("query", help="Keyword to search for")
    p_search.add_argument("--limit", type=int, default=20)

    # get
    p_get = sub.add_parser("get", help="Get a single order by ID")
    p_get.add_argument("order_id", help="Order ID (e.g. ORD-1001)")

    # list
    p_list = sub.add_parser("list", help="List orders")
    p_list.add_argument("--status", default="all")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--offset", type=int, default=0)

    # customer
    p_cust = sub.add_parser("customer", help="Get orders by customer")
    p_cust.add_argument("customer", help="Customer name, email, or ID")
    p_cust.add_argument("--limit", type=int, default=20)

    # date
    p_date = sub.add_parser("date", help="Get orders by date range")
    p_date.add_argument("start_date", help="Start date (YYYY-MM-DD)")
    p_date.add_argument("end_date", help="End date (YYYY-MM-DD)")
    p_date.add_argument("--limit", type=int, default=50)

    # stats
    p_stats = sub.add_parser("stats", help="Get order statistics")
    p_stats.add_argument("--period", default="all")

    args = parser.parse_args()

    if args.command == "search":
        _print(search_orders(args.query, limit=args.limit))
    elif args.command == "get":
        result = get_order(args.order_id)
        _print(result if result else {"error": f"Order '{args.order_id}' not found."})
    elif args.command == "list":
        _print(list_orders(status=args.status, limit=args.limit, offset=args.offset))
    elif args.command == "customer":
        _print(get_orders_by_customer(args.customer, limit=args.limit))
    elif args.command == "date":
        _print(get_orders_by_date(args.start_date, args.end_date, limit=args.limit))
    elif args.command == "stats":
        _print(get_order_stats(period=args.period))


if __name__ == "__main__":
    main()
