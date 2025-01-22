from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp
import matplotlib.pyplot as plt
from config import OPENWEATHER_API_KEY


# Получение API-ключей
open_weather_api = OPENWEATHER_API_KEY


# Получение температуры в городе через OpenWeatherMap
async def get_temperature(city: str) -> float:
    url = f"http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": open_weather_api,
        "units": "metric"
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data["main"]["temp"]
            else:
                return None


# Расчет нормы воды
def calculate_water_goal(weight, activity_minutes, temperature):
    base_water = weight * 30
    activity_bonus = (activity_minutes // 30) * 500
    weather_bonus = 500 if temperature > 25 else 0
    return base_water + activity_bonus + weather_bonus


# Расчет нормы калорий
def calculate_calorie_goal(weight, height, age, activity_minutes):
    base_calories = 10 * weight + 6.25 * height - 5 * age
    activity_bonus = min(400, max(200, activity_minutes * 5))
    return base_calories + activity_bonus


# Создание кнопок для выбора графиков
def create_chart_selection_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Прогресс по воде", callback_data="chart_water")],
        [InlineKeyboardButton(text="Прогресс по калориям", callback_data="chart_calories")]
    ])
    return keyboard


# Построение графиков прогресса
def generate_progress_charts(user_data, user_id):
    # Получаем данные
    water_goal = user_data.get("water_goal", 0)
    logged_water = user_data.get("logged_water", 0)

    calorie_goal = user_data.get("calorie_goal", 0)
    logged_calories = user_data.get("logged_calories", 0)
    burned_calories = user_data.get("burned_calories", 0)

    # Считаем остаток
    remaining_water = max(0, water_goal - logged_water)
    remaining_calories = max(0, calorie_goal - (logged_calories - burned_calories))

    # Построение графика воды
    plt.figure(figsize=(8, 4))
    plt.bar(["Выпито", "Осталось"], [logged_water, remaining_water], color=["#1f77b4", "#ff7f0e"])
    plt.title("Прогресс по воде (мл)")
    plt.ylabel("Миллитры")
    plt.savefig(f"water_progress_{user_id}.png")
    plt.close()

    # Построение графика калорий
    plt.figure(figsize=(8, 4))
    plt.bar(["Потреблено", "Сожжено", "Осталось"], [logged_calories, burned_calories, remaining_calories],
            color=["#2ca02c", "#d62728", "#9467bd"])
    plt.title("Прогресс по калориям (ккал)")
    plt.ylabel("Калории")
    plt.savefig(f"calorie_progress_{user_id}.png")
    plt.close()

    return f"water_progress_{user_id}.png", f"calorie_progress_{user_id}.png"
