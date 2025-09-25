from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import os

# === НАСТРОЙКИ ===
BOT_TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER"        # ← сюда вставьте токен!
CHANNEL_USERNAME = "@ваш_канал"              # ← например: @my_channel
YOUR_TELEGRAM_ID = 123456789                 # ← ваш ID из @userinfobot

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Состояния: будем запоминать, кто ждёт ввода даты
awaiting_birth_date = set()

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user = message.from_user
    user_id = user.id

    # Проверяем подписку
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in ['member', 'administrator', 'creator']:
            # Подписан → просим дату
            awaiting_birth_date.add(user_id)
            await message.answer(
                "✨ Отлично! Чтобы сделать расчет по матрице судьбы, напишите вашу дату рождения в формате:\n\n"
                "<code>дд.мм.гггг</code>\n\n"
                "Например: <code>15.08.1990</code>",
                parse_mode="HTML"
            )
        else:
            # Не подписан → просим подписаться
            await message.answer(
                "🙏 Пожалуйста, подпишитесь на канал, чтобы получить бесплатный расчет по матрице судьбы!",
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton(
                        "Подписаться на канал",
                        url=f"https://t.me/{CHANNEL_USERNAME[1:]}"
                    )
                )
            )
    except Exception as e:
        print("Ошибка проверки подписки:", e)
        await message.answer("Произошла ошибка. Попробуйте позже.")

# Обработка текстовых сообщений (дата рождения)
@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_text(message: types.Message):
    user = message.from_user
    user_id = user.id

    if user_id in awaiting_birth_date:
        birth_date = message.text.strip()
        # Простая проверка формата (можно улучшить)
        if len(birth_date) >= 8 and "." in birth_date:
            # Уведомление вам
            username = f"@{user.username}" if user.username else f"ID{user_id}"
            await bot.send_message(
                YOUR_TELEGRAM_ID,
                f"🆕 Новый лид!\n\n"
                f"Пользователь: {username}\n"
                f"Дата рождения: <code>{birth_date}</code>\n\n"
                f"Теперь вы можете написать ему вручную.",
                parse_mode="HTML"
            )
            awaiting_birth_date.discard(user_id)
            await message.answer("✅ Спасибо! Ваша заявка принята. Скоро я свяжусь с вами для расчета.")
        else:
            await message.answer("❌ Пожалуйста, введите дату в формате <code>дд.мм.гггг</code>", parse_mode="HTML")
    else:
        # Если не в процессе — игнорируем или перезапускаем
        await start_handler(message)

if __name__ == '__main__':
    print("Бот запущен!")
    executor.start_polling(dp, skip_updates=True)