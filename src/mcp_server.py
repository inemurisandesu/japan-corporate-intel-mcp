"""Zero-dependency JSON-RPC 2.0 MCP Server (stdio) for Japan Corporate Intelligence."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from .jp_corp_client import build_corporate_dossier, validate_corporate_number


SERVER_INFO = {
    "name": "flowcraft-japan-corporate-intel",
    "version": "0.1.0",
}

TOOLS = [
    {
        "name": "validate_corporate_number",
        "description": "Validate a 13-digit Japanese National Tax Agency (NTA) Corporate Number using the official check-digit formula.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "corporateNumber": {"type": "string", "description": "13-digit Japanese corporate number (hyphens/spaces allowed)."}
            },
            "required": ["corporateNumber"],
        },
    },
    {
        "name": "build_corporate_dossier",
        "description": "Build a unified English/Japanese corporate dossier from official METI gBizINFO and FSA EDINET APIs using environment API keys.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "corporateNumber": {"type": "string"},
                "companyName": {"type": "string"},
                "edinetDate": {"type": "string", "description": "YYYY-MM-DD filing date"},
            },
        },
    },
]


def handle_mcp_request(req: dict[str, Any]) -> dict[str, Any] | None:
    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}

    if method == "notifications/initialized":
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": SERVER_INFO,
                "capabilities": {"tools": {}},
            },
        }

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        try:
            if name == "validate_corporate_number":
                payload = validate_corporate_number(str(args.get("corporateNumber") or ""))
            elif name == "build_corporate_dossier":
                payload = build_corporate_dossier(
                    corporate_number=args.get("corporateNumber"),
                    company_name=args.get("companyName"),
                    edinet_date=args.get("edinetDate"),
                    gbiz_api_token=os.environ.get("GBIZ_API_TOKEN"),
                    edinet_api_key=os.environ.get("EDINET_API_KEY"),
                )
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {name}"},
                }
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}],
                    "isError": False,
                },
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {exc}"}],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unsupported method: {method}"},
    }


def serve_stdio() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle_mcp_request(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    serve_stdio()
