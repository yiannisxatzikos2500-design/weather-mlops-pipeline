# 🌤️ Weather MLOps Pipeline

An automated data pipeline that fetches weather forecasts, stores them in a local database, and generates creative bilingual poetry using LLMs.

## 🚀 How it Works
1. **Data Collection**: The script `fetch.py` calls the **Open-Meteo API** to get weather data for Athens, Rome, and Aalborg.
2. **Storage**: Data is saved into a local **SQLite** database (`weather.db`).
3. **LLM Generation**: The script sends the weather data to **Groq (Llama 3)** to generate a bilingual poem (English & Greek).
4. **Automation**: A **GitHub Action** runs this pipeline every day at 20:00 Danish time.
5. **Deployment**: Results are automatically published to **GitHub Pages**.

## 🛠️ Setup
- **Groq API Key**: Must be added to GitHub Secrets as `GROQ_API_KEY`.
- **Python Version**: 3.9+
- **Libraries**: See `requirements.txt`.

## 📂 Project Structure
- `fetch.py`: Main logic for API calls and database management.
- `index.html`: The website interface for GitHub Pages.
- `.github/workflows/main.yml`: The automation schedule.
- `docs/`: Contains the generated `poem.txt` and `weather.json`.
