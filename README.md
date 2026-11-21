# Japan Corporate Intelligence MCP Server, Apify Actor & n8n Starter Kit

100% legal, zero-scraping official Japanese government open-data toolkit for AI agents, due-diligence workflows, and cross-border research.

## Official Data Sources (Commercial Redistribution Permitted with Attribution)
- **National Tax Agency (国税庁)** — 13-digit Corporate Number official check-digit validation
- **METI gBizINFO (経済産業省)** — Corporate profile, capital, employees, subsidies/procurement via official REST API v1
- **FSA EDINET (金融庁)** — Securities filings & disclosures via official API v2

## What's Included
1. **Zero-Dependency Local MCP Server (`src/mcp_server.py`)** — Plug directly into Claude Desktop, Cursor, or any MCP client using your own free official API tokens (`GBIZ_API_TOKEN`, `EDINET_API_KEY`).
2. **Apify Store Actor (`src/apify_entry.py` + `.actor/`)** — Pay-Per-Event ready (`corporate-dossier`).
3. **n8n Due-Diligence Workflow (`n8n/japan-corporate-due-diligence-workflow.json`)** — Import into n8n and query gBizINFO + EDINET in parallel.

## Quick Start (Local MCP Server)
```bash
export GBIZ_API_TOKEN="your-free-gbiz-token"
export EDINET_API_KEY="your-free-edinet-key"
python3 -m src.mcp_server
```

## Run Unit Tests
```bash
python3 -m unittest discover -s tests -v
```

## Ready-to-Use Starter Kit & Japanese Guide
- **BOOTH Starter Kit (ZIP + n8n Workflow + Setup Guide)**: https://inemuric.booth.pm/items/9195542
- **Zenn Technical Guide (Japanese)**: https://zenn.dev/inemuri/articles/japan-open-data-edinet-gbiz-mcp

## Mandatory Attribution Notice
本ツールは、国税庁法人番号公表サイト、経済産業省gBizINFO、金融庁EDINET API v2の公開仕様および公式APIデータを加工して出力します。出力結果の二次利用時は各省庁の利用規約に従い出典を明記してください。
