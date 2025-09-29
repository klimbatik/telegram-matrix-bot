import os
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, CommandStart
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

# Списки состояний
awaiting_birth_date = set()

# === Вспомогательные клавиатуры ===

def get_subscription_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📢 Подписаться на канал",
            url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
        )],
        [InlineKeyboardButton(
            text="✅ Я подписался", 
            callback_data="check_subscription"
        )]
    ])

def get_back_to_channel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⬅️ Вернуться в канал",
            url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}"
        )]
    ])

# === Обработчик /start (включая deep link) ===

@dp.message(CommandStart())
async def start_handler(message: Message):
    user_id = message.from_user.id

    # Проверяем, пришел ли запрос из канала (с параметром start=guide)
    is_from_channel = "guide" in message.text if message.text else False

    # Если это админ И запрос не из канала - показываем админ-панель
    if user_id == YOUR_TELEGRAM_ID and not is_from_channel:
        await admin_panel(message)
        return

    # Для всех остальных случаев (обычные пользователи или админ из канала) - стандартная логика
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            awaiting_birth_date.add(user_id)
            await message.answer(
                "🖐️ Привет! Отлично, что Вы здесь.\n\n"
    "Этот метод расчета может видеть циклы, точки сдвига, угрозы и возможности.\n\n"
    "📌 Чтобы начать — введите свою дату рождения в формате:\n\n"
    "<code>дд.мм.гггг</code>\n\n"
    "(например: <code>15.08.1990</code>)",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "🙏 Пожалуйста, подпишитесь на канал, чтобы получить расчёт бесплатно!",
                reply_markup=get_subscription_keyboard()
            )
    except Exception as e:
        logger.error("Ошибка проверки подписки: %s", e)
        await message.answer("❌ Ошибка. Попробуйте позже.")

# === Обработка кнопки "Я подписался" ===
@dp.callback_query(F.data == "check_subscription")
async def check_subscription_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            awaiting_birth_date.add(user_id)
            await callback.message.edit_text(
                "🖐️ Привет! Отлично, что Вы здесь.\n\n"
    "Этот метод расчета может видеть циклы, точки сдвига, угрозы и возможности.\n\n"
    "📌 Чтобы начать — введите свою дату рождения в формате:\n\n"
    "<code>дд.мм.гггг</code>\n\n"
    "(например: <code>15.08.1990</code>)",
                parse_mode="HTML"
            )
        else:
            await callback.answer("❌ Вы ещё не подписались на канал!", show_alert=True)
    except Exception as e:
        logger.error("Ошибка проверки подписки: %s", e)
        await callback.answer("❌ Ошибка проверки. Попробуйте позже.")

# === Обработка даты рождения ===

@dp.message(F.text)
async def handle_text(message: Message):
    user_id = message.from_user.id

    # Админ — игнорируем текст (кроме случаев когда он тестирует функциональность)
    if user_id == YOUR_TELEGRAM_ID and user_id not in awaiting_birth_date:
        return

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
            await message.answer(
                "✅ Спасибо! Ваша заявка принята. Скоро я свяжусь с вами для расчёта.",
                reply_markup=get_back_to_channel_keyboard()
            )
        else:
            await message.answer("❌ Пожалуйста, введите дату в формате <code>дд.мм.гггг</code>", parse_mode="HTML")
    else:
        # Если не в процессе — перезапускаем сценарий
        await start_handler(message)

# === Админ-панель ===

async def admin_panel(message: Message):
    stats_text = f"""
📊 Админ-панель
Ожидают ввод даты: {len(awaiting_birth_date)}
Канал: {CHANNEL_USERNAME}
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Опубликовать пост", callback_data="publish_post")]
    ])
    await message.answer(stats_text, reply_markup=keyboard)

# === ОБРАБОТЧИК КНОПКИ "ОПУБЛИКОВАТЬ ПОСТ" ===
@dp.callback_query(F.data == "publish_post")
async def publish_post_handler(callback: CallbackQuery):
    if callback.from_user.id != YOUR_TELEGRAM_ID:
        return

    post_text = """
МОЙ ТЕКСТ
    """

    bot_username = "ElenaMusBot"  # Ваш бот ElenaMusBot
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="ПОЛУЧИТЬ РАСЧЕТ",
            url=f"https://t.me/{bot_username}?start=guide"
        )]
    ])

    try:
        await bot.send_message(CHANNEL_USERNAME, post_text, reply_markup=markup)
        await callback.answer("✅ Пост опубликован в канале!")
    except Exception as e:
        logger.error("Ошибка публикации: %s", e)
        await callback.answer("❌ Не удалось опубликовать пост.")

# === HTTP-сервер для Render ===

async def health_check(request):
    return web.Response(text="OK")

async def start_http_server():
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)  # Добавляем корневой путь тоже
    
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"HTTP server started on port {port}")

async def main():
    # Запускаем HTTP-сервер и бота параллельно
    await asyncio.gather(
        start_http_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())


