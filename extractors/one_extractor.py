import re
from utils.date_formatter import format_eta_date

ONE_URL = "https://www.one-line.com/one-ecom/manage-shipment/cargo-tracking"


def track_one(p, booking_number: str) -> str:
    browser = p.chromium.launch(
        headless=False, 
        args=["--disable-blink-features=AutomationControlled"]
    )
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()

    eta_result = "Not Found"

    try:
        # 1. Open ONE tracking page
        page.goto(ONE_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

        # 2. Gently dismiss onboarding popover if it exists
        try:
            skip_btn = page.get_by_role("button", name="Skip").first
            if skip_btn.is_visible(timeout=2000):
                skip_btn.click()
                page.wait_for_timeout(1000)
        except Exception:
            pass

        # 3. Enter booking number cleanly into search box
        search_input = page.get_by_test_id("tnt-search-multiple-input")
        if not search_input.is_visible():
            search_input = page.locator("input[placeholder*='Booking'], input[type='text']").first

        search_input.wait_for(state="visible", timeout=10000)
        search_input.click()
        search_input.fill("")
        search_input.fill(booking_number)
        page.wait_for_timeout(500)

        # 4. Press Enter key natively to avoid triggering 500 error routes
        search_input.press("Enter")

        # 5. Check again for popover right after submit and dismiss if present
        page.wait_for_timeout(1500)
        try:
            skip_btn = page.get_by_role("button", name="Skip").first
            if skip_btn.is_visible(timeout=1500):
                skip_btn.click()
        except Exception:
            pass

        # 6. Wait for table results to load
        page.wait_for_timeout(4000)

        # 7. Extract raw date directly from the POD cell using JavaScript evaluation
        raw_date = page.evaluate("""() => {
            const podCells = document.querySelectorAll("div[class*='Table_pod-vessel-arrival-selector-alias']");
            if (!podCells || podCells.length === 0) return null;

            for (let cell of podCells) {
                const dateSpan = cell.querySelector("div[class*='EventDate_event-date-container'] span, span");
                if (dateSpan && dateSpan.innerText.trim().match(/^\\d{4}[-/.]\\d{2}[-/.]\\d{2}$/)) {
                    return dateSpan.innerText.trim();
                }
            }

            const bodyText = document.body.innerText;
            const textMatch = bodyText.match(/(\\d{4}[-/.]\\d{2}[-/.]\\d{2})/);
            return textMatch ? textMatch[1] : null;
        }""")

        # Fallback RegEx if DOM evaluation returns nothing
        if not raw_date:
            body_text = page.locator("body").inner_text()
            eta_match = re.search(
                r"(\d{4}[-/.]\d{2}[-/.]\d{2})", 
                body_text, 
                re.IGNORECASE
            )
            if eta_match:
                raw_date = eta_match.group(1).strip()

        if raw_date:
            # Standardizes '2026-11-11' into '11-Nov-26'
            eta_result = format_eta_date(raw_date)

    except Exception as e:
        print(f"Error tracking ONE booking {booking_number}: {e}")
        eta_result = "Not Found"

    finally:
        context.close()
        browser.close()

    return eta_result