import re
from datetime import datetime
from utils.date_formatter import format_eta_date

MSC_URL = "https://www.msc.com/en/track-a-shipment"


def parse_msc_date(raw_date_str):
    """Converts DD/MM/YYYY or standard formats into '8-Oct-26' format."""
    if not raw_date_str:
        return "Not Found"

    cleaned = raw_date_str.strip()

    # Formats to attempt parsing
    input_formats = [
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d-%b-%y",
    ]

    dt = None
    for fmt in input_formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            break
        except ValueError:
            pass

    if dt:
        # Formats into '8-Oct-26' (lstrip('0') removes leading zero from day)
        day = dt.strftime("%d").lstrip("0")
        month_year = dt.strftime("%b-%y")
        return f"{day}-{month_year}"

    # Fall back to utility date formatter if parsing fails
    try:
        formatted = format_eta_date(cleaned)
        if formatted and formatted != "Not Found":
            return formatted
    except Exception:
        pass

    return cleaned


def track_msc(p, booking_number: str) -> str:
    browser = p.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled"]
    )
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()

    eta_result = "Not Found"

    try:
        # 1. Open MSC Tracking Page
        page.goto(MSC_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # 2. Hardened Cookie Banner & Overlay Handler
        try:
            accept_btn = page.get_by_role("button", name="Accept All").first
            if not accept_btn.is_visible():
                accept_btn = page.locator("#onetrust-accept-btn-handler, button:has-text('Accept All')").first
            
            if accept_btn.is_visible(timeout=3000):
                try:
                    accept_btn.click(timeout=2000)
                except Exception:
                    accept_btn.click(force=True)
                page.wait_for_timeout(1000)
        except Exception:
            pass

        # Cleanup lingering modal/backdrop elements if any remain on screen
        try:
            page.evaluate("""
                () => {
                    const overlays = document.querySelectorAll('.onetrust-pc-dark-filter, #onetrust-banner-sdk, .modal-backdrop');
                    overlays.forEach(el => el.remove());
                }
            """)
        except Exception:
            pass

        # 3. Explicitly Click 'Booking Number' Radio Label
        booking_radio_label = page.locator("label").filter(has_text="Booking Number").first
        if booking_radio_label.count() > 0:
            booking_radio_label.click()
        else:
            page.get_by_text("Booking Number").first.click()
        
        page.wait_for_timeout(1000)

        # 4. Fill Booking Input Box
        input_box = page.locator("#trackingNumber").first
        if not input_box.is_visible():
            input_box = page.get_by_role("textbox", name="Enter a Booking Number").first

        input_box.click()
        input_box.fill("")
        input_box.press_sequentially(booking_number, delay=50)
        page.wait_for_timeout(500)

        # 5. Submit Search Form
        search_btn = page.locator("button.msc-search-autocomplete__search").first
        if search_btn.count() > 0 and search_btn.is_enabled():
            search_btn.click()
        else:
            page.locator("form.js-form").evaluate("form => form.requestSubmit()")

        page.wait_for_timeout(5000)

        # ------------------------------------------------------
        # STEP 1: Attempt POD ETA Extraction
        # ------------------------------------------------------
        pod_eta_container = page.locator("div.msc-flow-tracking__data").filter(has_text="POD ETA").first
        
        try:
            if pod_eta_container.is_visible(timeout=4000):
                val_span = pod_eta_container.locator("span.data-value").first
                if val_span.count() > 0:
                    raw_text = val_span.inner_text().strip()
                    if raw_text:
                        eta_result = parse_msc_date(raw_text)
        except Exception:
            pass

        # ------------------------------------------------------
        # STEP 2: Fallback to "Import Discharged from Vessel" Event Date
        # ------------------------------------------------------
        if eta_result == "Not Found":
            try:
                # Find timeline row step div containing 'Import Discharged from Vessel'
                discharged_row = page.locator("div.msc-flow-tracking__step").filter(
                    has_text="Import Discharged from Vessel"
                ).first

                if discharged_row.count() > 0:
                    # Locate the date span inside this specific timeline step
                    date_span = discharged_row.locator("span[x-text*='event.Date']").first
                    if date_span.count() == 0:
                        date_span = discharged_row.locator("span.data-value").first

                    if date_span.count() > 0:
                        raw_discharged_date = date_span.inner_text().strip()
                        if raw_discharged_date:
                            eta_result = parse_msc_date(raw_discharged_date)
                            print(f"    [+] Extracted ETA from 'Import Discharged from Vessel': {eta_result}")
            except Exception as e:
                print(f"    Notice: Discharged move extraction error ({e})")

        # ------------------------------------------------------
        # STEP 3: Fallback 2: Broad Body Regex Sweep
        # ------------------------------------------------------
        if eta_result == "Not Found":
            body_text = page.locator("body").inner_text()
            eta_match = re.search(
                r"POD\s*ETA\s*[:\t\r\n]*(\d{2}/\d{2}/\d{4})",
                body_text,
                re.IGNORECASE,
            )
            if eta_match:
                eta_result = parse_msc_date(eta_match.group(1))

    except Exception as e:
        print(f"Error tracking MSC booking {booking_number}: {e}")
        eta_result = "Not Found"

    finally:
        context.close()
        browser.close()

    return eta_result