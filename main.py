import os
import asyncio
import json
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton

# ==================== НАСТРОЙКИ ====================

# Токен бота из переменных окружения (БЕЗОПАСНО!)
BOT_TOKEN = os.getenv('BOT_TOKEN')

# ID админа (твой Telegram ID)
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))

# Пароль для админки
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

# URL Mini App (пока заглушка, потом заменим)
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://cekarinzahar44-del.github.io/food-delivery/')

# Проверка токена
if not BOT_TOKEN:
    raise ValueError("❌ ОШИБКА: Не найден BOT_TOKEN в переменных окружения!")

# Создаем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==================== БАЗА ДАННЫХ ====================

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect('food.db')
    cursor = conn.cursor()
    
    # Таблица заказов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            items TEXT,
            total_amount INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )    ''')
    
    # Таблица блюд (заглушка для будущего)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price INTEGER,
            category TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

# ==================== КЛАВИАТУРЫ ====================

def get_main_keyboard():
    """Главная клавиатура с кнопкой меню"""
    keyboard = [
        [KeyboardButton(text="📱 Открыть меню", web_app=WebAppInfo(url=WEBAPP_URL))],
        [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="📞 Контакты")],
        [KeyboardButton(text="❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_admin_keyboard():
    """Админская клавиатура"""
    keyboard = [
        [KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="📦 Заказы"), KeyboardButton(text="🍽️ Меню")],
        [KeyboardButton(text="🔙 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# ==================== ОБРАБОТЧИКИ ====================

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    """Приветственное сообщение"""
    await message.answer(
        f"🍔 <b>Добро пожаловать в Food Delivery!</b>\n\n"
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        f"📱 У нас вы можете заказать:\n"
        f"• 🍕 Пиццу\n"
        f"• 🍔 Бургеры\n"
        f"• 🍣 Суши и роллы\n"
        f"• 🍝 Пасту\n"
        f"• 🥗 Салаты\n"        f"• 🥤 Напитки\n\n"
        f"🚀 <b>Нажмите кнопку ниже, чтобы открыть меню!</b>",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    
    # Уведомление админу о новом пользователе
    if ADMIN_ID != 0:
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🔔 <b>Новый пользователь!</b>\n\n"
                f"👤 {message.from_user.first_name}\n"
                f"📱 @{message.from_user.username or 'Нет username'}\n"
                f"ID: <code>{message.from_user.id}</code>",
                parse_mode='HTML'
            )
        except:
            pass

@dp.message(Command('menu'))
async def cmd_menu(message: types.Message):
    """Открыть меню"""
    await message.answer(
        "📱 <b>Открываю меню...</b>",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

@dp.message(Command('admin'))
async def cmd_admin(message: types.Message):
    """Админ-панель - вход"""
    if message.from_user.id != ADMIN_ID and ADMIN_ID != 0:
        await message.answer("❌ <b>Доступ запрещён!</b>\n\nТолько для владельца.", parse_mode='HTML')
        return
    
    await message.answer(
        f"🔐 <b>Админ-панель</b>\n\n"
        f"👋 Привет, владелец!\n\n"
        f"📊 <b>Функции:</b>\n"
        f"• Просмотр заказов\n"
        f"• Управление меню\n"
        f"• Статистика\n\n"
        f"🔑 <b>Пароль:</b> <code>{ADMIN_PASSWORD}</code>\n\n"
        f"⚠️ <i>Веб-версия админки будет доступна после запуска Mini App</i>",
        reply_markup=get_admin_keyboard(),
        parse_mode='HTML'
    )

@dp.message(Command('stats'))async def cmd_stats(message: types.Message):
    """Статистика"""
    if message.from_user.id != ADMIN_ID and ADMIN_ID != 0:
        return
    
    conn = sqlite3.connect('food.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM orders')
    total_orders = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status='pending'")
    pending_orders = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(total_amount) FROM orders WHERE status='completed'")
    revenue = cursor.fetchone()[0] or 0
    
    conn.close()
    
    await message.answer(
        f"📊 <b>Статистика</b>\n\n"
        f"📦 Всего заказов: <b>{total_orders}</b>\n"
        f"⏳ В обработке: <b>{pending_orders}</b>\n"
        f"💰 Выручка: <b>{revenue} ₽</b>\n\n"
        f"📈 Бот работает! ✅",
        parse_mode='HTML'
    )

@dp.message(Command('help'))
async def cmd_help(message: types.Message):
    """Помощь"""
    await message.answer(
        "📖 <b>Помощь</b>\n\n"
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "📱 <b>Команды:</b>\n"
        "/start - Главное меню\n"
        "/menu - Открыть меню\n"
        "/admin - Админ-панель\n"
        "/stats - Статистика\n"
        "/help - Эта справка\n\n"
        "📞 <b>Контакты:</b>\n"
        "📧 Email: support@fooddelivery.com\n"
        "📱 Telegram: @support_bot",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

@dp.message(Command('contacts'))
async def cmd_contacts(message: types.Message):
    """Контакты"""    await message.answer(
        "📞 <b>Контакты</b>\n\n"
        "📍 <b>Адрес:</b>\n"
        "г. Москва, ул. Примерная, д. 1\n\n"
        "📱 <b>Телефон:</b>\n"
        "+7 (999) 123-45-67\n\n"
        "📧 <b>Email:</b>\n"
        "info@fooddelivery.com\n\n"
        "⏰ <b>Режим работы:</b>\n"
        "Ежедневно с 10:00 до 23:00",
        parse_mode='HTML'
    )

@dp.message(Command('profile'))
async def cmd_profile(message: types.Message):
    """Профиль пользователя"""
    await message.answer(
        f"👤 <b>Ваш профиль</b>\n\n"
        f"👋 Имя: <b>{message.from_user.first_name}</b>\n"
        f"📱 Username: <code>@{message.from_user.username or 'Не указан'}</code>\n"
        f"🆔 ID: <code>{message.from_user.id}</code>\n\n"
        f"📊 <b>Ваша статистика:</b>\n"
        f"📦 Заказов: 0\n"
        f"⭐ Бонусов: 0",
        parse_mode='HTML'
    )

@dp.message()
async def handle_messages(message: types.Message):
    """Обработка текстовых сообщений"""
    text = message.text
    
    # Ответы на кнопки
    if text == "📱 Открыть меню":
        await message.answer(
            "🍔 <b>Меню открыто!</b>\n\n"
            f"Нажмите на кнопку выше или введите /menu",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    
    elif text == "👤 Мой профиль":
        await cmd_profile(message)
    
    elif text == "📞 Контакты":
        await cmd_contacts(message)
    
    elif text == "❓ Помощь":
        await cmd_help(message)
        elif text == "📊 Статистика":
        if message.from_user.id == ADMIN_ID or ADMIN_ID == 0:
            await cmd_stats(message)
        else:
            await message.answer("❌ Только для админа!")
    
    elif text == "📦 Заказы":
        if message.from_user.id == ADMIN_ID or ADMIN_ID == 0:
            await message.answer("📦 <b>Заказы</b>\n\nФункция в разработке...")
        else:
            await message.answer("❌ Только для админа!")
    
    elif text == "🍽️ Меню":
        if message.from_user.id == ADMIN_ID or ADMIN_ID == 0:
            await message.answer("🍽️ <b>Меню</b>\n\nФункция в разработке...")
        else:
            await message.answer("❌ Только для админа!")
    
    elif text == "🔙 Главное меню":
        await cmd_start(message)
    
    else:
        # Эхо для неизвестных команд
        await message.answer(
            f"🤔 <b>Я не понял команду</b>\n\n"
            f"Вы написали: <code>{text}</code>\n\n"
            f"Воспользуйтесь меню или введите /help",
            parse_mode='HTML'
        )

# ==================== ЗАПУСК ====================

async def main():
    """Главная функция запуска"""
    print("=" * 50)
    print("🚀 Food Delivery Bot запускается...")
    print("=" * 50)
    print(f"🤖 Токен: {BOT_TOKEN[:20]}...")  # Показываем только первые 20 символов
    print(f"👤 Admin ID: {ADMIN_ID}")
    print(f"🔑 Admin Password: {ADMIN_PASSWORD}")
    print(f"📱 WebApp URL: {WEBAPP_URL}")
    print("=" * 50)
    
    # Инициализация БД
    init_db()
    
    # Получаем информацию о боте
    bot_info = await bot.get_me()
    print(f"✅ Бот запущен! @{bot_info.username}")
    print("=" * 50)    print("📌 Для остановки нажмите Ctrl+C")
    print("=" * 50)
    
    # Запускаем polling
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())