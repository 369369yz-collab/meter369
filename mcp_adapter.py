#!/usr/bin/env python3
"""
369 Meter — MCP adapter (stdio + streamable-HTTP WSGI), stdlib only.

Exposes the four x402-metered services as MCP tools for directory
discovery (Official MCP Registry / Glama / Smithery / mcp.so).

Payment honesty: the underlying services are pay-per-call over x402
(USDC on Base). An MCP transport cannot carry an X-PAYMENT header, so
tools/call NEVER serves an unpaid resource: it performs the real call
to the live gateway, receives the gateway's HTTP 402, and returns the
full x402 payment requirements as an MCP error result so the caller can
pay over the x402 rail and call the REST route directly. tools/list and
initialize are free, exactly like GET /meter/health.

Live gateway: https://369yz.pythonanywhere.com/meter
  POST /v1/text/analyze        TextIntel          $0.01
  POST /v1/hook/score          HookScore          $0.01
  POST /v1/translate/check     TranslationCheck   $0.02
  POST /v1/game/facts          GameFacts          $0.03
Rail: x402 v1 "exact", USDC on Base, facilitator payai-public,
payTo 0xA0A1ff293EF2FF051121674c8eAAd69570b25e6c.

Run:
  stdio:           python3 mcp_adapter.py
  streamable HTTP: any WSGI server mounting `application` (POST /mcp)
Env: METER_BASE_URL (default https://369yz.pythonanywhere.com/meter)
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE = os.environ.get("METER_BASE_URL", "https://369yz.pythonanywhere.com/meter").rstrip("/")
SERVER_INFO = {"name": "meter369", "version": "1.0.0"}
PROTOCOL_VERSION = "2025-03-26"

TOOLS = [
    {
        "name": "text_analyze",
        "title": "TextIntel — text analysis ($0.01/call via x402)",
        "description": "Use this when you need deterministic text analysis (counts, Flesch readability, script mix, top keywords). Pay-per-call: $0.01 USDC on Base via x402 to the REST route POST /v1/text/analyze.",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string", "description": "Text to analyze, up to 20000 chars"}},
            "required": ["text"],
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "hook_score",
        "title": "HookScore — gaming hook scorer ($0.01/call via x402)",
        "description": "Use this when you need a gaming headline or hook scored 0-100 against the 369 team's hook rules. Pay-per-call: $0.01 USDC on Base via x402 to the REST route POST /v1/hook/score.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "headline": {"type": "string", "description": "Headline/hook to score"},
                "platform": {"type": "string", "description": "Optional platform, default 'reels'"},
            },
            "required": ["headline"],
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "translate_check",
        "title": "TranslationCheck — EN<->FA translation QA ($0.02/call via x402)",
        "description": "Use this when you need an EN<->FA translation QA score 0-100 (numbers/entities preserved, script purity, untranslated segments). Pay-per-call: $0.02 USDC on Base via x402 to the REST route POST /v1/translate/check.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_text": {"type": "string", "description": "Source text"},
                "target_text": {"type": "string", "description": "Translated text to check"},
            },
            "required": ["source_text", "target_text"],
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False},
    },
    {
        "name": "game_facts",
        "title": "GameFacts — live game metadata ($0.03/call via x402)",
        "description": "Use this when you need live game metadata from RAWG (release date, ratings, Metacritic, platforms, genres). Pay-per-call: $0.03 USDC on Base via x402 to the REST route POST /v1/game/facts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Game title to look up"},
                "limit": {"type": "integer", "description": "Optional, 1-5, default 3"},
            },
            "required": ["query"],
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": True},
    },
]
TOOL_ROUTES = {
    "text_analyze": "/v1/text/analyze",
    "hook_score": "/v1/hook/score",
    "translate_check": "/v1/translate/check",
    "game_facts": "/v1/game/facts",
}


def _call_gateway(route: str, args: dict):
    """Real call to the live gateway. Returns (status, parsed_json)."""
    req = urllib.request.Request(
        BASE + route,
        data=json.dumps(args or {}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"error": f"http_{e.code}"}
    except Exception as e:  # network failure: report honestly, never fake data
        return 0, {"error": f"gateway_unreachable:{type(e).__name__}"}


def handle(request: dict):
    """One JSON-RPC request -> response dict (or None for notifications)."""
    method = request.get("method", "")
    rid = request.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        }}
    if method in ("notifications/initialized", "notifications/cancelled"):
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = request.get("params") or {}
        name = params.get("name", "")
        route = TOOL_ROUTES.get(name)
        if not route:
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "isError": True,
                "content": [{"type": "text", "text": f"unknown tool: {name}"}],
            }}
        status, body = _call_gateway(route, params.get("arguments") or {})
        if status == 200:
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": json.dumps(body)}],
            }}
        # 402 (expected without payment) or any other failure: surface the
        # gateway's own response verbatim — never fabricate a result.
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "isError": True,
            "content": [{"type": "text", "text": json.dumps({
                "error": "payment_required_x402" if status == 402 else f"gateway_http_{status}",
                "pay_via": f"POST {BASE}{route} with an x402 v1 X-PAYMENT header (USDC on Base)",
                "gateway_response": body,
            })}],
        }}
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"method not found: {method}"}}


# ---------------------------------------------------------------- stdio
def serve_stdio():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            resp = handle(json.loads(line))
        except Exception as e:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"parse error: {e}"}}
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


# ------------------------------------------------------- streamable HTTP
def application(environ, start_response):
    if environ.get("REQUEST_METHOD") != "POST":
        start_response("405 Method Not Allowed", [("Content-Type", "application/json")])
        return [b'{"error":"POST only"}']
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
        payload = json.loads(environ["wsgi.input"].read(length).decode() or "{}")
    except Exception as e:
        start_response("400 Bad Request", [("Content-Type", "application/json")])
        return [json.dumps({"error": f"bad json: {e}"}).encode()]
    resp = handle(payload)
    if resp is None:
        start_response("202 Accepted", [("Content-Type", "application/json")])
        return [b""]
    start_response("200 OK", [("Content-Type", "application/json")])
    return [json.dumps(resp).encode()]


if __name__ == "__main__":
    serve_stdio()
