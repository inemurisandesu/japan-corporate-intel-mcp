"""Apify Actor entry point with Pay-Per-Event billing (`corporate-dossier`)."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from .jp_corp_client import build_corporate_dossier


async def run_actor() -> None:
    from apify import Actor

    async with Actor:
        inp: dict[str, Any] = await Actor.get_input() or {}
        dossier = build_corporate_dossier(
            corporate_number=inp.get("corporateNumber"),
            company_name=inp.get("companyName"),
            edinet_date=inp.get("edinetDate"),
            gbiz_api_token=inp.get("gbizApiToken") or os.environ.get("GBIZ_API_TOKEN"),
            edinet_api_key=inp.get("edinetApiKey") or os.environ.get("EDINET_API_KEY"),
        )
        await Actor.push_data(dossier, charged_event_name="corporate-dossier")
        await Actor.set_value("SUMMARY", {
            "resolvedCorporateNumber": dossier["resolvedCorporateNumber"],
            "gbizStatus": dossier["gbiz"].get("status"),
            "edinetStatus": dossier["edinet"].get("status"),
        })


if __name__ == "__main__":
    asyncio.run(run_actor())
