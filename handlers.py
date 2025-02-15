from aiogram import Router
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import aiohttp
from aiogram.filters.state import StateFilter
import os
from states import Form
from config import OPENWEATHER_API_KEY, FOOD_DATA_CENTRAL_API_KEY, NUTRITIONIX_API_KEY, NUTRITIONIX_APP_ID
from functions import get_temperature, calculate_water_goal, calculate_calorie_goal, create_chart_selection_keyboard
from functions import generate_progress_charts

router = Router()

# Временное хранилище данных
users = {}

# Получение API-ключей
open_weather_api = OPENWEATHER_API_KEY
food_data_api = FOOD_DATA_CENTRAL_API_KEY
nutritionix_api = NUTRITIONIX_API_KEY
nutritionix_id = NUTRITIONIX_APP_ID


# ХЭНДЛЕР /start (Запуск бота)
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Добро пожаловать! Я ваш бот для расчёта нормы воды, калорий и трекинга активности.\n"
        "Введите /help для получения списка команд.")


# ХЭНДЛЕР /help (Справочник команд)
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/set_profile - Настройка профиля пользователя\n"
        "/log_water - Трекинг воды\n"
        "/log_food - Трекинг калорий\n"
        "/log_workout - Трекинг физической активности\n"
        "/check_progress - Проверка текущего прогресса\n"
        "/progress_charts - Графики прогресса по воде и калориям\n"
        "/update_weight - Обновление данных по весу\n"
        "/reset - Удаление профиля (сброс настроек)\n"
    )


# ХЭНДЛЕР /set_profile (Настройка профиля)
@router.message(Command("set_profile"))
async def cmd_set_profile(message: Message, state: FSMContext):
    # Начало настройки профиля
    await message.answer("Введите ваш вес (в кг):")
    await state.set_state(Form.weight)


@router.message(StateFilter(Form.weight))
async def process_weight(message: Message, state: FSMContext):
    # Обработка веса пользователя
    weight = int(message.text)
    await state.update_data(weight=weight)
    await message.answer("Введите ваш рост (в см):")
    await state.set_state(Form.height)


@router.message(StateFilter(Form.height))
async def process_height(message: Message, state: FSMContext):
    # Обработка роста пользователя
    height = int(message.text)
    await state.update_data(height=height)
    await message.answer("Введите ваш возраст:")
    await state.set_state(Form.age)


@router.message(StateFilter(Form.age))
async def process_age(message: Message, state: FSMContext):
    # Обработка возраста пользователя
    age = int(message.text)
    await state.update_data(age=age)
    await message.answer("Сколько минут активности у вас в день?")
    await state.set_state(Form.activity)


@router.message(StateFilter(Form.activity))
async def process_activity(message: Message, state: FSMContext):
    # Обработка уровня активности пользователя
    activity = int(message.text)
    await state.update_data(activity=activity)
    await message.answer("В каком городе вы находитесь?")
    await state.set_state(Form.city)


@router.message(StateFilter(Form.city))
async def process_city(message: Message, state: FSMContext):
    # Обработка города и завершение настройки профиля
    city = message.text
    temperature = await get_temperature(city)
    user_data = await state.get_data()
    user_data["city"] = city

    weight = user_data["weight"]
    height = user_data["height"]
    age = user_data["age"]
    activity = user_data["activity"]

    # Подсчет норм воды и калорий
    water_goal = calculate_water_goal(weight, activity, temperature)
    calorie_goal = calculate_calorie_goal(weight, height, age, activity)

    # Сохранение данных
    user_id = message.from_user.id
    users[user_id] = {
        **user_data,
        "water_goal": water_goal,
        "calorie_goal": calorie_goal,
        "logged_water": 0,
        "logged_calories": 0,
        "burned_calories": 0,
    }

    await message.answer(
        f"Профиль настроен! Вот ваши данные:\n"
        f"Вес: {weight} кг\n"
        f"Рост: {height} см\n"
        f"Возраст: {age} лет\n"
        f"Активность: {activity} минут в день\n"
        f"Город: {city}\n"
        f"Температура: {temperature}°C\n"
        f"Цель по воде: {water_goal} мл\n"
        f"Цель по калориям: {calorie_goal} ккал"
    )
    await state.clear()


