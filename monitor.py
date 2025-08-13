import os
import time
import json
import sys
import re
from typing import Tuple

import requests

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "").strip()
TIMEOUT = 20  # seconds for HTTP calls
RETRIES = 2   # quick retries within a single run
RETRY_DELAY = 5  # seconds between retries

def send_discord_alert(title: str, message: str):
    if not DISCORD_WEBHOOK:
        print("No DISCORD_WEBHOOK set; printing message instead:")
        print(f"[{title}] {message}")
        return
    payload = {"content": f":rotating_light: **{title}**\n{message}"}
    try:
        r = requests.post(DISCORD_WEBHOOK, json=payload, timeout=TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        print(f"Failed to send Discord message: {e}", file=sys.stderr)

def http_get(url: str) -> Tuple[bool, requests.Response | None, str]:
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "status-check/1.0"})
        return True, resp, ""
    except Exception as e:
        return False, None, str(e)

def check_with_retries(check_fn, name: str) -> Tuple[bool, str]:
    """
    Runs check_fn() up to RETRIES+1 times. check_fn returns (ok: bool, detail: str)
    """
    last_detail = ""
    for attempt in range(RETRIES + 1):
        ok, detail = check_fn()
        last_detail = detail
        if ok:
            return True, detail
        if attempt < RETRIES:
            time.sleep(RETRY_DELAY)
    return False, last_detail

# ---------- STEAM CHECKS ----------

def check_steam_api() -> Tuple[bool, str]:
    url = "https://api.steampowered.com/ISteamWebAPIUtil/GetServerInfo/v1/"
    ok, resp, err = http_get(url)
    if not ok:
        return False, f"HTTP error: {err}"
    if resp.status_code != 200:
        return False, f"Status {resp.status_code}"
    try:
        data = resp.json()
        # A healthy response contains fields like 'servertimestring'
        if "servertimestring" in data or "server_time" in data or "response" in data:
            return True, "Steam Web API OK"
        return False, "Unexpected JSON structure"
    except Exception as e:
        return False, f"JSON parse error: {e}"

def check_steam_store() -> Tuple[bool, str]:
    url = "https://store.steampowered.com/"
    ok, resp, err = http_get(url)
    if not ok:
        return False, f"HTTP error: {err}"
    if resp.status_code != 200:
        return False, f"Status {resp.status_code}"
    body = resp.text.lower()
    # Heuristic: public store page usually includes 'install steam'
    if "install steam" in body:
        return True, "Steam Store reachable"
    return False, "Key text not found"

# ---------- PLAYSTATION CHECK (Browser-rendered) ----------

def check_psn_status() -> Tuple[bool, str]:
    """
    Uses Playwright (Chromium) to load https://status.playstation.com and look for healthy text.
    We intentionally look for multiple phrases to handle minor wording changes.
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return False, f"Playwright not available: {e}"

    healthy_phrases = [
        "all services are up and running",
        "service is running",
        "no issues reported",
    ]
    bad_phrases = [
        "under maintenance",
        "experiencing issues",
        "partially degraded",
        "outage",
        "some services are down",
    ]

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://status.playstation.com/", timeout=60000, wait_until="networkidle")
            body_text = (page.text_content("body") or "").lower()

            # If any bad phrase appears, treat as down.
            if any(bp in body_text for bp in bad_phrases):
                browser.close()
                return False, "PSN page shows issues"

            # If a healthy phrase appears, treat as up.
            if any(hp in body_text for hp in healthy_phrases):
                browser.close()
                return True, "PSN status looks healthy"

            # Fallback: try to detect green 'Running' chips
            chips = page.locator("text=/running/i").count()
            browser.close()
            if chips > 0:
                return True, "PSN components show 'Running'"
            return False, "Could not confirm healthy status"
    except Exception as e:
        return False, f"Playwright error: {e}"

# ---------- MAIN ----------

def main():
    failures = []

    ok, detail = check_with_retries(check_steam_api, "Steam API")
    print(f"Steam API: {detail}")
    if not ok:
        failures.append(f"Steam Web API: {detail}")

    ok, detail = check_with_retries(check_steam_store, "Steam Store")
    print(f"Steam Store: {detail}")
    if not ok:
        failures.append(f"Steam Store: {detail}")

    ok, detail = check_with_retries(check_psn_status, "PSN Status")
    print(f"PSN: {detail}")
    if not ok:
        failures.append(f"PSN: {detail}")

    if failures:
        title = "Gaming outage detected"
        msg = "\n".join(f"- {f}" for f in failures)
        send_discord_alert(title, msg)
    else:
        print("All checks healthy.")

if __name__ == "__main__":
    main()
