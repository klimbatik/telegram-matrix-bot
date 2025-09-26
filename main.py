import os
import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
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

# Хранилища
subscribed_users = set()
awaiting_birth_date = set()

# === КЛАВИАТУРЫ ===

# Основная клавиатура с кнопкой "ПОЛУЧИТЬ РАСЧЕТ"
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 ПОЛУЧИТЬ РАСЧЕТ", callback_data="get_calculation")]
    ])

# Клавиатура с проверкой подписки
def get_subscription_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_subscription")]
    ])

# Клавиатура "Вернуться в канал"
def get_back_to_channel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Вернуться в канал", url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}")]
    ])

# === ОБРАБОТЧИКИ ===

@dp.message(Command("start"))
async def start_handler(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Проверяем подписку при старте
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            # Пользователь подписан - просим дату рождения
            await message.answer(
                "🌟 Отлично! Чтобы сделать расчёт по матрице судьбы, напишите вашу дату рождения в формате:\n\n"
                "<code>дд.мм.гггг</code>\n\n"
                "Например: <code>15.08.1990</code>",
                parse_mode="HTML"
            )
            awaiting_birth_date.add(user_id)
            subscribed_users.add(user_id)
        else:
            # Пользователь не подписан - просим подписаться
            welcome_text = """
🌟 Добро пожаловать! 

Пожалуйста, подпишитесь на канал, чтобы получить расчёт бесплатно.

После подписки нажмите кнопку ниже:
            """
            await message.answer(welcome_text, reply_markup=get_subscription_keyboard())
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        await message.answer("❌ Ошибка проверки подписки. Попробуйте позже.")

@dp.callback_query(F.data == "get_calculation")
async def handle_get_calculation(callback: CallbackQuery):
    """Обработчик кнопки ПОЛУЧИТЬ РАСЧЕТ из канала"""
    user_id = callback.from_user.id
    
    # Проверяем подписку
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ["member", "administrator", "creator"]:
            # Пользователь подписан - просим дату рождения
            await callback.message.edit_text(
                "🌟 Отлично! Чтобы сделать расчёт по матрице судьбы, напишите вашу дату рождения в формате:\n\n"
                "<code>дд.мм.гггг</code>\n\n"
                "Например: <code>15.08.1990</code>",
                parse_mode="HTML"
            )
            awaiting_birth_date.add(user_id)
            subscribed_users.add(user_id)
        else:
            # Пользователь не подписан - просим подписаться
            await callback.message.edit_text(
                "📋 Чтобы получить расчёт, пожалуйста, подпишитесь на наш канал:\n\n"
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
            # Успешная подписка - просим дату рождения
            await callback.message.edit_text(
                "🌟 Отлично! Чтобы сделать расчёт по матрице судьбы, напишите вашу дату рождения в формате:\n\n"
                "<code>дд.мм.гггг</code>\n\n"
                "Например: <code>15.08.1990</code>",
                parse_mode="HTML"
            )
            awaiting_birth_date.add(user_id)
            subscribed_users.add(user_id)
        else:
            # Пользователь всё ещё не подписан
            await callback.answer("❌ Вы ещё не подписались на канал!")
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        await callback.answer("❌ Ошибка проверки. Попробуйте позже.")

# === Обработка даты рождения ===
@dp.message(F.content_type == "text")
async def handle_text(message: Message):
    user_id = message.from_user.id
    
    if user_id in awaiting_birth_date:
        birth_date = message.text.strip()
        
        # Проверяем формат даты
        if (len(birth_date) >= 8 and 
            birth_date.replace('.', '').replace(' ', '').isdigit() and
            birth_date.count('.') == 2):
            
            # Отправляем уведомление администратору
            username = f"@{message.from_user.username}" if message.from_user.username else f"ID{user_id}"
            await bot.send_message(
                YOUR_TELEGRAM_ID,
                f"🆕 Новый лид!\n\n"
                f"Пользователь: {username}\n"
                f"Дата рождения: <code>{birth_date}</code>\n\n"
                f"Теперь вы можете написать ему вручную.",
                parse_mode="HTML"
            )
            
            # Удаляем пользователя из ожидания
            awaiting_birth_date.discard(user_id)
            
            # Отправляем подтверждение пользователю
            await message.answer(
                "✅ Спасибо! Ваша заявка принята. Скоро я свяжусь с вами для расчёта.\n\n"
                "А пока можете вернуться в наш канал:",
                reply_markup=get_back_to_channel_keyboard()
            )
        else:
            await message.answer(
                "❌ Пожалуйста, введите дату в формате <code>дд.мм.гггг</code>\n\n"
                "Например: <code>15.08.1990</code>",
                parse_mode="HTML"
            )
    else:
        # Если пользователь не в процессе ввода даты, отправляем стартовое сообщение
        await start_handler(message)

# === УПРАВЛЕНИЕ СООБЩЕНИЯМИ В КАНАЛЕ ===
@dp.message(F.chat.type == "channel")
async def handle_channel_messages(message: Message):
    """Автоматическое удаление служебных сообщений в канале"""
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
📊 Статистика бота:
• Подписчиков получивших гайд: {len(subscribed_users)}
• Ожидают ввода даты: {len(awaiting_birth_date)}
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
🎁 БЕСПЛАТНЫЙ РАСЧЕТ по матрице судьбы!

Узнайте:
• Ваши сильные стороны
• Кармические задачи  
• Предназначение по дате рождения

Получите персональный расчет прямо сейчас! 👇
    """
    
    channel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 ПОЛУЧИТЬ РАСЧЕТ", url=f"https://t.me/{(await bot.get_me()).username}?start=guide")]
    ])
    
    try:
        await bot.send_message(CHANNEL_USERNAME, post_text, reply_markup=channel_keyboard)
        await callback.answer("✅ Пост опубликован в канале!")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}")

@dp.callback_query(F.data == "refresh_stats")
async def refresh_stats(callback: CallbackQuery):
    """Обновление статистики"""
    if callback.from_user.id != YOUR_TELEGRAM_ID:
        return
    
    stats_text = f"""
📊 Статистика бота (обновлено):
• Подписчиков получивших гайд: {len(subscribed_users)}
• Ожидают ввода даты: {len(awaiting_birth_date)}
• Канал: {CHANNEL_USERNAME}
    """
    
    await callback.message.edit_text(stats_text)
    await callback.answer("✅ Статистика обновлена!")

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