# ХЭНДЛЕР /log_water (Логирование воды)
@router.message(Command("log_water"))
async def cmd_log_water(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Сначала настройте профиль с помощью команды /set_profile.")
        return

    # Извлечение количества воды из команды
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Введите количество воды в миллилитрах. Пример: /log_water 250")
        return

    water_amount = int(parts[1])
    users[user_id]["logged_water"] += water_amount

    remaining_water = max(0, users[user_id]["water_goal"] - users[user_id]["logged_water"])

    await message.answer(
        f"Записано: {water_amount} мл воды. "
        f"Осталось до нормы: {remaining_water} мл."
    )


# ХЭНДЛЕР /log_food (Логирование еды)
@router.message(Command("log_food"))
async def cmd_log_food(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Сначала настройте профиль с помощью команды /set_profile.")
        return

    # Извлечение названия продукта из команды
    user_input = " ".join(message.text.split()[1:])
    if not user_input:  # Если название продукта не указано
        await message.answer("Введите название продукта на английском языке. Пример: /log_food banana")
        return

    # Поиск продукта через FoodData Central API
    async with aiohttp.ClientSession() as session:
        async with session.get(
                f"https://api.nal.usda.gov/fdc/v1/foods/search",
                params={"query": user_input, "api_key": FOOD_DATA_CENTRAL_API_KEY}
        ) as food_data_response:
            if food_data_response.status != 200:
                await message.answer("Ошибка при поиске данных о продукте. Попробуйте позже.")
                return

            food_data = await food_data_response.json()

    # Проверяем, есть ли продукты в ответе
    if not food_data.get("foods"):
        await message.answer(f"Продукт '{user_input}' не найден. Убедитесь, что вы ввели название на английском языке.")
        return

    # Получаем данные о калориях
    food_item = food_data["foods"][0]
    food_name = food_item.get("description", user_input).capitalize()
    calories_per_100g = next(
        (nutrient["value"] for nutrient in food_item.get("foodNutrients", []) if
         nutrient.get("nutrientName") == "Energy"), 0
    )

    await state.update_data(calories_per_100g=calories_per_100g, food_name=food_name)

    await message.answer(
        f"{food_name} — {calories_per_100g} ккал на 100 г.\n"
        "Сколько грамм вы съели? Введите число."
    )
    await state.set_state(Form.food_weight)


# Обработка веса продукта и расчет калорий
@router.message(StateFilter(Form.food_weight))
async def process_food_weight(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Сначала настройте профиль с помощью команды /set_profile.")
        return

    try:
        food_weight = float(message.text)
        user_data = await state.get_data()

        food_name = user_data.get("food_name", "неизвестный продукт")
        calories_per_100g = user_data.get("calories_per_100g", 0)

        total_calories = (calories_per_100g * food_weight) / 100
        users[user_id]["logged_calories"] += total_calories

        await message.answer(
            f"Записано: {food_name} — {total_calories:.1f} ккал.\n"
            f"Общее потребление калорий: {users[user_id]['logged_calories']:.1f} ккал."
        )
        await state.clear()
    except ValueError:
        await message.answer("Введите корректное число грамм.")


# Отслеживание сожженых калорий на тренировке
NUTRITIONIX_API_URL = "https://trackapi.nutritionix.com/v2/natural/exercise"
NUTRITIONIX_HEADERS = {
    "x-app-id": nutritionix_id,
    "x-app-key": nutritionix_api,
    "Content-Type": "application/json"
}

# ХЭНДЛЕР /log_workout (Логирование тренировок)
@router.message(Command("log_workout"))
async def cmd_log_workout(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Сначала настройте профиль с помощью команды /set_profile.")
        return

    # Извлечение типа тренировки и времени из команды
    parts = message.text.split(maxsplit=2)
    if len(parts) != 3:
        await message.answer("Введите тип тренировки и время в минутах. Пример: /log_workout бег 30")
        return

    workout_type = parts[1].lower()
    try:
        duration = int(parts[2])
    except ValueError:
        await message.answer("Введите время тренировки в минутах числом. Пример: /log_workout бег 30")
        return

    # Формирование запроса к API Nutritionix
    request_data = {
        "query": f"{duration} minutes of {workout_type}",
        "gender": "male",  # По умолчанию, можно добавить в профиль
        "weight_kg": users[user_id]["weight"],
        "height_cm": users[user_id]["height"],
        "age": users[user_id]["age"]
    }

    # Запрос к Nutritionix API
    async with aiohttp.ClientSession() as session:
        async with session.post(NUTRITIONIX_API_URL, headers=NUTRITIONIX_HEADERS, json=request_data) as response:
            if response.status == 200:
                data = await response.json()
                if "exercises" in data and len(data["exercises"]) > 0:
                    exercise = data["exercises"][0]
                    calories_burned = exercise["nf_calories"]

                    # Дополнительный расчет воды
                    extra_water = (duration // 30) * 200  # 200 мл за каждые 30 минут

                    # Обновление данных пользователя
                    users[user_id]["burned_calories"] += calories_burned
                    users[user_id]["logged_water"] += extra_water

                    remaining_water = max(0, users[user_id]["water_goal"] - users[user_id]["logged_water"])

                    # Ответ пользователю
                    await message.answer(
                        f"{workout_type.capitalize()} {duration} минут — {calories_burned:.1f} ккал.\n"
                        f"Дополнительно: выпейте {extra_water} мл воды.\n"
                        f"Осталось до нормы воды: {remaining_water} мл."
                    )
                else:
                    await message.answer(f"Не удалось найти информацию о тренировке: {workout_type}.")
            else:
                await message.answer("Ошибка при запросе данных о тренировке.")


# ХЭНДЛЕР /check_progress (Прогресс по воде и калориям)
@router.message(Command("check_progress"))
async def cmd_check_progress(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.answer("Сначала настройте профиль с помощью команды /set_profile.")
        return

    # Извлечение данных пользователя
    user_data = users[user_id]
    water_consumed = user_data["logged_water"]
    water_goal = user_data["water_goal"]
    water_remaining = max(0, water_goal - water_consumed)

    calories_consumed = user_data["logged_calories"]
    calorie_goal = user_data["calorie_goal"]
    calories_burned = user_data["burned_calories"]
    calorie_balance = calories_consumed - calories_burned

    # Формирование сообщения
    progress_message = (
        "<b>Прогресс:</b>\n\n"
        "<b>Вода:</b>\n"
        f"- Выпито: {water_consumed} мл из {water_goal} мл.\n"
        f"- Осталось: {water_remaining} мл.\n\n"
        "<b>Калории:</b>\n"
        f"- Потреблено: {calories_consumed} ккал из {calorie_goal} ккал.\n"
        f"- Сожжено: {calories_burned} ккал.\n"
        f"- Баланс: {calorie_balance} ккал."
    )

    # Отправка сообщения
    await message.answer(progress_message, parse_mode="HTML")


# ХЭНДЛЕР /progress_charts (Графики прогресса по воде и калориям)
@router.message(Command("progress_charts"))
async def cmd_progress_charts(message: Message):
    keyboard = create_chart_selection_keyboard()
    await message.answer(
        "Выберите, какой график вы хотите посмотреть:",
        reply_markup=keyboard
    )

# Обработка нажатий на кнопки
@router.callback_query(lambda c: c.data in ["chart_water", "chart_calories"])
async def handle_chart_selection(callback: CallbackQuery):
    user_id = callback.from_user.id

    # Проверяем наличие данных пользователя
    if user_id not in users:
        await callback.message.answer("Сначала настройте профиль с помощью команды /set_profile.")
        return

    user_data = users[user_id]

    # Генерация и отправка соответствующего графика
    if callback.data == "chart_water":
        water_chart, _ = generate_progress_charts(user_data, user_id)
        await callback.message.answer_photo(FSInputFile(water_chart), caption="Прогресс по воде")
        os.remove(water_chart)

    elif callback.data == "chart_calories":
        _, calorie_chart = generate_progress_charts(user_data, user_id)
        await callback.message.answer_photo(FSInputFile(calorie_chart), caption="Прогресс по калориям")
        os.remove(calorie_chart)

        # Уведомление об обработке выбора
    await callback.answer("График отправлен!")


# ХЭНДЛЕР /update_weight (Обновление веса)
@router.message(Command("update_weight"))
async def update_weight(message: Message):
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Укажите ваш вес в формате: /update_weight <вес в кг>.")
        return

    user_id = message.from_user.id
    new_weight = float(message.text.split()[1])

    if user_id in users:
        users[user_id]["weight"] = new_weight
        await message.answer(f"Ваш вес обновлён: {new_weight} кг.")
    else:
        await message.answer("Сначала настройте профиль с помощью команды /set_profile.")


# ХЭНДЛЕР /reset (Сброс профиля)
@router.message(Command("reset"))
async def reset_profile(message: Message):
    user_id = message.from_user.id
    if user_id in users:
        del users[user_id]
        await message.answer("Ваш профиль был сброшен. Вы можете настроить его заново через /set_profile.")
    else:
        await message.answer("У вас пока нет настроенного профиля.")
