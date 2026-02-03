import requests
import json
from datetime import datetime
import os
import pytz  # zorgt voor correcte tijdzone

# Config
with open("config.json") as f:
    config = json.load(f)

LOCATIONS = config["locations"]
WEBHOOK = os.environ["DISCORD_WEBHOOK"]
API_KEY = os.environ["OPENWEATHER_API_KEY"]

# Bestand om vorige weersdata op te slaan
STATE_FILE = "last_weather.json"

# Brussel tijdzone
BRUSSEL_TZ = pytz.timezone("Europe/Brussels")

def send_discord(msg):
    """Verstuur bericht naar Discord webhook"""
    requests.post(WEBHOOK, json={"content": msg})

def weather_emoji(temp, rain, main):
    """Kies emoji op basis van temperatuur, regen en weerconditie"""
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

def get_current_weather(lat, lon):
    """Haal huidige weerdata op van OpenWeatherMap"""
    url = (
        f"http://api.openweathermap.org/data/2.5/weather?"
        f"lat={lat}&lon={lon}&units=metric&appid={API_KEY}"
    )
    response = requests.get(url)
    data = response.json()
    if response.status_code != 200:
        raise ValueError(f"API error: {data}")
    return data

def process_location(loc):
    """Verwerk locatie en genereer bericht"""
    city = loc["name"]
    lat, lon = loc["latitude"], loc["longitude"]
    data = get_current_weather(lat, lon)

    # huidige data
    current_temp = data["main"]["temp"]
    current_rain = data.get("rain", {}).get("1h", 0)
    current_main = data["weather"][0]["main"]

    msg = (
        f"📍 **{city}** – Nu: "
        f"{weather_emoji(current_temp, current_rain, current_main)} "
        f"{current_temp:.1f}°C, neerslag: {current_rain:.1f} mm"
    )

    # Retourneer een dict zodat we makkelijk kunnen vergelijken
    return {"message": msg, "temp": current_temp, "rain": current_rain, "main": current_main}

# datum bovenaan
now_brussel = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(BRUSSEL_TZ)
header = f"**Weerupdate {now_brussel.strftime('%A %d-%m-%Y')}**\n\n"

# haal vorige data
if os.path.exists(STATE_FILE):
    with open(STATE_FILE) as f:
        last_data = json.load(f)
else:
    last_data = {}

# nieuwe data ophalen
new_data = {loc["name"]: process_location(loc) for loc in LOCATIONS}

# check of er veranderingen zijn
changes = False
for city in new_data:
    if city not in last_data or new_data[city] != last_data[city]:
        changes = True
        break

# verstuur alleen als er veranderingen zijn
if changes:
    full_message = header + "\n".join([new_data[city]["message"] for city in LOCATIONS])
    send_discord(full_message)
    print("Weerupdate verzonden")
    # sla nieuwe data op
    with open(STATE_FILE, "w") as f:
        json.dump(new_data, f)
else:
    print("Geen veranderingen, geen bericht verzonden")
