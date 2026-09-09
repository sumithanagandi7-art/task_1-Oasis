"""
Weather Service — OpenWeatherMap Integration
=============================================
Fetches current weather data using the OpenWeatherMap free-tier API.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("OPENWEATHERMAP_API_KEY", "")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "London")


def get_weather(city: str = None) -> dict:
    """
    Fetch current weather for a city.
    
    Args:
        city: City name. Falls back to DEFAULT_CITY from .env.
        
    Returns:
        dict with keys:
            - success (bool)
            - data (dict): Weather data if successful
            - error (str): Error message if failed
    """
    city = city or DEFAULT_CITY

    if not API_KEY or API_KEY == "your_api_key_here":
        return {
            "success": False,
            "error": (
                "Weather API key not configured. "
                "Please add your OpenWeatherMap API key to the .env file. "
                "Get a free key at https://openweathermap.org/api"
            ),
            "data": {}
        }

    try:
        params = {
            "q": city,
            "appid": API_KEY,
            "units": "metric"
        }
        response = requests.get(BASE_URL, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            weather_info = {
                "city": data.get("name", city),
                "country": data.get("sys", {}).get("country", ""),
                "temp": round(data["main"]["temp"], 1),
                "feels_like": round(data["main"]["feels_like"], 1),
                "temp_min": round(data["main"]["temp_min"], 1),
                "temp_max": round(data["main"]["temp_max"], 1),
                "humidity": data["main"]["humidity"],
                "pressure": data["main"]["pressure"],
                "description": data["weather"][0]["description"],
                "icon": data["weather"][0]["icon"],
                "wind_speed": data["wind"]["speed"],
                "wind_deg": data["wind"].get("deg", 0),
                "clouds": data["clouds"]["all"],
                "visibility": data.get("visibility", 0),
            }
            return {"success": True, "data": weather_info, "error": ""}

        elif response.status_code == 404:
            return {
                "success": False,
                "error": f"City '{city}' not found. Please check the city name.",
                "data": {}
            }
        elif response.status_code == 401:
            return {
                "success": False,
                "error": "Invalid API key. Please check your OpenWeatherMap API key.",
                "data": {}
            }
        else:
            return {
                "success": False,
                "error": f"Weather service returned status {response.status_code}.",
                "data": {}
            }

    except requests.Timeout:
        return {
            "success": False,
            "error": "Weather service timed out. Please try again.",
            "data": {}
        }
    except requests.ConnectionError:
        return {
            "success": False,
            "error": "No internet connection. Cannot fetch weather data.",
            "data": {}
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Weather error: {str(e)}",
            "data": {}
        }
