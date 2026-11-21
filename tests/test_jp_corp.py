import unittest

from src.jp_corp_client import (
    normalize_edinet_documents,
    normalize_gbiz_record,
    validate_corporate_number,
)
from src.mcp_server import handle_mcp_request


class TestJapanCorporateIntel(unittest.TestCase):
    def test_official_nta_check_digit(self) -> None:
        # National Tax Agency official example: 7000012050002 (Ministry of Finance) / 8000012010001 (Cabinet Secretariat)
        # Verify formula consistency: compute expected check digit for body 000012050002
        # Positions from right: 2*1 + 0*2 + 0*1 + 0*2 + 5*1 + 0*2 + 2*1 + 1*2 + 0*1 + 0*2 + 0*1 + 0*2 = 2+5+2+2 = 11 -> 11%9 = 2 -> 9-2 = 7
        valid_res = validate_corporate_number("7000012050002")
        self.assertTrue(valid_res["valid"])
        self.assertEqual(valid_res["expectedCheckDigit"], 7)

        bad_res = validate_corporate_number("6000012050002")
        self.assertFalse(bad_res["valid"])
        self.assertEqual(bad_res["expectedCheckDigit"], 7)

        short_res = validate_corporate_number("12345")
        self.assertFalse(short_res["valid"])

    def test_normalization_and_attribution(self) -> None:
        gbiz = normalize_gbiz_record(
            {
                "corporate_number": "7000012050002",
                "name": "テスト株式会社",
                "name_en": "Test Corp.",
                "capital_stock": 10000000,
                "employee_number": 50,
            }
        )
        self.assertEqual(gbiz["nameEn"], "Test Corp.")
        self.assertIn("gBizINFO", gbiz["attribution"])

        edinet = normalize_edinet_documents(
            {
                "results": [
                    {"docID": "S100ABCD", "JCN": "7000012050002", "filerName": "テスト株式会社", "pdfFlag": "1", "xbrlFlag": "1"},
                    {"docID": "S100OTHER", "JCN": "1111111111111", "filerName": "他社"},
                ]
            },
            corporate_number="7000012050002",
        )
        self.assertEqual(len(edinet), 1)
        self.assertEqual(edinet[0]["docId"], "S100ABCD")
        self.assertTrue(edinet[0]["pdfFlag"])
        self.assertIn("EDINET", edinet[0]["attribution"])

    def test_mcp_jsonrpc_handshake_and_tool_call(self) -> None:
        init = handle_mcp_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual(init["result"]["serverInfo"]["name"], "flowcraft-japan-corporate-intel")

        tools = handle_mcp_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tool_names = [t["name"] for t in tools["result"]["tools"]]
        self.assertIn("validate_corporate_number", tool_names)
        self.assertIn("build_corporate_dossier", tool_names)

        call = handle_mcp_request(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "validate_corporate_number", "arguments": {"corporateNumber": "7000012050002"}},
            }
        )
        self.assertFalse(call["result"]["isError"])
        self.assertIn('"valid": true', call["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
