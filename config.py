import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")

# Получение API-ключа OpenWeatherMap
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# Сайт с калорийностью продуктов
OPENFOODFACTS_API_URL = "https://world.openfoodfacts.org/api/v0/product/"

# Получение API-ключа и ID Nutritionix
NUTRITIONIX_API_KEY = os.getenv("NUTRITIONIX_API_KEY")
NUTRITIONIX_APP_ID = os.getenv("NUTRITIONIX_APP_ID")