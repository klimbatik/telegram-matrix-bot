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
        [InlineKeyboardButton(text="📢 СОЗДАТЬ ПОСТ В КАНАЛЕ", callback_data="create_post")],
        [InlineKeyboardButton(text="🔄 Обновить статистику", callback_data="refresh_stats")]
    ])

# === ОБРАБОТЧИКИ ===
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "🌟 Добро пожаловать! Получите бесплатный расчет по матрице судьбы.\n\n"
        "Нажмите кнопку ниже:",
        reply_markup=get_calculate_keyboard()
    )

@dp.callback_query(F.data == "get_calculation")
async def handle_get_calculation(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            users_waiting_for_date.add(user_id)
            await callback.message.edit_text(
                "📅 **Отлично! Вы подписаны!**\n\n"
                "Введите вашу дату рождения в формате: **ДД.ММ.ГГГГ**\n"
                "Например: 15.09.1985"
            )
        else:
            await callback.message.edit_text(
                "🙏 **ПОДПИШИТЕСЬ НА КАНАЛ, ЧТОБЫ ПОЛУЧИТЬ РАСЧЕТ!**\n\n"
                f"Канал: {CHANNEL_USERNAME}\n\n"
                "После подписки нажмите кнопку:",
                reply_markup=get_subscription_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await callback.answer("❌ Ошибка проверки подписки")

@dp.callback_query(F.data == "check_subscription")
async def handle_check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            users_waiting_for_date.add(user_id)
            await callback.message.edit_text(
                "✅ **Спасибо за подписку!**\n\n"
                "Введите вашу дату рождения в формате: **ДД.ММ.ГГГГ**\n"
                "Например: 15.09.1985"
            )
        else:
            await callback.answer("❌ Вы еще не подписались на канал!")
    except Exception as e:
        await callback.answer("❌ Ошибка проверки")

@dp.message(F.text)
async def handle_birth_date(message: Message):
    user_id = message.from_user.id
    if user_id not in users_waiting_for_date:
        await start_handler(message)
        return
    
    try:
        birth_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        
        username = message.from_user.username
        user_info = f"@{username}" if username else f"ID: {user_id}"
        first_name = message.from_user.first_name or ""
        last_name = message.from_user.last_name or ""
        full_name = f"{first_name} {last_name}".strip()

        # Отправляем уведомление вам
        await bot.send_message(
            YOUR_TELEGRAM_ID,
            f"👤 **НОВАЯ ЗАЯВКА НА РАСЧЕТ!**\n\n"
            f"• Пользователь: {user_info}\n"
            f"• Имя: {full_name if full_name else 'не указано'}\n"
            f"• Дата рождения: {birth_date.strftime('%d.%m.%Y')}\n"
            f"• ID: {user_id}\n\n"
            f"📩 Свяжитесь с клиентом!"
        )

        await message.answer(
            "✅ **Ваша заявка принята!**\n\n"
            "Я получила вашу дату рождения и скоро свяжусь с вами для подробного расчета.\n\n"
            "Обычно я отвечаю в течение 24 часов.\n\n"
            "С уважением, Елена 💫"
        )
        
        users_waiting_for_date.discard(user_id)
        
    except ValueError:
        await message.answer("❌ Неверный формат! Используйте ДД.ММ.ГГГГ")

# === АДМИН-ПАНЕЛЬ (ИСПРАВЛЕННАЯ) ===
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    """Админ-панель - ГЛАВНОЕ УСЛОВИЕ"""
    if message.from_user.id != YOUR_TELEGRAM_ID:
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    # ЭТО ГЛАВНОЕ СООБЩЕНИЕ С КНОПКОЙ
    admin_text = """
🛠 **АДМИН-ПАНЕЛЬ УПРАВЛЕНИЯ**

Здесь вы можете создать пост в канале с кнопкой "ПОЛУЧИТЬ РАСЧЕТ"

Выберите действие:
    """
    
    await message.answer(admin_text, reply_markup=get_admin_keyboard())
    logger.info("✅ Админ-панель показана пользователю")

@dp.callback_query(F.data == "create_post")
async def create_channel_post(callback: CallbackQuery):
    """СОЗДАНИЕ ПОСТА В КАНАЛЕ - ГЛАВНАЯ ФУНКЦИЯ"""
    if callback.from_user.id != YOUR_TELEGRAM_ID:
        await callback.answer("❌ Нет доступа")
        return
    
    # Текст поста для канала
    post_text = """
🌟 **БЕСПЛАТНЫЙ РАСЧЕТ ПО МАТРИЦЕ СУДЬБЫ!** 🎁

📊 Узнайте о своих:
• Сильных сторонах и талантах
• Кармических задачах  
• Предназначении по дате рождения
• Зонах роста и возможностях

✨ Получите персональный расчет БЕСПЛАТНО!

Нажмите кнопку ниже 👇
    """
    
    try:
        # СОЗДАЕМ ПОСТ В КАНАЛЕ С КНОПКОЙ
        await bot.send_message(
            CHANNEL_USERNAME, 
            post_text, 
            reply_markup=get_calculate_keyboard()
        )
        await callback.answer("✅ Пост успешно создан в канале!")
        logger.info(f"✅ Пост создан в канале {CHANNEL_USERNAME}")
        
    except Exception as e:
        error_msg = f"❌ Ошибка при создании поста: {e}"
        await callback.answer(error_msg)
        logger.error(error_msg)

@dp.callback_query(F.data == "refresh_stats")
async def refresh_stats(callback: CallbackQuery):
    if callback.from_user.id != YOUR_TELEGRAM_ID:
        await callback.answer("❌ Нет доступа")
        return
    
    stats_text = f"""
📊 **Статистика обновлена**

• Канал: {CHANNEL_USERNAME}
• Пользователей ожидают ввод даты: {len(users_waiting_for_date)}
• Время: {datetime.now().strftime('%H:%M:%S')}
    """
    
    await callback.message.edit_text(stats_text, reply_markup=get_admin_keyboard())
    await callback.answer("✅ Статистика обновлена")

# === ЗАПУСК ===
async def start_bot_with_retry():
    """Запуск бота"""
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Вебхук удален")
        
        await asyncio.sleep(2)
        logger.info("🚀 Запускаем бота...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        await asyncio.sleep(10)
        await start_bot_with_retry()

async def simple_web_server():
    """Веб-сервер для Render"""
    app = web.Application()
    
    async def health_check(request):
        return web.Response(text='✅ Бот работает!')
    
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get('PORT', 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🌐 HTTP-сервер на порту {port}")

async def main():
    logger.info("🎯 Запуск бота...")
    asyncio.create_task(simple_web_server())
    await start_bot_with_retry()

if __name__ == "__main__":
    logger.info("🔄 Запуск системы...")
    asyncio.run(main())
