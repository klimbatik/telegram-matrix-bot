import os
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# === Логирование ===
logging.basicConfig(level=logging.INFO)

# === Переменные окружения ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # пример: "@my_channel"
YOUR_TELEGRAM_ID = os.getenv("YOUR_TELEGRAM_ID")

if not all([BOT_TOKEN, CHANNEL_USERNAME, YOUR_TELEGRAM_ID]):
    raise ValueError("❌ Нет переменных окружения: BOT_TOKEN, CHANNEL_USERNAME или YOUR_TELEGRAM_ID")

try:
    YOUR_TELEGRAM_ID = int(YOUR_TELEGRAM_ID)
except ValueError:
    raise ValueError("❌ YOUR_TELEGRAM_ID должен быть числом (например, 1030370280)")

# === Инициализация ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Список пользователей, ожидающих дату рождения
awaiting_birth_date = set()


# === /start ===
@dp.message(F.text == "/start")
async def start_handler(message: Message):
    user_id = message.from_user.id
    try:
        # Проверка подписки
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            awaiting_birth_date.add(user_id)
            await message.answer(
                "✨ Отлично! Чтобы сделать расчёт по матрице судьбы, напишите вашу дату рождения в формате:\n\n"
                "<code>дд.мм.гггг</code>\n\n"
                "Например: <code>15.08.1990</code>",
                parse_mode="HTML"
            )
        else:
            markup = InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Подписаться на канал",
                        url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
                    )
                ]]
            )
            await message.answer(
                "🙏 Пожалуйста, подпишитесь на канал, чтобы получить бесплатный расчёт.",
                reply_markup=markup
            )
    except Exception as e:
        logging.error(f"Ошибка проверки подписки: {e}")
        await message.answer("⚠️ Ошибка при проверке подписки. Попробуйте позже.")


# === Обработка текста (дата рождения) ===
@dp.message(F.text)
async def handle_text(message: Message):
    user_id = message.from_user.id
    if user_id in awaiting_birth_date:
        text = message.text.strip()
        try:
            birth_date = datetime.strptime(text, "%d.%m.%Y").date()
        except ValueError:
            await message.answer("❌ Введите дату в формате <code>дд.мм.гггг</code>", parse_mode="HTML")
            return

        username = f"@{message.from_user.username}" if message.from_user.username else f"ID{user_id}"
        await bot.send_message(
            YOUR_TELEGRAM_ID,
            f"🆕 Новый лид!\n\n"
            f"Пользователь: {username}\n"
            f"Дата рождения: <code>{birth_date.strftime('%d.%m.%Y')}</code>\n\n"
            f"Теперь вы можете написать ему вручную.",
            parse_mode="HTML"
        )

        awaiting_birth_date.discard(user_id)
        await message.answer("✅ Спасибо! Ваша заявка принята. Скоро я свяжусь с вами для расчёта.")
    else:
        await start_handler(message)


# === /publish (отправка поста в канал) ===
@dp.message(F.text == "/publish")
async def publish_offer(message: Message):
    if message.from_user.id != YOUR_TELEGRAM_ID:
        return

    markup = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="Заказать расчёт", url="https://t.me/LenaMusBot?start=matrix")
        ]]
    )

    await bot.send_message(
        CHANNEL_USERNAME,
        "🔮 Бесплатный расчёт по матрице судьбы!\n\n"
        "Узнайте своё предназначение, кармические задачи и сильные стороны.\n"
        "Нажмите кнопку ниже, чтобы получить расчёт.",
        reply_markup=markup
    )
    await message.answer("✅ Сообщение с кнопкой отправлено в канал!")


# === Запуск бота ===
async def main():
    logging.info("✅ Бот запущен!")
    await dp.start_polling(bot)
    if name == "main":
    asyncio.run(main())
