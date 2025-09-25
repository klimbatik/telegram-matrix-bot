import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# === Загрузка переменных окружения ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # Должен начинаться с "@", например: "@my_channel"
YOUR_TELEGRAM_ID_STR = os.getenv("YOUR_TELEGRAM_ID")

# Проверка наличия всех переменных
if not all([BOT_TOKEN, CHANNEL_USERNAME, YOUR_TELEGRAM_ID_STR]):
    raise ValueError("❌ Отсутствуют переменные окружения: BOT_TOKEN, CHANNEL_USERNAME или YOUR_TELEGRAM_ID")

# Преобразуем ID в число
try:
    YOUR_TELEGRAM_ID = int(YOUR_TELEGRAM_ID_STR)
except ValueError:
    raise ValueError("❌ YOUR_TELEGRAM_ID должен быть целым числом (например, 1030370280)")

# === Инициализация бота ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Список пользователей, ожидающих ввод даты рождения
awaiting_birth_date = set()

# === /start — основной сценарий ===
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user = message.from_user
    user_id = user.id

    try:
        # Убираем "@" из CHANNEL_USERNAME для get_chat_member
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME[1:], user_id)
        if chat_member.status in ['member', 'administrator', 'creator']:
            awaiting_birth_date.add(user_id)
            await message.answer(
                "✨ Отлично! Чтобы сделать расчёт по матрице судьбы, напишите вашу дату рождения в формате:\n\n"
                "<code>дд.мм.гггг</code>\n\n"
                "Например: <code>15.08.1990</code>",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "🙏 Пожалуйста, подпишитесь на канал, чтобы получить бесплатный расчёт по матрице судьбы!",
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton(
                        "Подписаться на канал",
                        url=f"https://t.me/{CHANNEL_USERNAME[1:]}"
                    )
                )
            )
    except Exception as e:
        print("Ошибка проверки подписки:", e)
        await message.answer("Произошла ошибка. Попробуйте позже.")

# === Обработка текста (дата рождения) ===
@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_text(message: types.Message):
    user = message.from_user
    user_id = user.id

    if user_id in awaiting_birth_date:
        birth_date = message.text.strip()
        # Простая проверка формата дд.мм.гггг
        parts = birth_date.split('.')
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            day, month, year = parts
            if len(day) == 2 and len(month) == 2 and len(year) == 4:
                username = f"@{user.username}" if user.username else f"ID{user_id}"
                await bot.send_message(
                    YOUR_TELEGRAM_ID,
                    f"🆕 Новый лид!\n\n"
                    f"Пользователь: {username}\n"
                    f"Дата рождения: <code>{birth_date}</code>\n\n"
                    f"Теперь вы можете написать ему вручную.",
                    parse_mode="HTML"
                )
                awaiting_birth_date.discard(user_id)
                await message.answer("✅ Спасибо! Ваша заявка принята. Скоро я свяжусь с вами для расчёта.")
                return

        await message.answer("❌ Пожалуйста, введите дату в формате <code>дд.мм.гггг</code>", parse_mode="HTML")
    else:
        await start_handler(message)

# === /publish — отправка сообщения с кнопкой в канал (только для вас) ===
@dp.message_handler(commands=['publish'])
async def publish_offer(message: types.Message):
    if message.from_user.id != YOUR_TELEGRAM_ID:
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton(
            "Заказать расчёт",
            url="https://t.me/LenaMusBot?start=matrix"
        )
    )
    await bot.send_message(
        CHANNEL_USERNAME,
        "🔮 Бесплатный расчёт по матрице судьбы!\n\n"
        "Узнайте своё предназначение, кармические задачи и сильные стороны.\n"
        "Нажмите кнопку ниже, чтобы получить расчёт.",
        reply_markup=markup
    )
    await message.answer("✅ Сообщение с кнопкой отправлено в канал!")

# === ЗАПУСК БОТА ===
if __name__ == '__main__':
    print("✅ Бот @LenaMusBot запущен!")
    executor.start_polling(dp, skip_updates=True)
