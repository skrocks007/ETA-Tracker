# Automated Shipping ETA Tracker

**Automated Vessel Arrival Tracking with Python, Playwright & Google Sheets**

Automated Shipping ETA Tracker is a Python-based web scraping and data pipeline designed to extract Estimated Time of Arrival (ETA) information from supported ocean carrier portals and synchronize tracking results with a centralized Google Sheets dashboard.

Built for logistics and shipping documentation operations, this project helps reduce manual tracking efforts, streamline shipment monitoring, and organize vessel arrival information in one place.

---

## Key Features

* **Multi-Carrier Scraping Engine:** Carrier-specific extractors designed for supported ocean shipping line websites.
* **Persistent Browser Sessions:** Connects to Chrome through the Chrome DevTools Protocol (CDP) when required.
* **Two-Pass Retry Mechanism:** Performs an initial tracking pass followed by targeted retries for unresolved bookings.
* **Google Sheets Integration:** Reads booking records and writes tracking results using `gspread` and the Google Sheets API.
* **Standardized Output:** Normalizes supported ETA date formats into a consistent `DD-MMM-YY` format.
* **Modular Architecture:** Separates carrier extraction logic, browser management, date formatting, and spreadsheet operations.
* **Centralized Shipment Monitoring:** Organizes ETA information to simplify shipment follow-ups and arrival planning.

> **Note:** Extraction results depend on carrier website availability, shipment status, browser sessions, and website structure. Unresolved ETA values should not be treated as confirmed arrival dates.

---

## Supported Carriers

| Carrier Line          | Short Code | Access Strategy                                |
| --------------------- | ---------- | ---------------------------------------------- |
| Yang Ming             | `YML`      | Standard headless browser                      |
| CMA CGM               | `CMA`      | Persistent Chrome session via CDP (`9222`)     |
| Wan Hai Lines         | `WANHAI`   | Persistent Chrome session via CDP (`9222`)     |
| Ocean Network Express | `ONE`      | Standard browser session with popover handling |
| Evergreen             | `EMC`      | Targeted DOM-based extraction                  |
| MSC                   | `MSC`      | Dynamic DOM-based container tracking           |

*Carrier workflows reflect the current project configuration and may require maintenance when carrier websites change.*

---

## Project Architecture

```text
ETA-Tracker/
├── extractors/
│   ├── cma_extractor.py
│   ├── emc_extractor.py
│   ├── msc_extractor.py
│   ├── one_extractor.py
│   ├── wanhai_extractor.py
│   └── yml_extractor.py
├── utils/
│   ├── browser_launcher.py
│   ├── date_formatter.py
│   └── sheets_handler.py
├── .gitignore
├── LICENSE
├── main.py
├── README.md
└── service_account.json   # Local credentials only; never commit
```

### Component Overview

* **`extractors/`** — Contains carrier-specific scripts for extracting shipment ETA information.
* **`browser_launcher.py`** — Handles browser initialization and remote Chrome connections.
* **`date_formatter.py`** — Normalizes supported date formats.
* **`sheets_handler.py`** — Manages Google Sheets interactions.
* **`main.py`** — Orchestrates the tracking pipeline and retry workflow.
* **`README.md`** — Documents installation, configuration, execution, and licensing.

The `service_account.json` file must remain local and must never be committed to the repository.

---

## Getting Started

### Prerequisites

Ensure the following are installed or available:

* **Python 3.10 or later**
* **Google Chrome**
* **Git**
* **Google Cloud service account credentials**
* **Google Sheets API enabled**
* Access to the Google Sheet used for ETA tracking

---

## Installation & Setup

### 1. Clone the Repository

Open Git Bash, PowerShell, or the VS Code terminal and run:

```bash
git clone https://github.com/skrocks007/ETA-Tracker.git
cd ETA-Tracker
```

### 2. Create a Virtual Environment

Create an isolated Python environment for the project:

```bash
python -m venv venv
```

### 3. Activate the Virtual Environment

Choose the command for your terminal.

**Git Bash**

```bash
source venv/Scripts/activate
```

**Windows PowerShell**

