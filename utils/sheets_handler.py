import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

class SheetsHandler:
    def __init__(self, json_key_path: str, spreadsheet_id: str, sheet_name: str = "ETA Tracker"):
        creds = Credentials.from_service_account_file(json_key_path, scopes=SCOPES)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_key(spreadsheet_id).worksheet(sheet_name)

    def get_pending_bookings(self):
        records = self.sheet.get_all_records()
        pending_list = []

        for idx, row in enumerate(records, start=2):
            # Supports both "Booking No" and "Booking No."
            b_num = str(row.get("Booking No", row.get("Booking No.", ""))).strip()
            carrier = str(row.get("Shipping Line", "")).strip().upper()
            eta = str(row.get("ETA", "")).strip()

            # Skip empty rows, invalid formula values, or missing booking numbers
            if not b_num or b_num.startswith("#") or carrier.startswith("#"):
                continue

            # Process only active rows that need tracking
            if eta in ["", "(auto)", "Pending", "Not Found", "Failed"]:
                pending_list.append({
                    "row_index": idx,
                    "booking_number": b_num,
                    "carrier": carrier,
                })

        return pending_list

    def update_eta(self, row_index: int, eta_value: str):
        self.sheet.update_acell(f"C{row_index}", eta_value)