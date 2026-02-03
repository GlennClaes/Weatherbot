import requests
import json
from datetime import datetime, timedelta
import os

with open("config.json") as f:
    config = json.load(f)

LOCATIONS = config["locations"]
WEBHOOK = os.environ["DISCORD_WEBHOOK"]
API_KEY = os.environ["OPENWEATHER_API_KEY"]  # jouw API key in GitHub secrets

def send_discord(msg):
    requests.post(WEBHOOK, json={"content": msg})

def weather_emoji(temp, rain, main):
    """
    Emoji kiezen op basis van regen/temp/conditie
    """
    if "rain" in main.lower() or rain > 0.1:
        return "🌧"
    elif "snow" in main.lower():
        return "❄️"
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
        f"https://api.openweathermap.org/data/2.5/onecall?"
        f"lat={lat}&lon={lon}&units=metric&appid={API_KEY}"
    )
    return requests.get(url).json()

def process_location(loc):
    data = get_weather(loc["latitude"], loc["longitude"])

    current = data["current"]
    current_temp = current["temp"]
    current_rain = current.get("rain", {}).get("1h", 0)
    current_main = current["weather"][0]["main"]

    msg = f"📍 {loc['name']} – nu: {weather_emoji(current_temp, current_rain, current_main)} {current_temp:.1f}°C, neerslag: {current_rain:.1f} mm\n"

    # forecast komende 5 uur
    now = datetime.utcnow()
    forecast_hours = []
    for hour_data in data["hourly"]:
        dt = datetime.utcfromtimestamp(hour_data["dt"])
        if now < dt <= now + timedelta(hours=5):
            forecast_hours.append(hour_data)
        if len(forecast_hours) >= 5:
            break

    msg += "Komende 5 uur:\n"
    for hour_data in forecast_hours:
        dt = datetime.utcfromtimestamp(hour_data["dt"])
        temp = hour_data["temp"]
        rain = hour_data.get("rain", {}).get("1h", 0)
        main = hour_data["weather"][0]["main"]
        msg += f"{dt.hour:02d}:00 – {weather_emoji(temp, rain, main)} {temp:.1f}°C, neerslag: {rain:.1f} mm\n"

    return msg.strip()

# datum bovenaan
today = datetime.now().strftime("%A %d-%m-%Y")
header = f"**Vandaag {today}**\n\n"

# bouw bericht voor alle locaties
messages = [process_location(loc) for loc in LOCATIONS]
full_message = header + "\n\n".join(messages)

send_discord(full_message)
print("Sent weather update")
