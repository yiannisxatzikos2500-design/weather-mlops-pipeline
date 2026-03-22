import openmeteo_requests
import sqlite3
from datetime import date, timedelta
import requests_cache
from retry_requests import retry
import ollama  # Switched from Groq to Ollama
import os
import json

DB_PATH = "weather.db"

# FIXED: Added missing closing bracket ] for the list
LOCATIONS = [
    {"name": "Athens", "lat": 37.9838, "lon": 23.7275},
    {"name": "Rome", "lat": 41.9028, "lon": 12.4964},
    {"name": "Aalborg", "lat": 57.048, "lon": 9.9187},
]

def get_tomorrow():
    return (date.today() + timedelta(days=1)).isoformat()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weather (
        location TEXT,
        date TEXT,
        temp_max REAL,
        temp_min REAL,
        precipitation REAL,
        wind REAL,
        daylight REAL,
        uv REAL,
        PRIMARY KEY (location, date)
    )
    """)
    conn.commit()
    return conn

def generate_poem(weather_rows):
    # Prepare the data string for the local model
    weather_text = ""
    for row in weather_rows:
        weather_text += (
            f"Location: {row['location']} | Max Temp: {row['temp_max']}°C | "
            f"Rain: {row['precipitation']}mm | Wind: {row['wind']}km/h | UV: {row['uv']}\n"
        )

    # Updated Prompt for your new cities
    prompt = f"""
Write a short creative poem in two languages: English
Compare the weather in Athens, Rome, and Aalborg.
Describe differences in temperature, rain, wind, and UV.
Suggest the nicest city for tomorrow.


Data:
{weather_text}
"""

    # Using Ollama with gemma2:2b
    response = ollama.chat(model='gemma2:2b', messages=[
        {'role': 'system', 'content': 'You are a poetic meteorologist.'},
        {'role': 'user', 'content': prompt},
    ])

    return response['message']['content']

def main():
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    conn = init_db()

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": [loc["lat"] for loc in LOCATIONS],
        "longitude": [loc["lon"] for loc in LOCATIONS],
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "wind_speed_10m_max",
            "daylight_duration",
            "uv_index_max"
        ],
        "timezone": "auto", # 'auto' is safer than hardcoding Europe/Berlin
        "forecast_days": 1,
    }

    responses = openmeteo.weather_api(url, params=params)
    forecast_date = get_tomorrow()
    weather_rows = []

    for i, response in enumerate(responses):
        location = LOCATIONS[i]["name"]
        daily = response.Daily()

        # Extract values
        temp_max = float(daily.Variables(0).ValuesAsNumpy()[0])
        temp_min = float(daily.Variables(1).ValuesAsNumpy()[0])
        precipitation = float(daily.Variables(2).ValuesAsNumpy()[0])
        wind = float(daily.Variables(3).ValuesAsNumpy()[0])
        daylight = float(daily.Variables(4).ValuesAsNumpy()[0])
        uv = float(daily.Variables(5).ValuesAsNumpy()[0])

        conn.execute("""
        INSERT OR REPLACE INTO weather VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (location, forecast_date, temp_max, temp_min, precipitation, wind, daylight, uv))

        weather_rows.append({
            "location": location, "date": forecast_date, "temp_max": temp_max,
            "temp_min": temp_min, "precipitation": precipitation,
            "wind": wind, "daylight": daylight, "uv": uv
        })

    conn.commit()
    os.makedirs("docs", exist_ok=True)

    with open("docs/weather.json", "w", encoding="utf-8") as f:
        json.dump(weather_rows, f, indent=2, ensure_ascii=False)

    poem = generate_poem(weather_rows)

    with open("docs/poem.txt", "w", encoding="utf-8") as f:
        f.write(poem)

    conn.close()
    print("Success! Data stored and Gemma2 wrote your poem in docs/poem.txt")

if __name__ == "__main__":
    main()