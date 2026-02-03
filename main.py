import requests
import json
from datetime import datetime, timedelta
import os

# Load config
with open("config.json") as f:
    config = json.load(f)

LOCATIONS = config["locations"]
WEBHOOK = os.environ["DISCORD_WEBHOOK"]  # webhook als GitHub secret

def send_discord(msg):
    """
    Verstuur bericht naar Discord via webhook
    """
    requests.post(WEBHOOK, json={"content": msg})

def get_weather(lat, lon):
    """
    Haal weerdata op van Open-Meteo
    """
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=temperature_2m,precipitation"
        "&timezone=auto"
    )
    return requests.get(url).json()

def process_location(loc):
    """
    Bereken morgen gemiddelde temperatuur en totale neerslag
    """
    data = get_weather(loc["latitude"], loc["longitude"])
    times = data["hourly"]["time"]
    temps = data["hourly"]["temperature_2m"]
    rain = data["hourly"]["precipitation"]

    tomorrow = (datetime.now() + timedelta(days=1)).date()

    tomorrow_hours = [
        (datetime.fromisoformat(t), temp, r)
        for t, temp, r in zip(times, temps, rain)
        if datetime.fromisoformat(t).date() == tomorrow
    ]

    if not tomorrow_hours:
        return f"🌤 {loc['name']}: Geen data voor morgen beschikbaar"

    avg_temp = sum(x[1] for x in tomorrow_hours) / len(tomorrow_hours)
    total_rain = sum(x[2] for x in tomorrow_hours)

    return (
        f"🌤 {loc['name']}:\n"
        f"Gem temp: {avg_temp:.1f}°C\n"
        f"Totale neerslag: {total_rain:.1f} mm"
    )

# Maak bericht voor alle locaties
messages = [process_location(loc) for loc in LOCATIONS]
full_message = "\n\n".join(messages)

# Verstuur naar Discord
send_discord(full_message)
print("Sent weather update for all locations")
