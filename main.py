import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# === Загрузка переменных окружения ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # Пример: "@LenaMustest"
YOUR_TELEGRAM_ID_STR = os.getenv("YOUR_TELEGRAM_ID")

if not all([BOT_TOKEN, CHANNEL_USERNAME, YOUR_TELEGRAM_ID_STR]):
    raise ValueError("❌ Отсутствуют переменные окружения: BOT_TOKEN, CHANNEL_USERNAME или YOUR_TELEGRAM_ID")

try:
    YOUR_TELEGRAM_ID = int(YOUR_TELEGRAM_ID_STR)
except ValueError:
    raise ValueError("❌ YOUR_TELEGRAM_ID должен быть целым числом")

# === Инициализация бота ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Список ожидающих ввод даты
awaiting_birth_date = set()

# === /start — основной сценарий ===
@dp.message(F.text == "/start")
async def start_handler(message: Message):
    user_id = message.from_user.id
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ['member', 'administrator', 'creator']:
            awaiting_birth_date.add(user_id)
            await message.answer(
                "✨ Отлично! Чтобы сделать расчёт по матрице судьбы, напишите вашу дату рождения в формате:\n\n"
                "<code>дд.мм.гггг</code>\n\n"
                "Например: <code>15.08.1990</code>",
                parse_mode="HTML"
            )
        else:
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="Подписаться на канал",
                    url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
                )]
            ])
            await message.answer(
                "🙏 Пожалуйста, подпишитесь на канал, чтобы получить бесплатный расчёт по матрице судьбы!",
                reply_markup=markup
            )
    except Exception as e:
        print("Ошибка проверки подписки:", e)
        await message.answer("Произошла ошибка. Попробуйте позже.")

# === Обработка даты рождения ===
@dp.message(F.text)
async def handle_text(message: Message):
    user_id = message.from_user.id
    if user_id in awaiting_birth_date:
        birth_date = message.text.strip()
        parts = birth_date.split('.')
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            day, month, year = parts
            if len(day) == 2 and len(month) == 2 and len(year) == 4:
                username = f"@{message.from_user.username}" if message.from_user.username else f"ID{user_id}"
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

# === /publish — отправка сообщения с кнопкой в канал ===
@dp.message(F.text == "/publish")
async def publish_offer(message: Message):
    if message.from_user.id != YOUR_TELEGRAM_ID:
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Заказать расчёт",
            url="https://t.me/LenaMusBot?start=matrix"
        )]
    ])
    await bot.send_message(
        CHANNEL_USERNAME,
        "🔮 Бесплатный расчёт по матрице судьбы!\n\n"
        "Узнайте своё предназначение, кармические задачи и сильные стороны.\n"
        "Нажмите кнопку ниже, чтобы получить расчёт.",
        reply_markup=markup
    )
    await message.answer("✅ Сообщение с кнопкой отправлено в канал!")

# === ЗАПУСК БОТА ===
async def main():
    print("✅ Бот @LenaMusBot запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
