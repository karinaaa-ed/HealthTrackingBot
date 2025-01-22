import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

# Получение API-ключа OpenWeatherMap
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# Получение API-ключа FoodData Central API
FOOD_DATA_CENTRAL_API_KEY = os.getenv("FOOD_DATA_CENTRAL_API_KEY")

# Получение API-ключа и ID Nutritionix
NUTRITIONIX_API_KEY = os.getenv("NUTRITIONIX_API_KEY")
NUTRITIONIX_APP_ID = os.getenv("NUTRITIONIX_APP_ID")
