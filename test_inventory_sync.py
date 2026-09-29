"""Regression tests for the Google Sheets workbook importer."""

from io import BytesIO
import unittest

import pandas as pd

from inventory_app import spreadsheet_to_data, verify_inventory_data_integrity


class SpreadsheetToDataTests(unittest.TestCase):
    def test_accepts_month_and_year_and_a_header_after_instruction_rows(self):
        rows = [["Sunbird Trust inventory register"] for _ in range(25)]
        rows.append(["Item", "Location & Address", "Month & Year", "Closing Stock"])
        rows.append(["Blankets", "Aben", "August 2026", 12])

        workbook = BytesIO()
        with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
            pd.DataFrame(rows).to_excel(writer, sheet_name="Inventory", header=False, index=False)

        data = spreadsheet_to_data(workbook.getvalue())

        self.assertEqual(data["items"]["Blankets"][0]["address"], "Aben")
        self.assertEqual(data["items"]["Blankets"][0]["month"], "August")
        self.assertEqual(data["items"]["Blankets"][0]["year"], "2026")
        self.assertEqual(data["items"]["Blankets"][0]["closing_total"], 12)

    def test_preserves_snapshot_stock_without_creating_a_false_audit_error(self):
        workbook = BytesIO()
        pd.DataFrame([
            ["Location & Address", "Month & Year", "Closing Stock"],
            ["Aben", "January 2026", "1,284"],
        ]).to_excel(workbook, sheet_name="Bedsheets", header=False, index=False)

        data = spreadsheet_to_data(workbook.getvalue())
        record = data["items"]["Bedsheets"][0]

        self.assertEqual(record["closing_new"], 1284)
        self.assertEqual(record["closing_used"], 0)
        self.assertEqual(verify_inventory_data_integrity(data)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
