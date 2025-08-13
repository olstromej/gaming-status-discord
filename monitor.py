import os
import requests
from datetime import datetime
import pytz

# Get Discord webhook URL from environment (for GitHub Actions)
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

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
    # Set timezone (US Eastern)
    tz = pytz.timezone("US/Eastern")
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M %Z")

    services = {
        "Steam API": "https://api.steampowered.com/ISteamWebAPIUtil/GetServerInfo/v1/",
        "Steam Store": "https://store.steampowered.com/",
    }

    status_lines = []

    # Check Steam services
    for name, url in services.items():
        online = check_service(name, url)
        status_lines.append(f"{name}: {'✅ Online' if online else '⚠️ Down'}")

    # PSN: keep clickable link instead of automated check
    status_lines.append("PSN services: 🔗 [Check status](https://status.playstation.com/)")

    # Format Discord message
    message = f"⚠️ Gaming server status as of {now}:\n" + "\n".join(status_lines)
    send_discord_message(message)

if __name__ == "__main__":
    main()
