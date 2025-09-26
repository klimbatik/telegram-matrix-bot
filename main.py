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

    # Админ получает панель
    if user_id == YOUR_TELEGRAM_ID:
        await admin_panel(message)
        return

    # Обычный пользователь — проверяем подписку
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
                "✨ Отлично! Чтобы сделать расчёт по матрице судьбы, напишите вашу дату рождения в формате:\n\n"
                "<code>дд.мм.гггг</code>\n\n"
                "Например: <code>15.08.1990</code>",
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

    # Админ — игнорируем текст
    if user_id == YOUR_TELEGRAM_ID:
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

@dp.callback_query(F.data == "publish_post")
async def publish_post(callback: CallbackQuery):
    if callback.from_user.id != YOUR_TELEGRAM_ID:
        return

    post_text = """
🔮 Бесплатный расчёт по матрице судьбы!

Узнайте своё предназначение, кармические задачи и сильные стороны.

Нажмите кнопку ниже, чтобы получить расчёт.
    """

    bot_username = "LenaMusBot"  # Укажите точный юзернейм вашего бота
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="ПОЛУЧИТЬ РАСЧЁТ",
            url=f"https://t.me/{bot_username}?start=matrix"
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

async def start_bot():
    await dp.start_polling(bot)

if __name__ == "__main__":
    app = web.Application()
    app.router.add_get('/health', health_check)

    port = int(os.environ.get("PORT", 10000))

    async def main():
        await asyncio.gather(
            web._run_app(app, host='0.0.0.0', port=port),
            start_bot()
        )

    asyncio.run(main())
