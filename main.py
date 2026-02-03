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
    """Haal huidige weerdata op van OpenWeatherMap (huidig)"""
    url = (
        f"http://api.openweathermap.org/data/2.5/weather?"
        f"lat={lat}&lon={lon}&units=metric&appid={API_KEY}"
    )
    response = requests.get(url)
    data = response.json()
    if response.status_code != 200:
        raise ValueError(f"API error: {data}")
    return data

def get_forecast_weather(lat, lon):
    """Haal voorspelling op van OpenWeatherMap (gratis 5-day / 3-hour forecast)"""
    url = (
        f"http://api.openweathermap.org/data/2.5/forecast?"
        f"lat={lat}&lon={lon}&units=metric&appid={API_KEY}"
    )
    response = requests.get(url)
    data = response.json()
    if response.status_code != 200:
        raise ValueError(f"Forecast API error: {data}")
    return data

def process_location(loc):
    """Verwerk locatie en genereer bericht met huidig weer + voorspelling"""
    city = loc["name"]
    lat, lon = loc["latitude"], loc["longitude"]

    # Huidig weer
    current_data = get_current_weather(lat, lon)
    temp_now = current_data["main"]["temp"]
    rain_now = current_data.get("rain", {}).get("1h", 0)
    main_now = current_data["weather"][0]["main"]

    msg = f"📍 **{city}** – Nu: {weather_emoji(temp_now, rain_now, main_now)} {temp_now:.1f}°C, neerslag: {rain_now:.1f} mm\n"

    # Voorspelling komende 6 uur (2 blokken van 3 uur)
    forecast_data = get_forecast_weather(lat, lon)
    for forecast in forecast_data["list"][:2]:  # elk blok is 3 uur
        dt_local = datetime.utcfromtimestamp(forecast["dt"]).replace(tzinfo=pytz.utc).astimezone(BRUSSEL_TZ)
        temp = forecast["main"]["temp"]
        rain = forecast.get("rain", {}).get("3h", 0)
        main = forecast["weather"][0]["main"]
        msg += f"⏱ {dt_local.hour:02d}:00 – {weather_emoji(temp, rain, main)} {temp:.1f}°C, neerslag: {rain:.1f} mm\n"

    # Daghoog en -laag (berekend uit alle forecasts van vandaag)
    today = [f["main"]["temp"] for f in forecast_data["list"]
             if datetime.utcfromtimestamp(f["dt"]).replace(tzinfo=pytz.utc).astimezone(BRUSSEL_TZ).date() == datetime.utcnow().date()]
    if today:
        msg += f"🔆 Vandaag max: {max(today):.1f}°C, min: {min(today):.1f}°C\n"

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
