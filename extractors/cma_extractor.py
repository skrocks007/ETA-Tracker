import re
from utils.date_formatter import format_eta_date

CMA_URL = "https://www.cma-cgm.com/ebusiness/tracking"


def track_cma(p, booking_number: str) -> str:
    is_cdp = False
    page = None

    try:
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        context = browser.contexts[0]
        is_cdp = True

        for p_tab in context.pages:
            if "cma-cgm.com" in p_tab.url:
                page = p_tab
                break

        if not page:
            page = context.new_page()
            page.goto(CMA_URL, wait_until="domcontentloaded")

    except Exception:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto(CMA_URL, wait_until="domcontentloaded")

    eta_result = "Not Found"

    try:
        page.bring_to_front()
        page.wait_for_timeout(1000)

        # 1. Target search input field
        ref_input = page.locator("#Reference, input[name='SearchViewModel.Reference']").first
        ref_input.wait_for(state="visible", timeout=10000)
        
        ref_input.click()
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        ref_input.fill(booking_number)
        page.wait_for_timeout(500)

        # 2. Trigger Search
        try:
            search_btn = page.locator("#btnTracking, button[type='submit'], button:has-text('Search')").first
            if search_btn.is_visible():
                search_btn.click()
            else:
                ref_input.press("Enter")
        except Exception:
            ref_input.press("Enter")

        # 3. Wait for tracking results page to render
        page.wait_for_timeout(5000)

        # ------------------------------------------------------
        # PASS 1: Sweep 3 Main ETA Regex Patterns
        # ------------------------------------------------------
        body_text = page.locator("body").inner_text()

        eta_patterns = [
            r"ETA\s*BERTH\s*AT\s*POD\s*[:\t\r\n]*(?:[A-Za-z]{3}\s+)?(\d{2}-[A-Za-z]{3}-\d{4}|\d{4}[-/.]\d{2}[-/.]\d{2})",
            r"(?:ETA|BERTH\s*AT\s*POD|ETA\s*POD|ESTIMATED\s*ARRIVAL)\s*[:\t\r\n]*(?:[A-Za-z]{3}\s+)?(\d{2}-[A-Za-z]{3}-\d{4}|\d{4}[-/.]\d{2}[-/.]\d{2})",
            r"(?:ARRIVED\s*AT\s*POD|DISCHARGED\s*AT\s*POD)\s*[:\t\r\n]*(?:[A-Za-z]{3}\s+)?(\d{2}-[A-Za-z]{3}-\d{4}|\d{4}[-/.]\d{2}[-/.]\d{2})",
        ]

        for pattern in eta_patterns:
            eta_match = re.search(pattern, body_text, re.IGNORECASE)
            if eta_match:
                raw_date = eta_match.group(1).strip()
                eta_result = format_eta_date(raw_date)
                break

        # DOM Table Cell Fallback before opening previous moves
        if eta_result == "Not Found":
            try:
                eta_cell = page.locator("td:has-text('ETA'), th:has-text('ETA'), td:has-text('Berth')").locator("xpath=following-sibling::td[1]").first
                if eta_cell.count() > 0 and eta_cell.is_visible():
                    raw_cell_text = eta_cell.inner_text().strip()
                    cell_date_match = re.search(r"(\d{2}-[A-Za-z]{3}-\d{4}|\d{4}[-/.]\d{2}[-/.]\d{2})", raw_cell_text)
                    if cell_date_match:
                        eta_result = format_eta_date(cell_date_match.group(1))
            except Exception:
                pass

        # ------------------------------------------------------
        # PASS 2: If Not Found -> Click "Display Previous Moves"
        # ------------------------------------------------------
        if eta_result == "Not Found":
            try:
                prev_moves_link = page.locator("a[aria-label='Display Previous Moves'], a:has-text('Display Previous Moves')").first
                if prev_moves_link.count() > 0 and prev_moves_link.is_visible():
                    prev_moves_link.click()
                    page.wait_for_timeout(2000)

                # Target the LAST 'Vessel Arrival' row in the expanded table
                vessel_arrival_spans = page.locator("tr:has(span.capsule:has-text('Vessel Arrival'))")
                if vessel_arrival_spans.count() > 0:
                    # Select the last Vessel Arrival row
                    last_arrival_row = vessel_arrival_spans.last
                    
                    # Extract date span inside that specific row
                    date_span = last_arrival_row.locator("span.calendar").first
                    if date_span.count() > 0:
                        raw_date_text = date_span.inner_text().strip()
                        # Extract date string like "18-AUG-2026" from "Tuesday, 18-AUG-2026"
                        date_match = re.search(r"(\d{2}-[A-Za-z]{3}-\d{4}|\d{4}[-/.]\d{2}[-/.]\d{2})", raw_date_text)
                        if date_match:
                            eta_result = format_eta_date(date_match.group(1))
            except Exception as e:
                print(f"    Notice: Display Previous Moves expansion failed ({e})")

    except Exception as e:
        print(f"Error tracking CMA booking {booking_number}: {e}")
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