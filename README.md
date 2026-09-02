# Sunbird Trust — Inventory Management Register (Streamlit)

An editable, monthly-tracking version of the inventory dashboard — same
look and information as the HTML version, but every screen is backed by
`inventory_data.json`, which the app reads from and writes back to.

The dashboard can also download the shared Google Sheet and rebuild the JSON
file directly from it, so the locally displayed data can be refreshed without
manually exporting or copying spreadsheet rows.

## Run it

```bash
pip install -r requirements.txt
streamlit run inventory_app.py
```

It opens at http://localhost:8501

## Sync from Google Sheets

Use **↻ Sync from Google Sheet** in the header to download the configured
shared workbook and replace `inventory_data.json` with its current inventory
records. The existing JSON file is only replaced after the downloaded workbook
has been validated. The source sheet must remain accessible to people with the
link and each inventory tab needs a header row (within the first 20 rows) with
`Month` plus `Address` or `Location`; common column-name variants are accepted.

## What's in each tab

- **01 · Overview** — KPI cards, stock-by-category chart, combined trend
  line, and a location leaderboard. Read-only, always reflects the
  current data file.
- **02 · Locations** — searchable directory cards, a detail viewer
  (select a location to see its full inventory + notes), and an
  **✎ Edit directory** panel to add locations or update POC name /
  contact / address.
- **03 · Inventory** — pick a category to see its trend chart and a
  location × month closing-stock table, plus a **Monthly entry** panel:
  - *Edit an existing month* — adjust openings, additions, deletions,
    or notes for any month already on file.
  - *Add a new month* — pick the next month; opening stock is
    pre-filled from the previous month's closing stock for every
    location, so you only need to enter what came in, what went out,
    and any notes.
  - Closing stock (new / used / total) is always calculated for you —
    it isn't a field you edit directly.
- **04 · Activity Log** — every note across the register (transfers,
  losses/damage, consumption), filterable, newest first.

## Data file

`inventory_data.json` is the single source of truth, seeded from the
original Inventory Management Sheet (Jan–May 2026). Every save in the
app rewrites this file, so your edits persist across restarts. Back it
up before big edits if you want a safety net — it's plain JSON, so it's
easy to diff or version-control.

## Notes on the seed data

Two locations (Chingjaroi, Happiness home) had no POC on file in the
original sheet — worth filling in via the directory editor. Pillows at
Mantripukhri also shows a negative new-stock figure in Apr/May after a
transfer note; worth double-checking against the original record when
you next edit that month.
