import os
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Переменные окружения ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # "@LenaMustest"
YOUR_TELEGRAM_ID = int(os.getenv("YOUR_TELEGRAM_ID"))  # 1030370280

# === Инициализация ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Список ожидающих ввод даты
awaiting_birth_date = set()

# === /start — сразу проверка подписки ===
@dp.message(F.text == "/start")
async def start_handler(message: Message):
    user_id = message.from_user.id
    try:
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
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📢 Подписаться на канал",
                    url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
                )]
            ])
            await message.answer(
                "🙏 Пожалуйста, подпишитесь на канал, чтобы получить расчёт бесплатно!",
                reply_markup=markup
            )
    except Exception as e:
        logger.error("Ошибка проверки подписки: %s", e)
        await message.answer("❌ Ошибка. Попробуйте позже.")

# === Обработка даты рождения ===
@dp.message(F.text)
async def handle_text(message: Message):
    user_id = message.from_user.id

    if user_id in awaiting_birth_date:
        birth_date = message.text.strip()
        if len(birth_date) >= 8 and birth_date.replace('.', '').replace(' ', '').isdigit():
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

            # Кнопка "Вернуться в канал"
            back_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="⬅️ Вернуться в канал",
                    url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
                )]
            ])
            await message.answer(
                "✅ Спасибо! Ваша заявка принята. Скоро я свяжусь с вами для расчёта.",
                reply_markup=back_markup
            )
        else:
            await message.answer("❌ Пожалуйста, введите дату в формате <code>дд.мм.гггг</code>", parse_mode="HTML")
    else:
        await start_handler(message)

# === /admin — публикация поста в канале ===
@dp.message(F.text == "/admin")
async def admin_handler(message: Message):
    if message.from_user.id != YOUR_TELEGRAM_ID:
        return

    post_text = """
МОЙ ТЕКСТ
    """
    bot_username = "LenaMusBot"  # Укажите точный юзернейм вашего бота
    channel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="ПОЛУЧИТЬ РАСЧЕТ",
            url=f"https://t.me/{bot_username}?start=matrix"
        )]
    ])

    try:
        await bot.send_message(CHANNEL_USERNAME, post_text, reply_markup=channel_keyboard)
        await message.answer("✅ Пост опубликован в канале!")
    except Exception as e:
        logger.error("Ошибка публикации: %s", e)
        await message.answer("❌ Не удалось опубликовать пост.")

# === HTTP-сервер для Render (порт 10000) ===
async def health_check(request):
    return web.Response(text="OK")

async def start_bot():
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Запуск HTTP-сервера и бота одновременно
    app = web.Application()
    app.router.add_get('/health', health_check)

    port = int(os.environ.get("PORT", 10000))

    async def main():
        await asyncio.gather(
            web._run_app(app, host='0.0.0.0', port=port),
            start_bot()
        )

    asyncio.run(main())
