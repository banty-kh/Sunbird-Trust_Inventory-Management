"""Regression tests for the Google Sheets workbook importer."""

from io import BytesIO
import unittest

import pandas as pd

from inventory_app import spreadsheet_to_data


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


if __name__ == "__main__":
    unittest.main()
