import re
from utils.date_formatter import format_eta_date

EVERGREEN_URL = "https://ct.shipmentlink.com/servlet/TDB1_CargoTracking.do"


def track_emc(p, booking_number: str) -> str:
    is_cdp = False
    page = None

    # 1. Connect to debug Chrome or launch standalone browser
    try:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        is_cdp = True

        for p_tab in context.pages:
            if "shipmentlink.com" in p_tab.url:
                page = p_tab
                break

        if not page:
            page = context.new_page()
            page.goto(EVERGREEN_URL, wait_until="domcontentloaded")

    except Exception:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto(EVERGREEN_URL, wait_until="domcontentloaded")

    eta_result = "Not Found"

    try:
        page.bring_to_front()
        page.wait_for_timeout(1000)

        # 2. Dismiss cookie banner if present
        try:
            accept_btn = page.get_by_text("Accept All", exact=True)
            if accept_btn.is_visible(timeout=3000):
                accept_btn.click()
                page.wait_for_timeout(500)
        except Exception:
            pass

        # 3. Select 'Booking No.' radio button
        try:
            radio_booking = page.get_by_role("radio", name=re.compile(r"Booking", re.I))
            if radio_booking.is_visible():
                radio_booking.check()
        except Exception:
            pass

        # 4. Fill booking number into #NO text input
        input_field = page.locator("#NO").first
        input_field.wait_for(state="visible", timeout=10000)
        input_field.click()
        input_field.fill("")
        input_field.fill(booking_number)

        # 5. Submit query
        submit_btn = page.get_by_role("button", name="Submit").first
        submit_btn.click()

        # 6. Wait for tracking results table to render
        page.wait_for_timeout(4000)

        # 7. Extract raw date specifically from Place of Delivery / Port of Discharge row
        raw_date = page.evaluate("""() => {
            const rows = Array.from(document.querySelectorAll("tr"));

            // Strategy 1: Find row where <th> or <td> contains 'Place of Delivery' or 'Port of Discharge'
            for (let row of rows) {
                const header = row.querySelector("th");
                const headerText = header ? header.innerText.trim() : "";
                
                if (headerText.includes("Place of Delivery") || headerText.includes("Port of Discharge")) {
                    // Extract the text inside the align='center' cell (contains the ETA date)
                    const dateCell = row.querySelector("td[align='center']");
                    if (dateCell && dateCell.innerText.trim()) {
                        return dateCell.innerText.trim();
                    }
                    
                    // Fallback to cell regex search inside this specific row
                    const match = row.innerText.match(/([A-Za-z]{3}-\\d{2}-\\d{4})/);
                    if (match) return match[1];
                }
            }

            // Strategy 2: Search for any row containing NHAVA SHEVA or Destination port
            for (let row of rows) {
                const rowText = row.innerText || "";
                if (rowText.includes("Place of Delivery") && rowText.includes("NOV-")) {
                    const dateCell = row.querySelector("td[align='center']");
                    if (dateCell) return dateCell.innerText.trim();
                }
            }

            return null;
        }""")

        # Fallback RegEx if JS evaluation returns nothing
        if not raw_date:
            body_text = page.locator("body").inner_text()
            match = re.search(
                r"Place\s+of\s+Delivery[\s\S]{1,100}?([A-Za-z]{3}-\d{2}-\d{4})",
                body_text,
                re.IGNORECASE,
            )
            if match:
                raw_date = match.group(1).strip()

        if raw_date:
            # Standardizes 'NOV-09-2026' into '9-Nov-26'
            eta_result = format_eta_date(raw_date)

    except Exception as e:
        print(f"Error tracking Evergreen/EMC booking {booking_number}: {e}")
        eta_result = "Not Found"

    finally:
        if is_cdp and page:
            try:
                page.close()
            except Exception:
                pass
        elif not is_cdp:
            context.close()
            browser.close()

    return eta_result