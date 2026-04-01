import asyncio
import json
import sqlite3
import os
import base64
from datetime import datetime
from functools import wraps
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo
from flask import Flask, jsonify, request, make_response
import threading

# --- FLASK APP ---
app = Flask(__name__)

# 🔐 Админский пароль (измени на свой!)
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

# --- AUTH DECORATOR ---
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if not auth:
            return jsonify({'error': 'No authorization'}), 401
        
        try:
            token = auth.split(' ')[1]
            decoded = base64.b64decode(token).decode('utf-8')
            if decoded != ADMIN_PASSWORD:
                return jsonify({'error': 'Invalid password'}), 403
        except:
            return jsonify({'error': 'Invalid authorization'}), 401
        
        return f(*args, **kwargs)
    return decorated

# --- DATABASE ---
def get_db():
    conn = sqlite3.connect('food.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Таблица блюд
    c.execute('''CREATE TABLE IF NOT EXISTS dishes (        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        price INTEGER NOT NULL,
        category TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Таблица заказов
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        items TEXT NOT NULL,
        total_amount INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Проверяем есть ли данные
    c.execute('SELECT COUNT(*) FROM dishes')
    if c.fetchone()[0] == 0:
        dishes = [
            (1, 'Пицца Пепперони', 'Острая пицца с пепперони, моцареллой и томатным соусом', 450, 'pizza'),
            (2, 'Пицца Маргарита', 'Классическая пицца с томатами, моцареллой и базиликом', 390, 'pizza'),
            (3, 'Бургер Чиз', 'Сочная говяжья котлета, сыр чеддер, свежие овощи', 350, 'burgers'),
            (4, 'Суши Филадельфия', 'Лосось, сливочный сыр, огурец, авокадо', 520, 'sushi'),
            (5, 'Ролл Калифорния', 'Краб, икра тобико, огурец, майонез', 380, 'sushi'),
            (6, 'Паста Карбонара', 'Бекон, яйцо, пармезан, сливки', 420, 'pasta'),
            (7, 'Салат Цезарь', 'Курица, пармезан, сухарики, соус цезарь', 380, 'salads'),
            (8, 'Кола 0.5л', 'Газированный напиток', 120, 'drinks'),
        ]
        c.executemany('INSERT INTO dishes (id, name, description, price, category) VALUES (?,?,?,?,?)', dishes)
        print("✅ База данных инициализирована")
    
    conn.commit()
    conn.close()

# --- CORS ---
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

# --- PUBLIC API ---
@app.route('/')
def home():
    return jsonify({        "status": "ok",
        "service": "Food Delivery API",
        "version": "2.0 PRO",
        "endpoints": {
            "dishes": "/api/dishes",
            "categories": "/api/categories",
            "order": "/api/order (POST)",
            "admin": "/admin (требуется авторизация)"
        }
    })

@app.route('/api/categories')
def get_categories():
    categories = [
        {'id': 'pizza', 'name': '🍕 Пицца'},
        {'id': 'burgers', 'name': '🍔 Бургеры'},
        {'id': 'sushi', 'name': '🍣 Суши'},
        {'id': 'pasta', 'name': '🍝 Паста'},
        {'id': 'salads', 'name': '🥗 Салаты'},
        {'id': 'drinks', 'name': '🥤 Напитки'}
    ]
    return jsonify(categories)

@app.route('/api/dishes')
def get_dishes():
    try:
        cat = request.args.get('category')
        conn = get_db()
        c = conn.cursor()
        
        if cat and cat != 'all':
            c.execute('SELECT * FROM dishes WHERE category = ?', (cat,))
        else:
            c.execute('SELECT * FROM dishes')
        
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        print(f"❌ Error get_dishes: {e}")
        return jsonify([]), 500

@app.route('/api/order', methods=['POST'])
def create_order():
    try:
        data = request.json
        user_id = data.get('user_id', 0)
        username = data.get('username', 'unknown')
        items = data.get('items', [])
        total = data.get('total', 0)        
        if not items or total <= 0:
            return jsonify({'success': False, 'error': 'Invalid data'}), 400
        
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO orders (user_id, username, items, total_amount, status)
            VALUES (?, ?, ?, ?, 'pending')
        ''', (user_id, username, json.dumps(items), total))
        
        order_id = c.lastrowid
        conn.commit()
        conn.close()
        
        print(f"📦 Новый заказ #{order_id} на {total} ₽")
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'message': 'Заказ создан'
        })
    except Exception as e:
        print(f"❌ Error create_order: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# --- ADMIN API ---
@app.route('/admin/orders')
@require_auth
def admin_get_orders():
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM orders ORDER BY created_at DESC LIMIT 50')
        rows = c.fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/order/<int:order_id>/status', methods=['PUT'])
@require_auth
def admin_update_order_status(order_id):
    try:
        data = request.json
        status = data.get('status', 'pending')
        
        if status not in ['pending', 'completed', 'cancelled']:
            return jsonify({'error': 'Invalid status'}), 400
                conn = get_db()
        c = conn.cursor()
        c.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/dish', methods=['POST'])
@require_auth
def admin_add_dish():
    try:
        data = request.json
        name = data.get('name')
        description = data.get('description', '')
        price = data.get('price', 0)
        category = data.get('category', 'pizza')
        
        if not name or price <= 0:
            return jsonify({'error': 'Invalid data'}), 400
        
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO dishes (name, description, price, category)
            VALUES (?, ?, ?, ?)
        ''', (name, description, price, category))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Блюдо добавлено'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/dish/<int:dish_id>', methods=['DELETE'])
@require_auth
def admin_delete_dish(dish_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM dishes WHERE id = ?', (dish_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/admin/dish/<int:dish_id>', methods=['PUT'])
@require_auth
def admin_update_dish(dish_id):
    try:
        data = request.json
        name = data.get('name')
        description = data.get('description')
        price = data.get('price')
        category = data.get('category')
        
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            UPDATE dishes 
            SET name=?, description=?, price=?, category=?
            WHERE id=?
        ''', (name, description, price, category, dish_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- ADMIN HTML PAGE ---
@app.route('/admin')
def admin_page():
    return app.send_static_file('admin.html') if os.path.exists('admin.html') else jsonify({'error': 'Admin page not found'}), 404

# --- TELEGRAM BOT ---
bot_token = os.getenv('BOT_TOKEN')
if not bot_token:
    raise ValueError("❌ No BOT_TOKEN in environment variables!")

bot = Bot(token=bot_token)
dp = Dispatcher()

# URL Mini App на GitHub Pages
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://cekarinzahar44-del.github.io/food-delivery/')
ADMIN_URL = os.getenv('ADMIN_URL', 'https://bot-xxxx.bothost.tech/admin')

print(f"🔗 WEBAPP_URL: {WEBAPP_URL}")
print(f"🔗 ADMIN_URL: {ADMIN_URL}")

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    kb = [
        [types.KeyboardButton(text="📱 Открыть меню", web_app=WebAppInfo(url=WEBAPP_URL))],
        [types.KeyboardButton(text="👤 Мой профиль")]    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(
        f"🍔 <b>Добро пожаловать в Food Delivery!</b>\n\n"
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        f"У нас вы можете заказать:\n"
        f"🍕 Пиццу\n🍔 Бургеры\n🍣 Суши\n🍝 Пасту\n🥗 Салаты\n🥤 Напитки\n\n"
        f"Жмите кнопку ниже, чтобы сделать заказ:",
        reply_markup=keyboard,
        parse_mode='HTML'
    )

@dp.message(Command('admin'))
async def cmd_admin(message: types.Message):
    # Простая проверка (в продакшене используйте proper auth)
    admin_ids = [int(os.getenv('ADMIN_ID', 0))]  # ID админа в Telegram
    if message.from_user.id not in admin_ids and admin_ids[0] != 0:
        await message.answer("❌ Доступ запрещён")
        return
    
    await message.answer(
        f"🔐 <b>Админ-панель</b>\n\n"
        f"Откройте в браузере:\n"
        f"<code>{ADMIN_URL}</code>\n\n"
        f"Пароль: <code>{ADMIN_PASSWORD}</code>",
        parse_mode='HTML'
    )

@dp.message(Command('help'))
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 <b>Помощь</b>\n\n"
        "Команды:\n"
        "/start - Открыть меню\n"
        "/admin - Админ-панель (для владельца)\n"
        "/help - Эта справка\n\n"
        "Или нажмите кнопку 📱 Открыть меню",
        parse_mode='HTML'
    )

@dp.message()
async def handle_message(message: types.Message):
    if message.web_app_data:
        try:
            data = json.loads(message.web_app_data.data)
            if data.get('action') == 'order_created':
                total = data.get('total', 0)
                items = data.get('items', [])
                                items_text = '\n'.join([f"• {i['name']} x{i['qty']} = {i['price']*i['qty']} ₽" for i in items])
                
                # Ответ клиенту
                await message.answer(
                    f"✅ <b>Заказ принят!</b>\n\n"
                    f"<b>Состав:</b>\n{items_text}\n\n"
                    f"<b>Итого:</b> {total} ₽\n\n"
                    f"Менеджер скоро свяжется с вами для подтверждения!",
                    parse_mode='HTML'
                )
                
                # Уведомление админу
                admin_id = os.getenv('ADMIN_ID')
                if admin_id:
                    try:
                        await bot.send_message(
                            int(admin_id),
                            f"🔔 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
                            f"Клиент: @{message.from_user.username or 'N/A'}\n"
                            f"Сумма: {total} ₽\n\n"
                            f"Проверьте админ-панель для деталей.",
                            parse_mode='HTML'
                        )
                    except:
                        pass
        except Exception as e:
            print(f"Error parsing webapp data: {e}")

async def main():
    # Запуск Flask в фоне
    def run_flask():
        init_db()
        print("📡 Flask сервер запущен на порту 5000...")
        app.run(host='0.0.0.0', port=5000, debug=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    await asyncio.sleep(2)
    
    bot_info = await bot.get_me()
    print(f"🚀 Бот запущен! @{bot_info.username}")
    print(f"📱 Mini App: {WEBAPP_URL}")
    print(f"🔐 Admin Panel: {ADMIN_URL}")
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
