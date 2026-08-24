"""Update the verified daily production counts in the 40/400 Google Sheet."""

import argparse
import json
import os
from datetime import date


DEFAULT_SHEET_NAME = "40/400 Meals Accountability Dashboard"
DEFAULT_WORKSHEET = "Daily Tracker"
HEADERS = ["Date", "Recipes Published", "Pins Published"]


def upsert_daily_row(worksheet, day, recipes, pins):
    """Create or update one row for day; never create duplicate dates."""
    values = worksheet.get_all_values()
    if not values:
        worksheet.append_row(HEADERS)
        values = [HEADERS]

    header = values[0]
    missing = [name for name in HEADERS if name not in header]
    if missing:
        raise ValueError("Dashboard is missing columns: " + ", ".join(missing))

    date_col = header.index("Date") + 1
    recipe_col = header.index("Recipes Published") + 1
    pin_col = header.index("Pins Published") + 1

    target_row = None
    for row_number, row in enumerate(values[1:], start=2):
        if len(row) >= date_col and row[date_col - 1].strip() == day:
            target_row = row_number
            break

    if target_row is None:
        new_row = [""] * len(header)
        new_row[date_col - 1] = day
        new_row[recipe_col - 1] = recipes
        new_row[pin_col - 1] = pins
        worksheet.append_row(new_row, value_input_option="USER_ENTERED")
        return "created"

    worksheet.update_cell(target_row, recipe_col, recipes)
    worksheet.update_cell(target_row, pin_col, pins)
    return "updated"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipes", type=int, required=True)
    parser.add_argument("--pins", type=int, required=True)
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    credentials = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not credentials:
        print("Google Sheet update skipped: GOOGLE_SERVICE_ACCOUNT_JSON is not configured.")
        return

    import gspread

    client = gspread.service_account_from_dict(json.loads(credentials))
    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "").strip()
    spreadsheet = (
        client.open_by_key(sheet_id)
        if sheet_id
        else client.open(os.environ.get("GOOGLE_SHEET_NAME", DEFAULT_SHEET_NAME))
    )
    worksheet = spreadsheet.worksheet(
        os.environ.get("GOOGLE_WORKSHEET_NAME", DEFAULT_WORKSHEET)
    )
    result = upsert_daily_row(
        worksheet, args.date, max(args.recipes, 0), max(args.pins, 0)
    )
    print(f"Google dashboard row {result} for {args.date}.")


if __name__ == "__main__":
    main()
