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

def get_onecall_weather(lat, lon):
    """Haal huidige weerdata + voorspelling op van OpenWeatherMap"""
    url = (
        f"https://api.openweathermap.org/data/2.5/onecall?"
        f"lat={lat}&lon={lon}&units=metric&exclude=minutely,alerts&appid={API_KEY}"
    )
    response = requests.get(url)
    data = response.json()
    if response.status_code != 200:
        raise ValueError(f"OneCall API error: {data}")
    return data

def process_location(loc):
    """Verwerk locatie en genereer bericht"""
    city = loc["name"]
    lat, lon = loc["latitude"], loc["longitude"]
    data = get_onecall_weather(lat, lon)

    # huidige weer
    current = data["current"]
    temp_now = current["temp"]
    rain_now = current.get("rain", {}).get("1h", 0)
    main_now = current["weather"][0]["main"]

    msg = f"📍 **{city}** – Nu: {weather_emoji(temp_now, rain_now, main_now)} {temp_now:.1f}°C, neerslag: {rain_now:.1f} mm\n"

    # voorspelling komende 6 uur
    for hour_data in data["hourly"][1:7]:
        dt_local = datetime.utcfromtimestamp(hour_data["dt"]).replace(tzinfo=pytz.utc).astimezone(BRUSSEL_TZ)
        temp = hour_data["temp"]
        rain = hour_data.get("rain", {}).get("1h", 0)
        main = hour_data["weather"][0]["main"]
        msg += f"⏱ {dt_local.hour:02d}:00 – {weather_emoji(temp, rain, main)} {temp:.1f}°C, neerslag: {rain:.1f} mm\n"

    # daghoog en -laag
    today = data["daily"][0]
    msg += f"🔆 Vandaag max: {today['temp']['max']:.1f}°C, min: {today['temp']['min']:.1f}°C\n"

    # Retourneer dict om te vergelijken met vorige data
    return {"message": msg, "temp": temp_now, "rain": rain_now, "main": main_now}

# datum bovenaan
now_brussel = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(BRUSSEL_TZ)
header = f"**Weerupdate {now_brussel.strftime('%A %d-%m-%Y %H:%M')}**\n\n"

# vorige data ophalen
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
    full_message = header + "\n".join([new_data[loc["name"]]["message"] for loc in LOCATIONS])
    send_discord(full_message)
    print("Weerupdate verzonden")
    # sla nieuwe data op
    with open(STATE_FILE, "w") as f:
        json.dump(new_data, f)
else:
    print("Geen veranderingen, geen bericht verzonden")
