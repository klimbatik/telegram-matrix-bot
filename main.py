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

# Кнопка для поста в канале
def get_channel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 ПОЛУЧИТЬ РАСЧЕТ", url=f"https://t.me/{(await bot.get_me()).username}?start=channel")]
    ])

# Кнопка для проверки подписки в боте
def get_subscription_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")]
    ])

# Админ-панель
def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Опубликовать пост", callback_data="publish_post")],
        [InlineKeyboardButton(text="🔄 Обновить статистику", callback_data="refresh_stats")]
    ])

# === ОСНОВНЫЕ ОБРАБОТЧИКИ ===

@dp.message(Command("start"))
async def start_handler(message: Message):
    """Обработчик команды /start - когда клиент приходит из канала"""
    # Проверяем, пришел ли пользователь из канала
    if message.text.endswith('channel'):
        # Пользователь пришел из канала - сразу проверяем подписку
        user_id = message.from_user.id
        
        try:
            chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
            if chat_member.status in ["member", "administrator", "creator"]:
                # Подписан - просим дату рождения
                users_waiting_for_date.add(user_id)
                await message.answer(
                    "📅 **Для расчета введите вашу дату рождения в формате: ДД.ММ.ГГГГ**\n\n"
                    "Например: 15.09.1985"
                )
            else:
                # Не подписан - просим подписаться
                await message.answer(
                    "🙏 **Для получения расчета подпишитесь на наш канал**\n\n"
                    f"Канал: {CHANNEL_USERNAME}",
                    reply_markup=get_subscription_keyboard()
                )
        except Exception as e:
            await message.answer("❌ Ошибка проверки подписки")
    
    else:
        # Обычный старт - просто приветствие
        await message.answer(
            "🌟 Добро пожаловать! Нажмите кнопку для получения расчета:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 ПОЛУЧИТЬ РАСЧЕТ", callback_data="get_calculation")]
            ])
        )

@dp.callback_query(F.data == "get_calculation")
async def handle_get_calculation(callback: CallbackQuery):
    """Обработчик кнопки ПОЛУЧИТЬ РАСЧЕТ внутри бота"""
    user_id = callback.from_user.id
    
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            users_waiting_for_date.add(user_id)
            await callback.message.edit_text("📅 Введите дату рождения (ДД.ММ.ГГГГ):")
        else:
            await callback.message.edit_text(
                "🙏 Подпишитесь на канал для получения расчета:",
                reply_markup=get_subscription_keyboard()
            )
    except Exception as e:
        await callback.answer("❌ Ошибка проверки")

@dp.callback_query(F.data == "check_subscription")
async def handle_check_subscription(callback: CallbackQuery):
    """Проверка подписки после нажатия 'Я подписался'"""
    user_id = callback.from_user.id
    
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            users_waiting_for_date.add(user_id)
            await callback.message.edit_text("📅 Введите дату рождения (ДД.ММ.ГГГГ):")
        else:
            await callback.answer("❌ Вы еще не подписались!")
    except:
        await callback.answer("❌ Ошибка проверки")

@dp.message(F.text)
async def handle_birth_date(message: Message):
    """Обработка введенной даты рождения"""
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
            f"👤 **НОВАЯ ЗАЯВКА!**\n\n"
            f"Пользователь: {username}\n"
            f"Дата рождения: {birth_date.strftime('%d.%m.%Y')}\n"
            f"ID: {user_id}"
        )
        
        await message.answer("✅ Заявка принята! Я свяжусь с вами скоро.")
        users_waiting_for_date.discard(user_id)
        
    except ValueError:
        await message.answer("❌ Неверный формат! Используйте ДД.ММ.ГГГГ")

# === АДМИН-ПАНЕЛЬ ===

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    """Админ-панель - создание поста в канале"""
    if message.from_user.id != YOUR_TELEGRAM_ID:
        return
    
    stats_text = f"📊 Админ-панель\nОжидают ввод даты: {len(users_waiting_for_date)}"
    await message.answer(stats_text, reply_markup=get_admin_keyboard())

@dp.callback_query(F.data == "publish_post")
async def publish_post(callback: CallbackQuery):
    """Публикация поста в канале"""
    if callback.from_user.id != YOUR_TELEGRAM_ID:
        return
    
    post_text = """
🌟 **БЕСПЛАТНЫЙ РАСЧЕТ по матрице судьбы!**

Получите персональный расчет сейчас! 👇
    """
    
    try:
        await bot.send_message(CHANNEL_USERNAME, post_text, reply_markup=get_channel_keyboard())
        await callback.answer("✅ Пост опубликован в канале!")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}")

@dp.callback_query(F.data == "refresh_stats")
async def refresh_stats(callback: CallbackQuery):
    """Обновление статистики"""
    if callback.from_user.id != YOUR_TELEGRAM_ID:
        return
    
    stats_text = f"📊 Статистика обновлена\nОжидают ввод даты: {len(users_waiting_for_date)}"
    await callback.message.edit_text(stats_text, reply_markup=get_admin_keyboard())
    await callback.answer("✅ Обновлено")

# === ЗАПУСК ===
async def start_bot():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

async def web_server():
    app = web.Application()
    app.router.add_get('/', lambda r: web.Response(text='OK'))
    app.router.add_get('/health', lambda r: web.Response(text='OK'))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    await asyncio.gather(web_server(), start_bot())

if __name__ == "__main__":
    asyncio.run(main())