```powershell
.\venv\Scripts\Activate.ps1
```

**Windows Command Prompt**

```cmd
venv\Scripts\activate.bat
```

After activation, your terminal should display `(venv)`.

### 4. Install Dependencies

Upgrade `pip` and install the required packages:

```bash
python -m pip install --upgrade pip
pip install playwright gspread google-auth
```

Install the Chromium browser required by Playwright:

```bash
playwright install chromium
```

---

## Configuration & Execution

### 1. Configure Google Sheets Credentials

The tracker uses a Google Cloud service account to access the tracking spreadsheet.

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project or select an existing project.
3. Enable the **Google Sheets API**.
4. Navigate to **IAM & Admin → Service Accounts**.
5. Create a service account and generate a JSON key.
6. Save the downloaded key as `service_account.json`.
7. Place the file in the project root directory.
8. Share your Google Sheet with the service account email address.
9. Grant Editor access if the application needs to update ETA results.

Ensure that the spreadsheet ID, worksheet name, and column configuration match the values expected by the application.

**Security Warning**

* Never upload `service_account.json` to GitHub.
* Confirm that `.gitignore` excludes the credentials file.
* Never publish private keys, passwords, browser cookies, or session tokens.
* If credentials are accidentally exposed, revoke the affected key and generate a replacement.

### 2. Launch Chrome in Remote Debugging Mode

CMA CGM and Wan Hai workflows may require an existing Chrome session.

If required by the configured extractors, launch Chrome with remote debugging enabled before running the pipeline.

**Windows PowerShell**

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --user-data-dir="C:\chrome_dev_profile"
```

**Windows Command Prompt**

```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\chrome_dev_profile"
```

If Chrome is installed in a different location, update the executable path.

**Important Notes**

* Keep Chrome running while the tracker executes.
* Complete any required carrier login manually.
* Use a dedicated Chrome profile for automation.
* Ensure the browser launcher connects to the correct debugging endpoint.
* Restrict debugging access to trusted local connections because it can expose authenticated browser sessions and sensitive information.

This step is required only for carrier workflows configured to use CDP.

### 3. Run the Pipeline

Once installation and configuration are complete, activate the virtual environment and run:

```bash
python main.py
```

The application will execute the configured tracking workflow, process available booking records, retry unresolved results where supported, and update Google Sheets according to the implementation.

Before execution, verify that:

* Booking numbers are populated correctly.
* Google Sheets credentials and permissions are valid.
* Required Chrome sessions are running.
* Carrier websites are accessible.
* Spreadsheet and worksheet configurations are correct.

---

## Troubleshooting

| Issue                           | Recommended Solution                                                             |
| ------------------------------- | -------------------------------------------------------------------------------- |
| `ModuleNotFoundError`           | Activate the virtual environment and install the required dependencies.          |
| Chromium executable not found   | Run `playwright install chromium`.                                               |
| Google Sheets permission denied | Share the spreadsheet with the service account email and verify its permissions. |
| Credentials file not found      | Verify the filename and expected file path.                                      |
| Chrome connection refused       | Start Chrome with remote debugging enabled and check port `9222`.                |
| ETA not found                   | Verify the booking number and check the carrier website manually.                |
| Incorrect ETA format            | Review the extracted value and date normalization logic.                         |
| CAPTCHA or access restriction   | Follow the carrier's authorized verification process.                            |
| Google Sheets update failure    | Check API access, spreadsheet permissions, quotas, and network connectivity.     |

---

## Reliability & Data Validation

ETA information can change during a shipment's journey. To maintain reliable tracking:

* Distinguish successfully extracted ETAs from missing or failed results.
* Do not treat unresolved values as confirmed arrival dates.
* Log booking numbers and carrier details when extraction fails.
* Verify critical arrival information against official carrier sources.
* Update extraction logic when carrier websites change.
* Respect carrier website terms and access restrictions.

---

## License

MIT License

Copyright (c) 2025 Shubham Kumar

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## Author

**Shubham Kumar**

GitHub: [@skrocks007](https://github.com/skrocks007)

---

*Simplifying shipment visibility through automated ETA tracking.*
