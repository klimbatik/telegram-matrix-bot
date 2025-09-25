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
    text = "🌟 Добро пожаловать! Получите бесплатный расчет по матрице судьбы."
    await message.answer(text, reply_markup=get_calculate_keyboard())

@dp.callback_query(F.data == "get_calculation")
async def handle_get_calculation(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            await ask_for_birth_date(callback)
        else:
            await callback.message.edit_text(
                "🙏 ПОДПИШИТЕСЬ НА КАНАЛ для получения расчета!",
                reply_markup=get_subscription_keyboard()
            )
    except Exception as e:
        await callback.answer("❌ Ошибка проверки подписки")

@dp.callback_query(F.data == "check_subscription")
async def handle_check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            await ask_for_birth_date(callback)
        else:
            await callback.answer("❌ Вы ещё не подписались!")
    except:
        await callback.answer("❌ Ошибка проверки")

async def ask_for_birth_date(callback: CallbackQuery):
    user_id = callback.from_user.id
    users_waiting_for_date.add(user_id)
    await callback.message.edit_text("📅 Введите дату рождения в формате ДД.ММ.ГГГГ:")
    await callback.answer("✅ Введите дату рождения")

@dp.message(F.text)
async def handle_birth_date(message: Message):
    user_id = message.from_user.id
    if user_id not in users_waiting_for_date:
        await start_handler(message)
        return
    
    try:
        birth_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        username = f"@{message.from_user.username}" if message.from_user.username else f"ID{user_id}"
        
        # Отправляем уведомление вам
        await bot.send_message(
            YOUR_TELEGRAM_ID, 
            f"👤 НОВАЯ ЗАЯВКА!\nПользователь: {username}\nДата: {birth_date.strftime('%d.%m.%Y')}"
        )
        
        await message.answer("✅ Заявка принята! Я свяжусь с вами скоро.")
        users_waiting_for_date.discard(user_id)
        
    except ValueError:
        await message.answer("❌ Неверный формат! Используйте ДД.ММ.ГГГГ")

# === АДМИН-ПАНЕЛЬ ===
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != YOUR_TELEGRAM_ID:
        return
    
    stats_text = f"📊 Панель управления\nКанал: {CHANNEL_USERNAME}\nОжидают ввод даты: {len(users_waiting_for_date)}"
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

@dp.callback_query(F.data == "refresh_stats")
async def refresh_stats(callback: CallbackQuery):
    if callback.from_user.id != YOUR_TELEGRAM_ID:
        return
    
    stats_text = f"📊 Статистика обновлена\nОжидают ввод даты: {len(users_waiting_for_date)}"
    await callback.message.edit_text(stats_text, reply_markup=get_admin_keyboard())
    await callback.answer("✅ Статистика обновлена")

# === ПРОСТОЙ HTTP-СЕРВЕР ===
async def handle_request(request):
    return web.Response(text="Bot is running")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_request)
    app.router.add_get('/health', handle_request)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    await site.start()

async def main():
    # Запускаем веб-сервер в фоне
    asyncio.create_task(start_web_server())
    
    # Запускаем бота
    logger.info("✅ Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
