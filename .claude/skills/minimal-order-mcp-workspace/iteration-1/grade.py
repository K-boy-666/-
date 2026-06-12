import json
import os
import re

WORKSPACE = os.path.dirname(os.path.abspath(__file__))


def read_file(path):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


configs = [
    ("eval-1", "with_skill"),
    ("eval-1", "without_skill"),
    ("eval-2", "with_skill"),
    ("eval-2", "without_skill"),
    ("eval-3", "with_skill"),
    ("eval-3", "without_skill"),
]

all_results = {}

for eval_name, skill_mode in configs:
    out_dir = os.path.join(WORKSPACE, eval_name, skill_mode, "outputs")
    assertions = []

    api_content = read_file(os.path.join(out_dir, "order_api.py"))
    client_content = read_file(os.path.join(out_dir, "api_client.py"))
    server_content = read_file(os.path.join(out_dir, "server.py"))
    pp_content = read_file(os.path.join(out_dir, "pyproject.toml"))
    env_content = read_file(os.path.join(out_dir, ".env"))
    config_content = read_file(
        os.path.join(out_dir, ".claude", "settings.local.json")
    )

    # 1. has_order_api
    ok = bool(api_content) and "FastAPI" in api_content
    assertions.append(
        {
            "text": "has_order_api",
            "passed": ok,
            "evidence": (
                "order_api.py with FastAPI"
                if ok
                else ("missing" if not api_content else "no FastAPI")
            ),
        }
    )

    # 2. has_api_client
    ok = bool(client_content) and "httpx" in client_content
    assertions.append(
        {
            "text": "has_api_client",
            "passed": ok,
            "evidence": (
                "api_client.py with httpx"
                if ok
                else ("missing" if not client_content else "no httpx")
            ),
        }
    )

    # 3. has_mcp_server
    ok = bool(server_content) and ("FastMCP" in server_content or "mcp" in server_content.lower())
    assertions.append(
        {
            "text": "has_mcp_server",
            "passed": ok,
            "evidence": (
                "server.py with MCP"
                if ok
                else ("missing" if not server_content else "no MCP framework")
            ),
        }
    )

    # 4. has_pyproject
    ok = bool(pp_content) and (
        "fastmcp" in pp_content or "fastapi" in pp_content or '"mcp"' in pp_content
    )
    assertions.append(
        {
            "text": "has_pyproject",
            "passed": ok,
            "evidence": (
                "pyproject.toml with deps"
                if ok
                else ("missing" if not pp_content else "no deps")
            ),
        }
    )

    # 5. has_env_file
    ok = bool(env_content) and (
        "8000" in env_content
        or "API_BASE_URL" in env_content
        or "API_HOST" in env_content
    )
    assertions.append(
        {
            "text": "has_env_file",
            "passed": ok,
            "evidence": (
                ".env with config"
                if ok
                else ("missing" if not env_content else "no API URL")
            ),
        }
    )

    # 6. has_claude_config
    ok = bool(config_content) and (
        "mcpServers" in config_content or "order-server" in config_content
    )
    assertions.append(
        {
            "text": "has_claude_config",
            "passed": ok,
            "evidence": (
                "Claude config with MCP"
                if ok
                else ("missing" if not config_content else "no MCP config")
            ),
        }
    )

    # 7. api_min_5_endpoints
    routes = re.findall(r'@app\.(?:get|post|put|delete)\s*\(\s*["\']', api_content)
    assertions.append(
        {
            "text": "api_min_5_endpoints",
            "passed": len(routes) >= 5,
            "evidence": f"API has {len(routes)} routes",
        }
    )

    # 8. mcp_min_5_tools
    tools = re.findall(r"@mcp\.tool\s*\(", server_content)
    if len(tools) < 3:
        tools = re.findall(
            r"async def (?:search_orders|get_order|list_orders|get_orders_by|get_order_stats)",
            server_content,
        )
    assertions.append(
        {
            "text": "mcp_min_5_tools",
            "passed": len(tools) >= 5,
            "evidence": f"MCP has {len(tools)} tools",
        }
    )

    # 9. tools_have_readonly_hint
    readonly = server_content.count("readOnlyHint")
    assertions.append(
        {
            "text": "tools_have_readonly_hint",
            "passed": readonly >= 5,
            "evidence": f"{readonly} readOnlyHint occurrences",
        }
    )

    # 10. min_5_sample_orders
    orders = re.findall(r'"id"\s*:\s*"ORD-', api_content)
    if len(orders) < 5:
        orders = re.findall(r'"order_id"', api_content)
    if len(orders) < 3:
        orders = re.findall(r'"customer_name"', api_content)
    assertions.append(
        {
            "text": "min_5_sample_orders",
            "passed": len(orders) >= 5,
            "evidence": f"{len(orders)} sample orders",
        }
    )

    # 11. has_mcp_instructions
    ok = "instructions" in server_content.lower()
    assertions.append(
        {
            "text": "has_mcp_instructions",
            "passed": ok,
            "evidence": "has instructions" if ok else "no instructions",
        }
    )

    all_results[f"{eval_name}_{skill_mode}"] = assertions
    passed = sum(1 for a in assertions if a["passed"])
    print(f"{eval_name}/{skill_mode}: {passed}/11")

    grading = {"assertions": assertions}
    grading_path = os.path.join(WORKSPACE, eval_name, skill_mode, "grading.json")
    with open(grading_path, "w", encoding="utf-8") as f:
        json.dump(grading, f, ensure_ascii=False, indent=2)

print()
for key, assertions in all_results.items():
    passed = sum(1 for a in assertions if a["passed"])
    failed = [a["text"] for a in assertions if not a["passed"]]
    line = f"{key}: {passed}/11"
    if failed:
        line += f"  FAILS: {failed}"
    print(line)
