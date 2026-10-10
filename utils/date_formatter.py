import re
from datetime import datetime

def format_eta_date(date_str: str) -> str:
    """
    Standardizes any date string into the format: '7-Dec -26' or '20-Oct -26'
    Pattern: Day (no leading zero) - Month (3-letter) [space] - Year (2-digit)
    """
    if not date_str or str(date_str).strip().upper() in ["NOT FOUND", "FAILED TO EXTRACT", "N/A", "NONE"]:
        return "Not Found"

    cleaned = str(date_str).strip()

    # Clean up common delimiters & extra whitespace
    cleaned_input = re.sub(r"\s+", " ", cleaned.replace("/", "-").replace(".", "-"))

    # Supported input date formats across carriers
    input_formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y",
        "%d-%b-%Y %H:%M",
        "%d-%b-%Y",
        "%d-%b-%y",
        "%d %b %Y",
        "%Y-%b-%d",
    ]

    parsed_dt = None

    # First attempt: Match against standard datetime strptime formats
    for fmt in input_formats:
        try:
            parsed_dt = datetime.strptime(cleaned_input.split()[0] if " " in cleaned_input and ":" not in cleaned_input else cleaned_input, fmt)
            break
        except ValueError:
            pass

    # Second attempt: Regex extraction for messy strings like "Wednesday, 08-OCT-2026" or "08/10/2026"
    if not parsed_dt:
        # Regex for DD-MMM-YYYY or DD-MMM-YY
        match_alpha = re.search(r"(\d{1,2})[-_\s]*([A-Za-z]{3})[-_\s]*(\d{2,4})", cleaned)
        if match_alpha:
            day, month, year = match_alpha.groups()
            year = f"20{year}" if len(year) == 2 else year
            try:
                parsed_dt = datetime.strptime(f"{day}-{month}-{year}", "%d-%b-%Y")
            except ValueError:
                pass

        # Regex for DD-MM-YYYY or YYYY-MM-DD
        if not parsed_dt:
            match_num = re.search(r"(\d{4})[-_\s](\d{1,2})[-_\s](\d{1,2})", cleaned)
            if match_num:
                year, month, day = match_num.groups()
                try:
                    parsed_dt = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d")
                except ValueError:
                    pass

    if parsed_dt:
        day = parsed_dt.strftime("%d").lstrip("0")  # Removes leading zero (e.g., '7' instead of '07')
        month = parsed_dt.strftime("%b")            # 3-letter month (e.g., 'Dec')
        year = parsed_dt.strftime("%y")             # 2-digit year (e.g., '26')
        
        # Returns exact format requested: '7-Dec -26'
        return f"{day}-{month} -{year}"

    return date_str