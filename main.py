# 📄 **ПОЛНЫЙ РАБОЧИЙ `main.py`**

**Копируй ВСЁ от начала до конца:**

```python
import os
import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask, jsonify
import threading

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://cekarinzahar44-del.github.io/food-delivery/')

if not BOT_TOKEN:
    raise ValueError("❌ ОШИБКА: Не найден BOT_TOKEN!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
app = Flask(__name__)
BOT_USERNAME = "unknown"

@app.route('/')
def index():
    return jsonify({'status': 'ok', 'service': 'Food Delivery API', 'bot': f'@{BOT_USERNAME}'})

@app.route('/api/health')
def health():
    return jsonify({'status': 'healthy', 'port': 5000})

def init_db():
    conn = sqlite3.connect('food.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, username TEXT, first_name TEXT, items TEXT, total_amount INTEGER, status TEXT DEFAULT "pending", created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    cursor.execute('CREATE TABLE IF NOT EXISTS dishes (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER, category TEXT)')
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def get_main_keyboard():
    keyboard = [[KeyboardButton(text="📱 Открыть меню", web_app=WebAppInfo(url=WEBAPP_URL))], [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="📞 Контакты")], [KeyboardButton(text="❓ Помощь")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_admin_keyboard():
    keyboard = [[KeyboardButton(text="📊 Статистика")], [KeyboardButton(text="📦 Заказы"), KeyboardButton(text="🍽️ Меню")], [KeyboardButton(text="🔙 Главное меню")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.answer(f"🍔 <b>Добро пожаловать в Food Delivery!</b>\n\n👋 Привет, <b>{message.from_user.first_name}</b>!\n\n📱 У нас вы можете заказать:\n• 🍕 Пиццу\n• 🍔 Бургеры\n• 🍣 Суши\n• 🍝 Пасту\n• 🥗 Салаты\n• 🥤 Напитки\n\n🚀 <b>Нажмите кнопку ниже!</b>", reply_markup=get_main_keyboard(), parse_mode='HTML')
    if ADMIN_ID != 0:
        try:
            await bot.send_message(ADMIN_ID, f"🔔 Новый пользователь: {message.from_user.first_name} (@{message.from_user.username or 'N/A'})")
        except:
            pass

@dp.message(Command('menu'))
async def cmd_menu(message: types.Message):
    await message.answer("📱 <b>Открываю меню...</b>", reply_markup=get_main_keyboard(), parse_mode='HTML')

@dp.message(Command('admin'))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID and ADMIN_ID != 0:
        await message.answer("❌ <b>Доступ запрещён!</b>", parse_mode='HTML')
        return
    await message.answer(f"🔐 <b>Админ-панель</b>\n\n👋 Привет, владелец!\n\n🔑 <b>Пароль:</b> <code>{ADMIN_PASSWORD}</code>", reply_markup=get_admin_keyboard(), parse_mode='HTML')

@dp.message(Command('stats'))
async def cmd_stats(message: types.Message):
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
    await message.answer(f"📊 <b>Статистика</b>\n\n📦 Всего заказов: <b>{total_orders}</b>\n⏳ В обработке: <b>{pending_orders}</b>\n💰 Выручка: <b>{revenue} ₽</b>\n\n📈 Бот работает! ✅", parse_mode='HTML')

@dp.message(Command('help'))
async def cmd_help(message: types.Message):
    await message.answer("📖 <b>Помощь</b>\n\n📱 <b>Команды:</b>\n/start - Главное меню\n/menu - Открыть меню\n/admin - Админ-панель\n/stats - Статистика\n/help - Эта справка", reply_markup=get_main_keyboard(), parse_mode='HTML')

@dp.message()
async def handle_messages(message: types.Message):
    text = message.text
    if text == "📱 Открыть меню":
        await message.answer("🍔 <b>Меню открыто!</b>", reply_markup=get_main_keyboard(), parse_mode='HTML')
    elif text == "👤 Мой профиль":
        await message.answer(f"👤 <b>Ваш профиль</b>\n\nИмя: {message.from_user.first_name}\nID: {message.from_user.id}", parse_mode='HTML')
    elif text == "📞 Контакты":
        await message.answer("📞 <b>Контакты</b>\n\n📱 +7 (999) 123-45-67\n📧 info@fooddelivery.com", parse_mode='HTML')
    elif text == "❓ Помощь":
        await cmd_help(message)
    elif text == "📊 Статистика":
        if message.from_user.id == ADMIN_ID or ADMIN_ID == 0:
            await cmd_stats(message)
    elif text == "🔙 Главное меню":
        await cmd_start(message)
    else:
        await message.answer("🤔 Воспользуйтесь меню или введите /help")

async def main():
    global BOT_USERNAME
    print("=" * 50)
    print("🚀 Food Delivery Bot запускается...")
    print("=" * 50)
    print(f"🤖 Токен: {BOT_TOKEN[:20]}...")
    print(f"👤 Admin ID: {ADMIN_ID}")
    print(f"📱 WebApp URL: {WEBAPP_URL}")
    print(f"🌐 Flask сервер: http://0.0.0.0:5000")
    print("=" * 50)
    init_db()
    bot_info = await bot.get_me()
    BOT_USERNAME = bot_info.username
    print(f"✅ Бот: @{BOT_USERNAME}")
    def run_flask():
        app.run(host='0.0.0.0', port=5000, debug=False)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("✅ Flask сервер запущен!")
    print("=" * 50)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
