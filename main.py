import os
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiohttp import web

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Переменные окружения ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # Например: "@LenaMustest"
YOUR_TELEGRAM_ID = int(os.getenv("YOUR_TELEGRAM_ID"))

# === Инициализация бота ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище для отслеживания подписчиков
subscribed_users = set()

# === КЛАВИАТУРЫ ===

# Основная клавиатура с кнопкой "ПОЛУЧИТЬ РАСЧЕТ"
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 ПОЛУЧИТЬ РАСЧЕТ", callback_data="get_guide")]
    ])

# Клавиатура с проверкой подписки
def get_subscription_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")]
    ])

# === ОБРАБОТЧИКИ ===

@dp.message(Command("start"))
async def start_handler(message: Message):
    """Обработчик команды /start"""
    welcome_text = """
🌟 Добро пожаловать! 

Я помогу вам получить полезный гайд по матрице судьбы.

Нажмите кнопку ниже, чтобы получить доступ к материалам:
    """
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@dp.callback_query(F.data == "get_guide")
async def handle_get_guide(callback: CallbackQuery):
    """Обработчик кнопки ПОЛУЧИТЬ РАСЧЕТ"""
    user_id = callback.from_user.id
    
    # Проверяем подписку
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            # Пользователь подписан - выдаём гайд
            await send_guide(callback)
            subscribed_users.add(user_id)
        else:
            # Пользователь не подписан - просим подписаться
            await callback.message.edit_text(
                "📋 Чтобы получить гайд, пожалуйста, подпишитесь на наш канал:\n\n"
                f"➡️ {CHANNEL_USERNAME}\n\n"
                "После подписки нажмите кнопку ниже:",
                reply_markup=get_subscription_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        await callback.answer("❌ Ошибка проверки подписки. Попробуйте позже.")

@dp.callback_query(F.data == "check_subscription")
async def handle_check_subscription(callback: CallbackQuery):
    """Проверка подписки после нажатия кнопки 'Я подписался'"""
    user_id = callback.from_user.id
    
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            # Успешная подписка - выдаём гайд
            await send_guide(callback)
            subscribed_users.add(user_id)
        else:
            # Пользователь всё ещё не подписан
            await callback.answer("❌ Вы ещё не подписались на канал!")
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        await callback.answer("❌ Ошибка проверки. Попробуйте позже.")

async def send_guide(callback: CallbackQuery):
    """Отправка гайда пользователю"""
    guide_text = """
📚 **Ваш гайд готов!**

Вот ссылка на материалы: [ссылка на ваш гайд]

Также вы можете:
• Получить персональный расчёт
• Задать вопросы

Для нового гайда нажмите /start
    """
    
    # Удаляем предыдущее сообщение с кнопками
    try:
        await callback.message.delete()
    except:
        pass
    
    # Отправляем гайд
    await callback.message.answer(guide_text)
    await callback.answer("✅ Гайд отправлен!")

# === УПРАВЛЕНИЕ СООБЩЕНИЯМИ В КАНАЛЕ ===

@dp.message(F.chat.type == "channel")
async def handle_channel_messages(message: Message):
    """Автоматическое удаление служебных сообщений в канале"""
    # Удаляем сообщения о смене названия канала
    if message.service and any(keyword in str(message.service) for keyword in ["title", "name", "назван"]):
        try:
            await message.delete()
            logger.info("🗑 Удалено служебное сообщение о смене названия")
        except Exception as e:
            logger.error(f"Ошибка удаления сообщения: {e}")

# === ПАНЕЛЬ АДМИНИСТРАТОРА ===

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    """Панель управления для администратора"""
    if message.from_user.id != YOUR_TELEGRAM_ID:
        return
    
    stats_text = f"""
  Статистика бота
• Подписчиков получивших гайд: {len(subscribed_users)}
• Канал: {CHANNEL_USERNAME}
    """
    
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Опубликовать пост", callback_data="publish_post")],
        [InlineKeyboardButton(text="🔄 Обновить статистику", callback_data="refresh_stats")]
    ])
    
    await message.answer(stats_text, reply_markup=admin_keyboard)

@dp.callback_query(F.data == "publish_post")
async def publish_guide_offer(callback: CallbackQuery):
    """Публикация предложения в канал"""
    if callback.from_user.id != YOUR_TELEGRAM_ID:
        return
    
    post_text = """
МОЙ ТЕКСТ
    """
    
    channel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ПОЛУЧИТЬ РАСЧЕТ", url=f"https://t.me/{(await bot.get_me()).username}?start=guide")]
    ])
    
    try:
        await bot.send_message(CHANNEL_USERNAME, post_text, reply_markup=channel_keyboard)
        await callback.answer("✅ Пост опубликован в канале!")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}")

# === HTTP-сервер для Render ===
async def health_check(request):
    return web.Response(text="✅ Bot is running!")

async def start_bot():
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Веб-сервер для Render
    app = web.Application()
    app.router.add_get('/health', health_check)
    
    port = int(os.environ.get("PORT", 10000))
    
    async def main():
        await asyncio.gather(
            web._run_app(app, host='0.0.0.0', port=port),
            start_bot()
        )
    
    asyncio.run(main())

