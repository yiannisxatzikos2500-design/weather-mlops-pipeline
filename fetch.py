import openmeteo_requests
import sqlite3
from datetime import date, timedelta
import requests_cache
from retry_requests import retry
from groq import Groq  # Fixed: Using Groq for GitHub
import os
import json

DB_PATH = "weather.db"

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
        location TEXT, date TEXT, temp_max REAL, temp_min REAL, 
        precipitation REAL, wind REAL, daylight REAL, uv REAL,
        PRIMARY KEY (location, date)
    )""")
    conn.commit()
    return conn

def generate_poem(weather_rows):
    # This pulls your Secret key from GitHub
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return "Error: GROQ_API_KEY not found in GitHub Secrets."

    client = Groq(api_key=api_key)
    weather_text = ""
    for row in weather_rows:
        weather_text += f"Location: {row['location']} | Temp: {row['temp_max']}°C | Rain: {row['precipitation']}mm\n"

    prompt = f"Write a short bilingual poem in English and Greek comparing the weather in Athens, Rome, and Aalborg: {weather_text}"

    # Using Groq's model instead of Ollama
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def main():
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    conn = init_db()
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": [loc["lat"] for loc in LOCATIONS],
        "longitude": [loc["lon"] for loc in LOCATIONS],
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", 
                  "wind_speed_10m_max", "daylight_duration", "uv_index_max"],
        "timezone": "auto",
        "forecast_days": 1,
    }

    responses = openmeteo.weather_api(url, params=params)
    forecast_date = get_tomorrow()
    weather_rows = []

    for i, res in enumerate(responses):
        daily = res.Daily()
        row = (LOCATIONS[i]["name"], forecast_date, 
               float(daily.Variables(0).ValuesAsNumpy()[0]), float(daily.Variables(1).ValuesAsNumpy()[0]),
               float(daily.Variables(2).ValuesAsNumpy()[0]), float(daily.Variables(3).ValuesAsNumpy()[0]),
               float(daily.Variables(4).ValuesAsNumpy()[0]), float(daily.Variables(5).ValuesAsNumpy()[0]))
        
        conn.execute("INSERT OR REPLACE INTO weather VALUES (?,?,?,?,?,?,?,?)", row)
        weather_rows.append({"location": row[0], "temp_max": row[2], "precipitation": row[4]})

    conn.commit()
    os.makedirs("docs", exist_ok=True)
    with open("docs/weather.json", "w") as f: json.dump(weather_rows, f)
    with open("docs/poem.txt", "w", encoding="utf-8") as f: f.write(generate_poem(weather_rows))
    conn.close()
    print("Success! Pipeline complete.")

if __name__ == "__main__":
    main()
