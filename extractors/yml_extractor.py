import re
from playwright.sync_api import TimeoutError
from utils.date_formatter import format_eta_date


def track_yml(p, booking_number: str) -> str:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()

    eta_result = "Not Found"

    try:
        # 1. Open tracking page
        page.goto("https://www.yangming.com/en/esolution/cargo_tracking", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        # 2. Input booking number
        search_input = page.get_by_role("textbox").first
        search_input.click()
        search_input.fill("")
        search_input.fill(booking_number)

        # 3. Trigger Search
        page.get_by_role("button", name="Search").click()

        # 4. Wait for Routing Schedule timeline elements to render
        page.wait_for_selector("div.relative.flex.items-start", timeout=15000)
        page.wait_for_timeout(2000)

        # 5. Extract the ETA date directly from the LAST step in Routing Schedule via JS
        raw_eta = page.evaluate("""() => {
            // Find all routing schedule step items
            const steps = Array.from(document.querySelectorAll("div.relative.flex.items-start"));
            if (steps.length === 0) return null;

            // Target the last item (Destination Port / POD)
            const lastStep = steps[steps.length - 1];

            // Target <span class="font-medium"> containing the date inside the last step
            const dateSpan = lastStep.querySelector("span.font-medium");
            return dateSpan ? dateSpan.innerText.trim() : null;
        }""")

        # Fallback regex if JS evaluation returns nothing
        if not raw_eta:
            body_text = page.locator("body").inner_text()
            matches = re.findall(r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})\s*\(\s*Estimated\s*\)", body_text, re.I)
            if matches:
                # Take the last match (Destination ETA)
                raw_eta = matches[-1]

        if raw_eta:
            # Converts '2026/10/27 11:00' to '27-Oct-26'
            eta_result = format_eta_date(raw_eta)

    except Exception as e:
        print(f"Error tracking YML booking {booking_number}: {e}")
        eta_result = "Not Found"

    finally:
        context.close()
        browser.close()

    return eta_result