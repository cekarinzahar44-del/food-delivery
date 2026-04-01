import asyncio
import json
import sqlite3
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo
from flask import Flask, jsonify, request
import threading

# ===== FLASK СЕРВЕР (API) =====
app = Flask(__name__)

# CORS для GitHub Pages
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

def init_db():
    """Инициализация базы данных с тестовыми блюдами"""
    conn = sqlite3.connect('food.db')
    cursor = conn.cursor()
    
    # Создаем таблицу блюд
    cursor.execute('''CREATE TABLE IF NOT EXISTS dishes (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        price INTEGER NOT NULL,
        category TEXT NOT NULL
    )''')
    
    # Проверяем, есть ли уже данные
    cursor.execute('SELECT COUNT(*) FROM dishes')
    if cursor.fetchone()[0] == 0:
        # Добавляем тестовые блюда
        dishes = [
            (1, 'Пицца Пепперони', 'Острая пицца с пепперони, моцареллой и томатным соусом', 450, 'pizza'),
            (2, 'Пицца Маргарита', 'Классическая пицца с томатами, моцареллой и свежим базиликом', 390, 'pizza'),
            (3, 'Бургер Чиз', 'Сочная говяжья котлета, сыр чеддер, свежие овощи, фирменный соус', 350, 'burgers'),
            (4, 'Суши Филадельфия', 'Свежий лосось, сливочный сыр, огурец, авокадо', 520, 'sushi'),
            (5, 'Ролл Калифорния', 'Краб, икра тобико, огурец, майонез', 380, 'sushi'),
            (6, 'Паста Карбонара', 'Спагетти с беконом, яйцом, пармезаном и сливками', 420, 'pasta'),
            (7, 'Салат Цезарь', 'Салат ромэн, куриная грудка, пармезан, сухарики, соус цезарь', 380, 'salads'),
            (8, 'Кола 0.5л', 'Газированный напиток Coca-Cola', 120, 'drinks'),
        ]
        cursor.executemany('INSERT INTO dishes VALUES (?,?,?,?,?)', dishes)        print("✅ База данных заполнена тестовыми блюдами")
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    """Главная страница API"""
    return jsonify({
        'status': 'ok',
        'message': 'Food Delivery API is running',
        'endpoints': {
            'dishes': '/api/dishes',
            'categories': '/api/categories',
            'order': '/api/order (POST)'
        }
    })

@app.route('/api/dishes')
def get_dishes():
    """Получить все блюда или по категории"""
    try:
        category = request.args.get('category')
        conn = sqlite3.connect('food.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if category and category != 'all':
            cursor.execute('SELECT * FROM dishes WHERE category=?', (category,))
        else:
            cursor.execute('SELECT * FROM dishes')
        
        dishes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(dishes)
    except Exception as e:
        print(f"❌ Ошибка get_dishes: {e}")
        return jsonify([]), 500

@app.route('/api/categories')
def get_categories():
    """Получить список категорий"""
    categories = ['pizza', 'burgers', 'sushi', 'pasta', 'salads', 'drinks']
    return jsonify(categories)

@app.route('/api/order', methods=['POST'])
def create_order():
    """Создать заказ"""
    try:
        data = request.json        print(f"📦 Новый заказ: {data}")
        
        # Здесь можно сохранить заказ в базу данных
        # Для демо просто возвращаем успех
        
        return jsonify({
            'success': True,
            'order_id': 1,
            'message': 'Заказ создан'
        })
    except Exception as e:
        print(f"❌ Ошибка create_order: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ===== TELEGRAM БОТ =====
bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher()

# URL Mini App на GitHub Pages
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://cekarinzahar44-del.github.io/food-delivery/')

print(f"🔗 WEBAPP_URL: {WEBAPP_URL}")

@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    """Обработка команды /start"""
    await message.answer(
        '🍔 <b>Добро пожаловать в Food Delivery!</b>\n\n'
        'У нас вы можете заказать:\n'
        '🍕 Пиццу\n'
        '🍔 Бургеры\n'
        '🍣 Суши и роллы\n'
        '🍝 Пасту\n'
        '🥗 Салаты\n'
        '🥤 Напитки\n\n'
        'Нажмите кнопку ниже, чтобы открыть меню:',
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text='📱 Открыть меню', web_app=WebAppInfo(url=WEBAPP_URL))]],
            resize_keyboard=True
        ),
        parse_mode='HTML'
    )

@dp.message(Command('menu'))
async def cmd_menu(message: types.Message):
    """Обработка команды /menu"""
    await cmd_start(message)

@dp.message(Command('help'))
async def cmd_help(message: types.Message):    """Обработка команды /help"""
    await message.answer(
        '📖 <b>Помощь</b>\n\n'
        'Доступные команды:\n'
        '/start - Запустить бота и открыть меню\n'
        '/menu - Открыть меню\n'
        '/help - Эта справка\n\n'
        'Или нажмите кнопку "📱 Открыть меню"'
    )

@dp.message()
async def handle_webapp(message: types.Message):
    """Обработка данных из Mini App"""
    if message.web_app_data:
        try:
            data = json.loads(message.web_app_data.data)
            print(f"📨 Данные из Mini App: {data}")
            
            if data.get('action') == 'order_created':
                order_id = data.get('order_id', 1)
                items = data.get('items', [])
                total = data.get('total', 0)
                
                # Формируем текст заказа
                items_text = '\n'.join([f"• {item['name']} x{item['qty']} - {item['price']*item['qty']} ₽" for item in items])
                
                await message.answer(
                    f'✅ <b>Заказ #{order_id} принят!</b>\n\n'
                    f'<b>Состав заказа:</b>\n{items_text}\n\n'
                    f'<b>Итого:</b> {total} ₽\n\n'
                    f'Мы скоро свяжемся с вами для подтверждения!',
                    parse_mode='HTML'
                )
        except Exception as e:
            print(f"❌ Ошибка обработки webapp_data: {e}")

async def main():
    """Основная функция запуска"""
    print("🚀 Запуск Food Delivery App...")
    
    # Запуск Flask в фоновом режиме
    def run_flask():
        init_db()
        print("📡 Запуск Flask сервера на порту 5000...")
        app.run(host='0.0.0.0', port=5000, debug=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Небольшая задержка перед запуском бота    await asyncio.sleep(2)
    
    print("🤖 Запуск Telegram бота...")
    print(f"✅ Бот запущен! Откройте @{(await bot.get_me()).username}")
    
    # Запуск бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
