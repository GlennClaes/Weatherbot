import requests
import json
from datetime import datetime, timedelta
import os

with open("config.json") as f:
    config = json.load(f)

LOCATIONS = config["locations"]
WEBHOOK = os.environ["DISCORD_WEBHOOK"]

def send_discord(msg):
    requests.post(WEBHOOK, json={"content": msg})

def weather_emoji(temp, rain):
    """
    Kies emoji op basis van regen en temp
    """
    if rain > 0.1:
        return "🌧"
    elif temp >= 25:
        return "☀️"
    elif temp >= 15:
        return "⛅"
    elif temp >= 5:
        return "🌤"
    else:
        return "❄️"

def get_weather(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=temperature_2m,precipitation"
        "&timezone=auto"
    )
    return requests.get(url).json()

def process_location(loc):
    data = get_weather(loc["latitude"], loc["longitude"])
    times = data["hourly"]["time"]
    temps = data["hourly"]["temperature_2m"]
    rain = data["hourly"]["precipitation"]

    now = datetime.now()
    next_hours = []

    # pak komende 5 uur
    for t, temp, r in zip(times, temps, rain):
        dt = datetime.fromisoformat(t)
        if now <= dt <= now + timedelta(hours=5):
            next_hours.append((dt.hour, temp, r))

    if not next_hours:
        return f"{loc['name']}: geen data beschikbaar"

    msg = f"📍 {loc['name']} – komende 5 uur:\n"
    for hour, temp, r in next_hours:
        emoji = weather_emoji(temp, r)
        msg += f"{hour}:00 – {emoji} {temp:.1f}°C, neerslag: {r:.1f} mm\n"
    return msg.strip()

# datum bovenaan
today = datetime.now().strftime("%A %d-%m-%Y")
header = f"**Vandaag {today}**\n\n"

# bouw bericht voor alle locaties
messages = [process_location(loc) for loc in LOCATIONS]
full_message = header + "\n\n".join(messages)

send_discord(full_message)
print("Sent weather update")
