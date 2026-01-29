import os
import telebot
from telebot import types
import sqlite3
import datetime
import logging
from flask import Flask, request
import time

# ========== КОНФИГУРАЦИЯ ==========
TOKEN = os.environ.get("BOT_TOKEN", "8496935356:AAEB6niHyvdSUJCsOETT5kQb-PAWwHhCvrs")
ADMIN_CHAT_ID = "787419978"
GROUP_CHAT_ID = "-5275786758"

# ========== ИНИЦИАЛИЗАЦИЯ ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Переменные состояния
user_data = {}

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect('orders.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT, telegram TEXT, phone TEXT, 
                  wedding_date TEXT, created_date TIMESTAMP,
                  consent INTEGER DEFAULT 0, user_id INTEGER)''')
    conn.commit()
    conn.close()
    logger.info("✅ База данных готова")

# ========== ВЕБ-ХУК ДЛЯ TELEGRAM ==========
@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    """Принимаем обновления от Telegram"""
    if request.headers.get('content-type') == 'application/json':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return ''
        except Exception as e:
            logger.error(f"❌ Ошибка webhook: {e}")
            return 'Error', 500
    return 'Bad request', 400

# ========== ОСНОВНЫЕ ФУНКЦИИ ==========
def send_order_notification(order_data):
    """Отправляет заявку вам и в группу"""
    try:
        message = f"""🎯 НОВЫЙ ЗАКАЗ САЙТА!

👤 Имя: {order_data['name']}
📱 Телефон: {order_data['phone']}
📲 Telegram: {order_data['telegram']}
📅 Год свадьбы: {order_data['wedding_date']}
🆔 Username: @{order_data.get('username', 'нет')}
🆔 User ID: {order_data['user_id']}
⏰ Время: {datetime.datetime.now().strftime('%H:%M %d.%m.%Y')}

#заказсайт"""
        
        bot.send_message(ADMIN_CHAT_ID, message)
        bot.send_message(GROUP_CHAT_ID, message)
        logger.info("✅ Заявка отправлена")
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки: {e}")

def show_main_menu(chat_id):
    """Показывает главное меню"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('🎯 Заказать сайт'),
        types.KeyboardButton('🔒 Политика'),
        types.KeyboardButton('✨ Примеры работ'),
        types.KeyboardButton('💰 Стоимость')
    )
    bot.send_message(chat_id, "Выберите действие:", reply_markup=markup)

# ========== ОБРАБОТЧИКИ СООБЩЕНИЙ ==========
@bot.message_handler(commands=['start', 'menu'])
def start_command(message):
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    logger.info(f"👤 Пользователь {user_id} начал")
    
    if user_id in user_data:
        del user_data[user_id]
    
    show_main_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == '🎯 Заказать сайт')
def order_button(message):
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    user_data[user_id] = {'step': 'name'}
    
    bot.send_message(
        message.chat.id,
        "📋 Введите ваше имя и фамилию:",
        reply_markup=types.ReplyKeyboardRemove()
    )

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    
    if user_id in user_data:
        session = user_data[user_id]
        step = session.get('step')
        
        if step == 'name':
            session['name'] = message.text
            session['step'] = 'phone'
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton('📱 Поделиться телефоном', request_contact=True))
            
            bot.send_message(
                message.chat.id,
                f"👤 Имя: {message.text}\n\n📱 Нажмите кнопку для телефона:",
                reply_markup=markup
            )
        
        elif step == 'phone':
            if hasattr(message, 'contact') and message.contact:
                session['phone'] = message.contact.phone_number
            else:
                session['phone'] = message.text
            
            session['step'] = 'telegram'
            
            bot.send_message(
                message.chat.id,
                f"📱 Телефон: {session['phone']}\n\n📲 Введите Telegram:",
                reply_markup=types.ReplyKeyboardRemove()
            )
        
        elif step == 'telegram':
            telegram = message.text
            if not telegram.startswith('@'):
                telegram = f"@{telegram}"
            session['telegram'] = telegram
            session['step'] = 'date'
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add('2025', '2026', '2027', '2028')
            
            bot.send_message(
                message.chat.id,
                f"📲 Telegram: {telegram}\n\n📅 Выберите год свадьбы:",
                reply_markup=markup
            )
        
        elif step == 'date':
            session['date'] = message.text
            
            # Отправляем заявку
            send_order_notification({
                'name': session['name'],
                'phone': session['phone'],
                'telegram': session['telegram'],
                'wedding_date': session['date'],
                'user_id': user_id,
                'username': message.from_user.username
            })
            
            # Ответ пользователю
            bot.send_message(
                message.chat.id,
                f"🎉 {session['name']}, заявка принята! Свяжусь в течение 24 часов.",
                reply_markup=types.ReplyKeyboardRemove()
            )
            
            # Очищаем и показываем меню
            del user_data[user_id]
            show_main_menu(message.chat.id)
    
    else:
        show_main_menu(message.chat.id)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if message.chat.type != 'private':
        return
    
    user_id = message.from_user.id
    if user_id in user_data and user_data[user_id].get('step') == 'phone':
        user_data[user_id]['phone'] = message.contact.phone_number
        user_data[user_id]['step'] = 'telegram'
        
        bot.send_message(
            message.chat.id,
            f"📱 Телефон: {message.contact.phone_number}\n\n📲 Введите Telegram:",
            reply_markup=types.ReplyKeyboardRemove()
        )

@bot.message_handler(func=lambda m: m.text in ['🔒 Политика', '✨ Примеры работ', '💰 Стоимость'])
def menu_buttons(message):
    if message.text == '🔒 Политика':
        bot.send_message(message.chat.id, "🔒 Политика конфиденциальности...")
    elif message.text == '✨ Примеры работ':
        bot.send_message(message.chat.id, "✨ Примеры работ...")
    elif message.text == '💰 Стоимость':
        bot.send_message(message.chat.id, "💰 Стоимость...")
    
    show_main_menu(message.chat.id)

# ========== FLASK РОУТЫ ==========
@app.route('/')
def home():
    return """
    <html>
        <head><title>Wedding Bot</title></head>
        <body style="text-align:center;padding:50px;">
            <h1>🤵👰 Wedding Bot</h1>
            <p style="color:green;font-size:24px;">✅ Бот работает через веб-хук!</p>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return 'OK', 200

# ========== НАСТРОЙКА ВЕБ-ХУКА ==========
def setup_webhook():
    """Настраивает веб-хук при запуске"""
    try:
        # Удаляем старый веб-хук
        bot.remove_webhook()
        time.sleep(1)
        
        # Получаем URL сервиса
        service_name = os.environ.get('RENDER_SERVICE_NAME', 'wedding-site-bot')
        webhook_url = f"https://{service_name}.onrender.com/webhook/{TOKEN}"
        
        # Устанавливаем новый веб-хук
        bot.set_webhook(url=webhook_url)
        logger.info(f"✅ Веб-хук установлен: {webhook_url}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка веб-хука: {e}")

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    logger.info("🚀 Запуск бота с веб-хуками...")
    logger.info(f"🤖 Токен: {TOKEN[:10]}...")
    logger.info(f"👑 Админ: {ADMIN_CHAT_ID}")
    logger.info(f"👥 Группа: {GROUP_CHAT_ID}")
    
    init_db()
    
    # Настраиваем веб-хук
    setup_webhook()
    
    # Запускаем Flask
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🌐 Запуск Flask на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
