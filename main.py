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
YOUR_TELEGRAM_ID_STR = os.getenv("YOUR_TELEGRAM_ID")

if not all([BOT_TOKEN, CHANNEL_USERNAME, YOUR_TELEGRAM_ID_STR]):
    raise ValueError("❌ Отсутствуют переменные окружения")

try:
    YOUR_TELEGRAM_ID = int(YOUR_TELEGRAM_ID_STR)
except ValueError:
    raise ValueError("❌ YOUR_TELEGRAM_ID должен быть числом")

# === Инициализация бота ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
awaiting_birth_date = set()
awaiting_admin_post = set()

# === /start — проверка подписки и запрос даты рождения ===
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
                    text="Подписаться на канал",
                    url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
                )]
            ])
            await message.answer(
                "🙏 Пожалуйста, подпишитесь на канал, чтобы получить бесплатный расчёт по матрице судьбы!",
                reply_markup=markup
            )
    except Exception as e:
        logger.error("Ошибка проверки подписки: %s", e)
        await message.answer("⚠️ Ошибка. Попробуйте позже.")

# === Обработка даты рождения ===
@dp.message(F.text)
async def handle_text(message: Message):
    user_id = message.from_user.id

    # Если ждём дату рождения
    if user_id in awaiting_birth_date:
        try:
            birth_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
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
        except ValueError:
            await message.answer("❌ Пожалуйста, введите дату в формате <code>дд.мм.гггг</code>", parse_mode="HTML")
        return

    # Если ждём пост от админа
    if user_id in awaiting_admin_post:
        post_text = message.text
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("Получить расчёт", url=f"https://t.me/{bot._me.user.username}?start=matrix")]
        ])
        await bot.send_message(CHANNEL_USERNAME, post_text, reply_markup=markup)
        awaiting_admin_post.discard(user_id)
        await message.answer("✅ Пост отправлен в канал!")
        return

    # Если ничего не ждём — перезапускаем сценарий
    await start_handler(message)

# === /admin — создание поста с кнопкой ===
@dp.message(F.text == "/admin")
async def admin_handler(message: Message):
    if message.from_user.id != YOUR_TELEGRAM_ID:
        return
    awaiting_admin_post.add(message.from_user.id)
    await message.answer("✏️ Напишите текст поста для канала. Я добавлю кнопку «Получить расчёт» автоматически.")

# === Фиктивный HTTP-сервер для Render (бесплатно!) ===
async def health_check(request):
    return web.Response(text="✅ Bot is alive!")

async def start_bot():
    try:
        logger.info("🚀 Бот запущен!")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error("❌ Ошибка бота: %s", e)

async def create_app():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    return app

async def main():
    app = await create_app()
    bot_task = asyncio.create_task(start_bot())
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    logger.info(f"🌐 HTTP-сервер запущен на порту {port}")
    await bot_task

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен")
    except Exception as e:
        logger.error("💥 Критическая ошибка: %s", e)
