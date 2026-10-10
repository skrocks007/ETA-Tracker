import re
from utils.date_formatter import format_eta_date

WANHAI_MAIN_URL = "https://www.wanhai.com/views/Main.xhtml"
WANHAI_TRACKING_LIST_URL = "https://www.wanhai.com/views/cargo_track_v2/tracking_data_list.xhtml"


def track_wanhai(p, booking_number: str) -> str:
    is_cdp = False
    page1 = None

    try:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]

        # Purge extra tabs from previous loops
        while len(context.pages) > 1:
            try:
                context.pages[-1].close()
            except Exception:
                break

        page1 = context.new_page()
        is_cdp = True
    except Exception:
        browser = p.chromium.launch(
            headless=False, 
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page1 = context.new_page()

    created_pages = [page1]
    eta_result = "Not Found"

    try:
        # STEP 1: Open Main page & query booking number
        page1.goto(WANHAI_MAIN_URL, wait_until="domcontentloaded")
        page1.wait_for_timeout(2000)

        target_context = page1
        for frame in page1.frames:
            if "cargo" in frame.url.lower() or "track" in frame.url.lower():
                target_context = frame
                break

        search_input = target_context.locator("input[type='text'], input[name*='Search'], input[id*='refNo']").first
        if search_input.is_visible(timeout=5000):
            search_input.click()
            search_input.fill("")
            search_input.fill(booking_number)

            query_btn = target_context.locator("input[type='submit'], button:has-text('Query'), button:has-text('Search')").first
            if query_btn.is_visible():
                query_btn.click()
            else:
                target_context.keyboard.press("Enter")

            page1.wait_for_timeout(3500)

        # STEP 2: Open tracking_data_list.xhtml in a fresh tab
        page2 = context.new_page()
        created_pages.append(page2)
        page2.goto(WANHAI_TRACKING_LIST_URL, wait_until="domcontentloaded")
        page2.wait_for_timeout(2500)

        # STEP 3: Click Booking Data / B/L Data to trigger detail tab (Page 3)
        page3 = None
        try:
            link_selector = "a:has-text('Booking Data'), a:has-text('B/L Data'), a:has-text('Cargo Tracking')"
            detail_link = page2.locator(link_selector).first

            if detail_link.is_visible(timeout=5000):
                with context.expect_page(timeout=8000) as popup_info:
                    detail_link.click()

                page3 = popup_info.value
                created_pages.append(page3)
                page3.wait_for_load_state("domcontentloaded")
                page3.wait_for_timeout(2500)
        except Exception as e:
            print(f"Notice: Transition to detail tab skipped ({e})")

        if not page3 and len(context.pages) > len(created_pages):
            page3 = context.pages[-1]

        target_page = page3 if page3 else page2

        # STEP 4: Target the exact 'Port of Discharging' row in the table
        raw_date = target_page.evaluate("""() => {
            const rows = Array.from(document.querySelectorAll("tr"));
            for (let row of rows) {
                const text = row.innerText || "";
                if (text.includes("Port of Discharging")) {
                    // Extract date matching YYYY/MM/DD or YYYY-MM-DD format within this row
                    const match = text.match(/(\\d{4}[-/.]\\d{2}[-/.]\\d{2})/);
                    if (match) return match[1];
                }
            }
            return null;
        }""")

        # Fallback to RegEx over body text if JS row evaluation returns nothing
        if not raw_date:
            body_text = target_page.locator("body").inner_text()
            match = re.search(
                r"Port\s+of\s+Discharging[\s\S]{1,150}?(\d{4}[-/.]\d{2}[-/.]\d{2})",
                body_text,
                re.IGNORECASE
            )
            if match:
                raw_date = match.group(1).strip()

        if raw_date:
            # Standardizes '2026/11/17' into '17-Nov-26'
            eta_result = format_eta_date(raw_date)

    except Exception as e:
        print(f"Error tracking Wan Hai booking {booking_number}: {e}")
        eta_result = "Not Found"

    finally:
        # Cleanly close temporary tab windows created during this iteration
        if is_cdp:
            for p_tab in created_pages:
                try:
                    p_tab.close()
                except Exception:
                    pass
        else:
            context.close()
            browser.close()

    return eta_result