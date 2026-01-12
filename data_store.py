import gspread
import pandas as pd
from google.auth import default

SHEET_NAME = "OKC Happy Hours"
WORKSHEET_NAME = "Sheet1"

def get_client():
    creds, _ = default(scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return gspread.authorize(creds)

def get_worksheet():
    client = get_client()
    sheet = client.open(SHEET_NAME)
    return sheet.worksheet(WORKSHEET_NAME)

def load_locations():
    ws = get_worksheet()
    records = ws.get_all_records()
    df = pd.DataFrame(records)

    if not df.empty:
        df["id"] = df["id"].astype(int)

    return df

def insert_location(row):
    ws = get_worksheet()

    existing = ws.get_all_records()
    next_id = max([r["id"] for r in existing], default=0) + 1

    row_with_id = {
        "id": next_id,
        **row
    }

    ws.append_row(list(row_with_id.values()))
    return next_id

def update_description(location_id, description):
    ws = get_worksheet()
    records = ws.get_all_records()

    for i, r in enumerate(records, start=2):
        if r["id"] == location_id:
            ws.update_cell(i, 6, description)  # description column
            return

def delete_location(location_id):
    ws = get_worksheet()
    records = ws.get_all_records()

    for i, r in enumerate(records, start=2):
        if r["id"] == location_id:
            ws.delete_rows(i)
            return
