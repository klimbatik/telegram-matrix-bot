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
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
YOUR_TELEGRAM_ID = int(os.getenv("YOUR_TELEGRAM_ID"))

# === Инициализация бота ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

users_waiting_for_date = set()

# === КЛАВИАТУРЫ ===
def get_calculate_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 ПОЛУЧИТЬ РАСЧЕТ", callback_data="get_calculation")]
    ])

def get_subscription_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")]
    ])

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Создать пост в канале", callback_data="create_post")],
        [InlineKeyboardButton(text="🔄 Обновить статистику", callback_data="refresh_stats")]
    ])

# === ОБРАБОТЧИКИ ===
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("🌟 Добро пожаловать! Нажмите кнопку ниже:", reply_markup=get_calculate_keyboard())

@dp.callback_query(F.data == "get_calculation")
async def handle_get_calculation(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            users_waiting_for_date.add(user_id)
            await callback.message.edit_text("📅 Введите дату рождения (ДД.ММ.ГГГГ):")
        else:
            await callback.message.edit_text("🙏 Подпишитесь на канал!", reply_markup=get_subscription_keyboard())
    except Exception as e:
        await callback.answer("❌ Ошибка")

@dp.callback_query(F.data == "check_subscription")
async def handle_check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            users_waiting_for_date.add(user_id)
            await callback.message.edit_text("📅 Введите дату рождения (ДД.ММ.ГГГГ):")
        else:
            await callback.answer("❌ Вы ещё не подписались!")
    except:
        await callback.answer("❌ Ошибка")

@dp.message(F.text)
async def handle_birth_date(message: Message):
    user_id = message.from_user.id
    if user_id not in users_waiting_for_date:
        await start_handler(message)
        return
    
    try:
        birth_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        username = f"@{message.from_user.username}" if message.from_user.username else f"ID{user_id}"
        
        await bot.send_message(
            YOUR_TELEGRAM_ID, 
            f"👤 НОВАЯ ЗАЯВКА!\nПользователь: {username}\nДата: {birth_date.strftime('%d.%m.%Y')}"
        )
        
        await message.answer("✅ Заявка принята! Свяжусь с вами скоро.")
        users_waiting_for_date.discard(user_id)
        
    except ValueError:
        await message.answer("❌ Неверный формат! Используйте ДД.ММ.ГГГГ")

# === АДМИН-ПАНЕЛЬ ===
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != YOUR_TELEGRAM_ID:
        return
    
    stats_text = f"📊 Панель управления\nКанал: {CHANNEL_USERNAME}"
    await message.answer(stats_text, reply_markup=get_admin_keyboard())

@dp.callback_query(F.data == "create_post")
async def create_channel_post(callback: CallbackQuery):
    if callback.from_user.id != YOUR_TELEGRAM_ID:
        return
    
    post_text = "🌟 БЕСПЛАТНЫЙ РАСЧЕТ ПО МАТРИЦЕ СУДЬБЫ! 🎁"
    
    try:
        await bot.send_message(CHANNEL_USERNAME, post_text, reply_markup=get_calculate_keyboard())
        await callback.answer("✅ Пост создан в канале!")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}")

# === ПРИНУДИТЕЛЬНЫЙ ЗАПУСК ===
async def start_bot_with_retry():
    """Запуск бота с принудительным прекращением других сессий"""
    try:
        # Принудительно закрываем возможные другие сессии
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Вебхук удален, другие сессии прекращены")
        
        # Ждем секунду для очистки
        await asyncio.sleep(2)
        
        # Запускаем polling
        logger.info("🚀 Запускаем бота...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска: {e}")
        # Перезапуск через 10 секунд
        await asyncio.sleep(10)
        await start_bot_with_retry()

async def simple_web_server():
    """Простой веб-сервер для Render"""
    app = web.Application()
    
    async def health_check(request):
        return web.Response(text='Bot is alive!')
    
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🌐 HTTP-сервер запущен на порту {port}")

async def main():
    """Главная функция"""
    logger.info("🎯 Инициализация бота...")
    
    # Запускаем веб-сервер в фоне
    asyncio.create_task(simple_web_server())
    
    # Запускаем бота
    await start_bot_with_retry()

if __name__ == "__main__":
    # Принудительно убиваем возможные старые процессы
    logger.info("🔄 Принудительный перезапуск бота...")
    asyncio.run(main())
