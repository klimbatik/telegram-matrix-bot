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
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # "@LenaMustest"
YOUR_TELEGRAM_ID = int(os.getenv("YOUR_TELEGRAM_ID"))

# === Инициализация бота ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище для пользователей, которые оставили заявки
users_waiting_for_date = set()

# === КЛАВИАТУРЫ ===

def get_calculate_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 ПОЛУЧИТЬ РАСЧЕТ", callback_data="get_calculation")]
    ])

def get_subscription_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")]
    ])

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Создать пост в канале", callback_data="create_post")],
        [InlineKeyboardButton(text="🔄 Обновить статистику", callback_data="refresh_stats")]
    ])

# === ОСНОВНЫЕ ОБРАБОТЧИКИ ===

@dp.message(Command("start"))
async def start_handler(message: Message):
    welcome_text = """
🌟 Добро пожаловать! 

Я помогу вам получить бесплатный расчет по матрице судьбы.

Нажмите кнопку ниже, чтобы начать:
    """
    await message.answer(welcome_text, reply_markup=get_calculate_keyboard())

@dp.callback_query(F.data == "get_calculation")
async def handle_get_calculation(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            await ask_for_birth_date(callback)
        else:
            await callback.message.edit_text(
                "🙏 **ПОДПИШИТЕСЬ НА КАНАЛ, ЧТОБЫ ПОЛУЧИТЬ БЕСПЛАТНЫЙ РАСЧЕТ**\n\n"
                f"Канал: {CHANNEL_USERNAME}\n\n"
                "После подписки нажмите кнопку ниже:",
                reply_markup=get_subscription_keyboard()
            )
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        await callback.answer("❌ Ошибка. Попробуйте позже.")

@dp.callback_query(F.data == "check_subscription")
async def handle_check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            await ask_for_birth_date(callback)
        else:
            await callback.answer("❌ Вы ещё не подписались на канал!")
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        await callback.answer("❌ Ошибка проверки. Попробуйте позже.")

async def ask_for_birth_date(callback: CallbackQuery):
    user_id = callback.from_user.id
    users_waiting_for_date.add(user_id)
    
    instruction_text = """
📅 **Отлично! Вы подписаны!**

Для расчета матрицы судьбы мне нужна ваша дата рождения.

📋 **Введите дату в формате: ДД.ММ.ГГГГ**
Например: 15.09.1985

⚠️ Расчет будет точным только при правильной дате рождения.
    """
    
    await callback.message.edit_text(instruction_text, reply_markup=None)
    await callback.answer("✅ Введите дату рождения")

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
        notification_text = f"""
👤 **НОВАЯ ЗАЯВКА НА РАСЧЕТ!**

• Пользователь: {user_info}
• Имя: {full_name if full_name else 'не указано'}
• Дата рождения: {birth_date.strftime('%d.%m.%Y')}
• ID: {user_id}

📩 Свяжитесь с клиентом для подробного расчета!
        """
        
        await bot.send_message(YOUR_TELEGRAM_ID, notification_text)
        
        await message.answer(
            "✅ **Ваша заявка принята!**\n\n"
            "Я получила вашу дату рождения и скоро свяжусь с вами для подробного расчета матрицы судьбы.\n\n"
            "Обычно я отвечаю в течение 24 часов.\n\n"
            "С уважением, Елена 💫"
        )
        
        users_waiting_for_date.discard(user_id)
        
    except ValueError:
        await message.answer(
            "❌ **Неверный формат даты!**\n\n"
            "Пожалуйста, введите дату в формате: **ДД.ММ.ГГГГ**\n"
            "Например: 15.09.1985\n\n"
            "Попробуйте еще раз:"
        )

# === АДМИН-ПАНЕЛЬ (ИСПРАВЛЕННАЯ) ===

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    """Панель управления для администратора"""
    if message.from_user.id != YOUR_TELEGRAM_ID:
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    stats_text = f"""
📊 **Панель управления ботом**

• Канал: {CHANNEL_USERNAME}
• Пользователей ожидают ввод даты: {len(users_waiting_for_date)}

Что вы хотите сделать?
    """
    
    await message.answer(stats_text, reply_markup=get_admin_keyboard())

@dp.callback_query(F.data == "create_post")
async def create_channel_post(callback: CallbackQuery):
    """Создание поста в канале с кнопкой"""
    if callback.from_user.id != YOUR_TELEGRAM_ID:
        await callback.answer("❌ Нет доступа")
        return
    
    post_text = """
🌟 **БЕСПЛАТНЫЙ РАСЧЕТ ПО МАТРИЦЕ СУДЬБЫ!**

📊 Узнайте о своих:
• Сильных сторонах и талантах
• Кармических задачах
• Предназначении по дате рождения
• Зонах роста и возможностях

🎁 Получите персональный расчет БЕСПЛАТНО!

Нажмите кнопку ниже 👇
    """
    
    try:
        await bot.send_message(
            CHANNEL_USERNAME, 
            post_text, 
            reply_markup=get_calculate_keyboard()
        )
        await callback.answer("✅ Пост создан в канале!")
    except Exception as e:
        logger.error(f"Ошибка создания поста: {e}")
        await callback.answer(f"❌ Ошибка: {e}")

@dp.callback_query(F.data == "refresh_stats")
async def refresh_stats(callback: CallbackQuery):
    """Обновление статистики"""
    if callback.from_user.id != YOUR_TELEGRAM_ID:
        await callback.answer("❌ Нет доступа")
        return
    
    stats_text = f"""
📊 **Обновленная статистика**

• Канал: {CHANNEL_USERNAME}
• Пользователей ожидают ввод даты: {len(users_waiting_for_date)}
• Статистика обновлена: {datetime.now().strftime('%H:%M:%S')}
    """
    
    await callback.message.edit_text(stats_text, reply_markup=get_admin_keyboard())
    await callback.answer("✅ Статистика обновлена")

# === HTTP-сервер для Render ===
async def health_check(request):
    return web.Response(text="✅ Бот работает!")

async def start_bot():
    await dp.start_polling(bot)

if __name__ == "__main__":
    app = web.Application()
    app.router.add_get('/health', health_check)
    
    port = int(os.environ.get("PORT", 10000))
    
    async def main():
        # Запускаем бота
        await dp.start_polling(bot)
    
    # Запускаем веб-сервер и бота
    async def run_all():
        await asyncio.gather(
            web._run_app(app, host='0.0.0.0', port=port),
            main()
        )
    
    asyncio.run(run_all())
