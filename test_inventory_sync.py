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

    def test_accepts_months_grouped_across_columns(self):
        rows = [
            ["Inventory register"],
            ["Address", "POC", "January 2026", "", "", "February 2026", "", ""],
            ["", "", "New", "Used", "Total", "New", "Used", "Total"],
            ["Aben", "Pratip", 3, 2, 5, 4, 2, 6],
        ]
        workbook = BytesIO()
        with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
            pd.DataFrame(rows).to_excel(writer, sheet_name="Blankets", header=False, index=False)

        data = spreadsheet_to_data(workbook.getvalue())

        january, february = data["items"]["Blankets"]
        self.assertEqual((january["month"], january["year"]), ("January", "2026"))
        self.assertEqual((january["closing_new"], january["closing_used"], january["closing_total"]), (3, 2, 5))
        self.assertEqual((february["month"], february["closing_total"]), ("February", 6))


if __name__ == "__main__":
    unittest.main()
