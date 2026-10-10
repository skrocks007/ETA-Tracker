import time
from playwright.sync_api import sync_playwright
from utils.sheets_handler import SheetsHandler
from utils.browser_launcher import ensure_chrome_debugging

from extractors.yml_extractor import track_yml
from extractors.one_extractor import track_one
from extractors.cma_extractor import track_cma
from extractors.emc_extractor import track_emc
from extractors.wanhai_extractor import track_wanhai
from extractors.msc_extractor import track_msc  # 1. Added MSC Import

CARRIER_MAP = {
    "YML": track_yml,
    "YANGMING": track_yml,
    "ONE": track_one,
    "CMA": track_cma,
    "EMC": track_emc,
    "WANHAI": track_wanhai,
    "MSC": track_msc,  # 2. Added MSC Carrier Mapping
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


def main():
    sheets = SheetsHandler(
        json_key_path=SERVICE_ACCOUNT_FILE,
        spreadsheet_id=GOOGLE_SHEET_ID,
        sheet_name="ETA Tracker"
    )

    pending_rows = sheets.get_pending_bookings()
    if not pending_rows:
        print("No pending bookings found on ETA Tracker.")
        return

    # 3. Check if CMA, WANHAI, or MSC exist in pending queue
    needs_debug_chrome = any(r["carrier"] in ["CMA", "WANHAI",] for r in pending_rows)
    if needs_debug_chrome:
        ensure_chrome_debugging()

    with sync_playwright() as p:
        # =======================================================
        # PASS 1: Main tracking loop for all pending bookings
        # =======================================================
        for record in pending_rows:
            process_record(p, record, sheets)
            time.sleep(1)

        # =======================================================
        # PASS 2: Single lightweight re-check for "Not Found"
        # =======================================================
        refreshed_pending = sheets.get_pending_bookings()
        not_found_records = [
            r for r in refreshed_pending 
            if r.get("eta") == "Not Found" or r.get("status") == "Not Found"
        ]

        if not_found_records:
            print("=" * 60)
            print(f"Starting lightweight re-check for {len(not_found_records)} 'Not Found' booking(s)...")
            print("=" * 60 + "\n")

            time.sleep(2)  # Brief pause before retry pass

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

                # Only write and report if the retry successfully retrieved an ETA
                if eta_result != "Not Found":
                    sheets.update_eta(row_idx, eta_result)
                    print(f"Row {row_idx} Successfully Resolved -> ETA: {eta_result}\n")
                else:
                    print(f"Row {row_idx} Still Not Found on Re-check.\n")

                time.sleep(1)

    print("All tracking tasks and re-checks completed successfully!")


if __name__ == "__main__":
    main()