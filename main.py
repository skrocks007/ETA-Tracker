import time
from playwright.sync_api import sync_playwright
from utils.sheets_handler import SheetsHandler
from utils.browser_launcher import ensure_chrome_debugging

from extractors.yml_extractor import track_yml
from extractors.one_extractor import track_one
from extractors.cma_extractor import track_cma
from extractors.emc_extractor import track_emc
from extractors.wanhai_extractor import track_wanhai
from extractors.msc_extractor import track_msc

CARRIER_MAP = {
    "YML": track_yml,
    "YANGMING": track_yml,
    "ONE": track_one,
    "CMA": track_cma,
    "CMA CGM": track_cma,
    "EMC": track_emc,
    "EVERGREEN": track_emc,
    "WANHAI": track_wanhai,
    "WAN HAI": track_wanhai,
    "MSC": track_msc,
    "MEDITERRANEAN SHIPPING COMPANY": track_msc,
}

GOOGLE_SHEET_ID = "1-8hFBIYdhP8XGZxsYSmN0gV2ZNZ0Su5syDIYCXDJ0P4"
SERVICE_ACCOUNT_FILE = "service_account.json"


def process_record(p, record, sheets):
    """Tracks a single booking record and updates the sheet."""
    row_idx = record["row_index"]
    b_num = record["booking_number"]
    carrier = record["carrier"]

    print(f"Tracking Row {row_idx}: [{carrier}] {b_num}...")

    if carrier in CARRIER_MAP:
        try:
            extractor = CARRIER_MAP[carrier]
            eta_result = extractor(p, b_num)
        except Exception as e:
            print(f"Error tracking Row {row_idx} ({b_num}): {e}")
            eta_result = "Not Found"
    else:
        print(f"Row {row_idx}: Unsupported carrier '{carrier}'")
        eta_result = "Not Found"

    sheets.update_eta(row_idx, eta_result)
    print(f"Row {row_idx} Updated -> ETA: {eta_result}\n")
    return eta_result


def get_not_found_records_robust(sheets):
    """
    Robustly scans raw sheet values for any rows where ETA is 'Not Found'.
    Matches columns dynamically regardless of exact header casing.
    """
    all_values = sheets.sheet.get_all_values()
    if not all_values:
        return []

    headers = [str(h).strip().lower() for h in all_values[0]]
    
    # Dynamically find column indexes
    booking_col_idx = -1
    carrier_col_idx = -1
    eta_col_idx = -1

    for idx, h in enumerate(headers):
        if "booking" in h:
            booking_col_idx = idx
        elif "line" in h or "carrier" in h or "shipping" in h:
            carrier_col_idx = idx
        elif "eta" in h or "status" in h:
            eta_col_idx = idx

    # Fallbacks if headers weren't named expectedly (Defaulting to standard 0, 1, 2 layout)
    if booking_col_idx == -1: booking_col_idx = 0
    if carrier_col_idx == -1: carrier_col_idx = 1
    if eta_col_idx == -1: eta_col_idx = 2

    not_found_list = []

    # Iterate starting from row index 2 (1-based sheet index)
    for row_idx_0, row in enumerate(all_values[1:], start=2):
        if len(row) <= max(booking_col_idx, carrier_col_idx, eta_col_idx):
            continue

        b_num = str(row[booking_col_idx]).strip()
        carrier = str(row[carrier_col_idx]).strip().upper()
        eta_val = str(row[eta_col_idx]).strip()

        if eta_val.lower() == "not found" and b_num:
            not_found_list.append({
                "row_index": row_idx_0,
                "booking_number": b_num,
                "carrier": carrier,
                "eta": eta_val
            })

    return not_found_list


def main():
    sheets = SheetsHandler(
        json_key_path=SERVICE_ACCOUNT_FILE,
        spreadsheet_id=GOOGLE_SHEET_ID,
        sheet_name="ETA Tracker"
    )

    pending_rows = sheets.get_pending_bookings()
    
    if pending_rows:
        needs_debug_chrome = any(r["carrier"] in ["CMA", "CMA CGM", "WANHAI", "WAN HAI", "MSC"] for r in pending_rows)
        if needs_debug_chrome:
            ensure_chrome_debugging()

        with sync_playwright() as p:
            # =======================================================
            # PASS 1: Main tracking loop for all pending bookings
            # =======================================================
            for record in pending_rows:
                process_record(p, record, sheets)
                time.sleep(1)
    else:
        print("No blank pending bookings found on ETA Tracker.")

    # =======================================================
    # PASS 2: Explicit Re-check for ALL 'Not Found' Records
    # =======================================================
    not_found_records = get_not_found_records_robust(sheets)

    if not_found_records:
        print("\n" + "=" * 60)
        print(f"Starting re-check for {len(not_found_records)} 'Not Found' booking(s)...")
        print("=" * 60 + "\n")

        time.sleep(2)

        needs_debug_chrome_retry = any(r["carrier"] in ["CMA", "CMA CGM", "WANHAI", "WAN HAI", "MSC"] for r in not_found_records)
        if needs_debug_chrome_retry:
            ensure_chrome_debugging()

        with sync_playwright() as p:
            for record in not_found_records:
                row_idx = record["row_index"]
                b_num = record["booking_number"]
                carrier = record["carrier"]

                print(f"[RE-TRY PASS] Re-checking Row {row_idx}: [{carrier}] {b_num}...")

                if carrier in CARRIER_MAP:
                    try:
                        extractor = CARRIER_MAP[carrier]
                        eta_result = extractor(p, b_num)
                    except Exception as e:
                        print(f"Retry error on Row {row_idx} ({b_num}): {e}")
                        eta_result = "Not Found"
                else:
                    eta_result = "Not Found"

                sheets.update_eta(row_idx, eta_result)
                if eta_result != "Not Found":
                    print(f"Row {row_idx} Successfully Resolved -> ETA: {eta_result}\n")
                else:
                    print(f"Row {row_idx} Still Not Found on Re-check.\n")

                time.sleep(1)
    else:
        print("\nNo 'Not Found' records found in the sheet to re-check.")

    print("\nAll tracking tasks and re-checks completed successfully!")


if __name__ == "__main__":
    main()