"""Official Japanese Government Open-Data Integrator (NTA Corporate Number / METI gBizINFO / FSA EDINET).

100% legal, zero scraping. Uses only official public government APIs with caller-supplied API keys
and always attaches mandatory official data source attribution.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from typing import Any


USER_AGENT = "FlowCraft-JapanCorporateIntel/0.1 (+https://github.com/inemurisandesu/japan-corporate-intel-mcp)"

ATTRIBUTIONS = {
    "nta_corporate_number": "国税庁法人番号公表サイト (https://www.houjin-bangou.nta.go.jp/) の公開仕様に基づく検証",
    "gbizinfo": "経済産業省 gBizINFO (https://info.gbiz.go.jp/) のデータを加工して作成",
    "edinet": "金融庁 EDINET API v2 (https://disclosure2.edinet-fsa.go.jp/) のデータを加工して作成",
}


def validate_corporate_number(raw: str) -> dict[str, Any]:
    """Validate a 13-digit Japanese Corporate Number using NTA's official check-digit formula.

    Formula (National Tax Agency):
    Given digits d1..d13 (where d1 is check digit and d2..d13 are the 12-digit base):
    Let p_i = digit at position i from the right (1-indexed, for i = 1..12, i.e., d13..d2).
    Weight q_i = 1 if i is odd, 2 if i is even.
    Check digit = 9 - (sum(p_i * q_i) % 9).
    """
    cleaned = re.sub(r"[\s-]", "", str(raw or ""))
    if not re.fullmatch(r"\d{13}", cleaned):
        return {
            "input": raw,
            "normalized": cleaned,
            "valid": False,
            "reason": "Corporate number must be exactly 13 digits.",
            "attribution": ATTRIBUTIONS["nta_corporate_number"],
        }

    check_digit = int(cleaned[0])
    body_12 = cleaned[1:]
    # Right-to-left (1-indexed) weights: odd -> 1, even -> 2
    total = 0
    for idx_from_right, ch in enumerate(reversed(body_12), start=1):
        weight = 1 if idx_from_right % 2 == 1 else 2
        total += int(ch) * weight
    expected = 9 - (total % 9)
    valid = check_digit == expected
    return {
        "input": raw,
        "normalized": cleaned,
        "valid": valid,
        "expectedCheckDigit": expected,
        "actualCheckDigit": check_digit,
        "reason": None if valid else f"Check digit mismatch (expected {expected}, got {check_digit})",
        "attribution": ATTRIBUTIONS["nta_corporate_number"],
    }


def _http_get_json(url: str, headers: dict[str, str] | None = None, timeout: int = 15) -> dict[str, Any]:
    req_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize_gbiz_record(raw_record: dict[str, Any]) -> dict[str, Any]:
    """Normalize a METI gBizINFO API v1 company record into clean English/Japanese fields."""
    return {
        "corporateNumber": raw_record.get("corporate_number"),
        "nameJa": raw_record.get("name"),
        "nameKana": raw_record.get("kana"),
        "nameEn": raw_record.get("name_en"),
        "location": raw_record.get("location"),
        "status": raw_record.get("status"),
        "dateOfEstablishment": raw_record.get("date_of_establishment"),
        "capitalStockJpy": raw_record.get("capital_stock"),
        "employeeNumber": raw_record.get("employee_number"),
        "representativeName": raw_record.get("representative_name"),
        "companyUrl": raw_record.get("company_url"),
        "businessSummary": raw_record.get("business_summary"),
        "updateDate": raw_record.get("update_date"),
        "source": "gBizINFO",
        "attribution": ATTRIBUTIONS["gbizinfo"],
    }


def normalize_edinet_documents(payload: dict[str, Any], corporate_number: str | None = None) -> list[dict[str, Any]]:
    """Normalize FSA EDINET API v2 document list results, optionally filtering by corporate number."""
    results = payload.get("results") or []
    normalized: list[dict[str, Any]] = []
    target_cn = re.sub(r"[\s-]", "", corporate_number) if corporate_number else None

    for doc in results:
        if not isinstance(doc, dict):
            continue
        doc_cn = str(doc.get("JCN") or "").strip()
        if target_cn and doc_cn != target_cn:
            continue
        normalized.append(
            {
                "docId": doc.get("docID"),
                "edinetCode": doc.get("edinetCode"),
                "corporateNumber": doc_cn or None,
                "filerName": doc.get("filerName"),
                "secCode": doc.get("secCode"),
                "docDescription": doc.get("docDescription"),
                "formCode": doc.get("formCode"),
                "submitDateTime": doc.get("submitDateTime"),
                "periodStart": doc.get("periodStart"),
                "periodEnd": doc.get("periodEnd"),
                "pdfFlag": doc.get("pdfFlag") == "1",
                "xbrlFlag": doc.get("xbrlFlag") == "1",
                "source": "EDINET_v2",
                "attribution": ATTRIBUTIONS["edinet"],
            }
        )
    return normalized


def fetch_gbiz_company(
    *,
    corporate_number: str | None = None,
    company_name: str | None = None,
    api_token: str | None = None,
) -> dict[str, Any]:
    if not api_token:
        return {"status": "skipped", "reason": "gbizApiToken not provided", "records": []}

    headers = {"X-hojinInfo-api-token": api_token}
    if corporate_number:
        check = validate_corporate_number(corporate_number)
        if not check["valid"]:
            return {"status": "invalid_input", "reason": check["reason"], "records": []}
        url = f"https://info.gbiz.go.jp/hojin/v1/hojin/{check['normalized']}"
    elif company_name:
        qs = urllib.parse.urlencode({"name": company_name.strip(), "limit": "10"})
        url = f"https://info.gbiz.go.jp/hojin/v1/hojin?{qs}"
    else:
        return {"status": "invalid_input", "reason": "Provide corporateNumber or companyName", "records": []}

    raw = _http_get_json(url, headers=headers)
    infos = raw.get("hojin-infos") or []
    return {
        "status": "ok",
        "count": len(infos),
        "records": [normalize_gbiz_record(r) for r in infos if isinstance(r, dict)],
        "attribution": ATTRIBUTIONS["gbizinfo"],
    }


def fetch_edinet_filings(
    *,
    date_yyyy_mm_dd: str,
    api_key: str | None = None,
    corporate_number: str | None = None,
) -> dict[str, Any]:
    if not api_key:
        return {"status": "skipped", "reason": "edinetApiKey not provided", "filings": []}
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(date_yyyy_mm_dd or "")):
        return {"status": "invalid_input", "reason": "edinetDate must be YYYY-MM-DD", "filings": []}

    qs = urllib.parse.urlencode({"date": date_yyyy_mm_dd, "type": "2", "Subscription-Key": api_key})
    url = f"https://api.edinet-fsa.go.jp/api/v2/documents.json?{qs}"
    raw = _http_get_json(url)
    filings = normalize_edinet_documents(raw, corporate_number=corporate_number)
    return {
        "status": "ok",
        "date": date_yyyy_mm_dd,
        "count": len(filings),
        "filings": filings,
        "attribution": ATTRIBUTIONS["edinet"],
    }


def build_corporate_dossier(
    *,
    corporate_number: str | None = None,
    company_name: str | None = None,
    edinet_date: str | None = None,
    gbiz_api_token: str | None = None,
    edinet_api_key: str | None = None,
) -> dict[str, Any]:
    validation = validate_corporate_number(corporate_number) if corporate_number else None
    resolved_cn = validation["normalized"] if (validation and validation["valid"]) else None

    gbiz = fetch_gbiz_company(
        corporate_number=resolved_cn,
        company_name=company_name if not resolved_cn else None,
        api_token=gbiz_api_token,
    )
    if not resolved_cn and gbiz.get("records"):
        resolved_cn = gbiz["records"][0].get("corporateNumber")

    edinet = (
        fetch_edinet_filings(
            date_yyyy_mm_dd=edinet_date,
            api_key=edinet_api_key,
            corporate_number=resolved_cn,
        )
        if edinet_date
        else {"status": "skipped", "reason": "edinetDate not provided", "filings": []}
    )

    return {
        "corporateNumberValidation": validation,
        "resolvedCorporateNumber": resolved_cn,
        "gbiz": gbiz,
        "edinet": edinet,
        "attributions": list(ATTRIBUTIONS.values()),
    }
