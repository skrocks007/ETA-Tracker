# utils/browser_launcher.py

import os
import socket
import subprocess
import time

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = r"C:\chrome_dev_session"
DEBUG_PORT = 9222

CMA_URL = "https://www.cma-cgm.com/ebusiness/tracking"
WANHAI_URL = "https://www.wanhai.com/views/Main.xhtml"


def is_port_open(port=DEBUG_PORT):
    """Checks if Chrome remote debugging port 9222 is active."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", port)) == 0


def ensure_chrome_debugging():
    """Launches Chrome in debug mode with tracking sites and waits for human captcha clearance."""
    if not is_port_open(DEBUG_PORT):
        print(f"[!] Launching Chrome on debug port {DEBUG_PORT}...")
        cmd = [
            CHROME_PATH,
            f"--remote-debugging-port={DEBUG_PORT}",
            f"--user-data-dir={USER_DATA_DIR}",
            CMA_URL,
            WANHAI_URL,
        ]
        subprocess.Popen(cmd, creationflags=subprocess.DETACHED_PROCESS)

        for _ in range(10):
            time.sleep(1)
            if is_port_open(DEBUG_PORT):
                break

    print("\n" + "=" * 60)
    print(" MANUAL CHECK REQUIRED IN CHROME:")
    print(" 1. Resolve any Captcha / Cloudflare on Wan Hai or CMA CGM tabs.")
    print(" 2. Ensure both sites show clean tracking search bars.")
    print("=" * 60)
    input("\n Press [ENTER] in this terminal once captchas are solved to start tracking...\n")
    print("[+] Resuming automation script...\n")