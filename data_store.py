import gspread
import pandas as pd
import os
import json
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
SHEET_NAME = "happy_hour_data"
WORKSHEET_NAME = "Sheet1"

def get_client():
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not sa_json:
        raise RuntimeError("Missing GOOGLE_SERVICE_ACCOUNT_JSON environment variable")

    creds_dict = json.loads(sa_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

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
