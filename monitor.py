import os
import requests
from datetime import datetime

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def send_discord_message(message: str):
    """Send a message to Discord via webhook."""
    if not DISCORD_WEBHOOK_URL:
        print("No Discord webhook URL set.")
        return
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
        response.raise_for_status()
        print("Discord message sent successfully.")
    except Exception as e:
        print(f"Failed to send Discord message: {e}")

def check_service(name: str, url: str) -> bool:
    """Check if a service URL is reachable."""
    try:
        r = requests.get(url, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"{name} check failed: {e}")
        return False

def main():
    services = {
        "Steam API": "https://api.steampowered.com/ISteamWebAPIUtil/GetServerInfo/v1/",
        "Steam Store": "https://store.steampowered.com/",
        "PSN": "https://status.playstation.com/data/status/es-MX.json"
    }

    issues = []

    for name, url in services.items():
        if not check_service(name, url):
            issues.append(f"{name} is down!")

    now = datetime.now().strftime("%Y-%m-%d %H:%M %Z")

    # Always post daily status
    if not issues:
        message = f"✅ All servers healthy as of {now}."
        send_discord_message(message)
    else:
        # Post alert if any server is down
        message = f"⚠️ Gaming server issues detected as of {now}:\n" + "\n".join(issues)
        send_discord_message(message)

if __name__ == "__main__":
    main()
