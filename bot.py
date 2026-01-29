import os
import telebot
from telebot import types
import sqlite3
import datetime
import logging
from flask import Flask, request
import time
import threading
import requests

# ========== КОНФИГУРАЦИЯ ==========
TOKEN = os.environ.get("BOT_TOKEN", "8496935356:AAEB6niHyvdSUJCsOETT5kQb-PAWwHhCvrs")
ADMIN_CHAT_ID = "787419978"
GROUP_CHAT_ID = "-5275786758"
WEBSITE_URL = "https://annasultanova29-spec.github.io/wedding-site-89/"
SERVICE_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://your-bot-name.onrender.com")

# Настройка таймаутов для Telegram
telebot.apihelper.READ_TIMEOUT = 5  # Секунд
telebot.apihelper.CONNECT_TIMEOUT = 3  # Секунд

# ========== ИНИЦИАЛИЗАЦИЯ ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN, threaded=False)  # Отключаем многопоточность
app = Flask(__name__)

# Простая in-memory база (лучше для Render)
user_data = {}
orders = []

# ========== KEEP-ALIVE ФУНКЦИЯ ==========
def keep_render_awake():
    """Отправляет запросы каждые 5 минут чтобы Render не спал"""
    while True:
        try:
            response = requests.get(f"{SERVICE_URL}/health", timeout=10)
            logger.info(f"🔄 Keep-alive sent: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Keep-alive failed: {e}")
        time.sleep(300)  # 5 минут

# ========== ВЕБ-ХУК ДЛЯ TELEGRAM ==========
@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    """Принимаем обновления от Telegram"""
    try:
        if request.headers.get('content-type') == 'application/json':
            json_string = request.get_data(as_text=True)
            update = telebot.types.Update.de_json(json_string)
            
            # Быстрая обработка в отдельном потоке
            def process_update():
                try:
                    bot.process_new_updates([update])
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки: {e}")
            
            threading.Thread(target=process_update).start()
            
            # Немедленно отвечаем Telegram (важно!)
            return '', 200
            
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
    
    return '', 200  # Всегда возвращаем 200 чтобы Telegram не повторял

# ========== ОСНОВНЫЕ ФУНКЦИИ ==========
def send_quick_message(chat_id, text):
    """Быстрая отправка сообщения с таймаутом"""
    try:
        bot.send_message(chat_id, text, timeout=3)
        return True
    except Exception as e:
        logger.error(f"❌ Send message error: {e}")
        return False

def show_main_menu(chat_id):
    """Показывает главное меню"""
    try:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton('🎯 Заказать сайт'),
            types.KeyboardButton('🔒 Политика'),
            types.KeyboardButton('✨ Примеры работ'),
            types.KeyboardButton('💰 Стоимость'),
            types.KeyboardButton('🌐 Наш сайт')
        )
        bot.send_message(chat_id, "Выберите действие:", reply_markup=markup, timeout=3)
    except Exception as e:
        logger.error(f"❌ Menu error: {e}")

# ========== ОБРАБОТЧИКИ (УПРОЩЕННЫЕ ДЛЯ НАДЕЖНОСТИ) ==========
@bot.message_handler(commands=['start', 'menu'])
def start_command(message):
    """Обработчик старта"""
    try:
        if message.chat.type != 'private':
            return
        
        user_id = message.from_user.id
        logger.info(f"👤 Start from {user_id}")
        
        # Очищаем старые данные
        if user_id in user_data:
            del user_data[user_id]
        
        welcome = "🤵👰 Добро пожаловать! Я помогу создать свадебный сайт.\n\nВыберите действие:"
        send_quick_message(message.chat.id, welcome)
        time.sleep(0.5)
        show_main_menu(message.chat.id)
        
    except Exception as e:
        logger.error(f"❌ Start error: {e}")

@bot.message_handler(func=lambda m: m.text == '🎯 Заказать сайт')
def order_button(message):
    """Начало заказа"""
    try:
        user_id = message.from_user.id
        user_data[user_id] = {'step': 'name', 'user_id': user_id}
        
        bot.send_message(
            message.chat.id,
            "📋 Введите ваше имя и фамилию:",
            reply_markup=types.ReplyKeyboardRemove(),
            timeout=3
        )
    except Exception as e:
        logger.error(f"❌ Order button error: {e}")

@bot.message_handler(func=lambda m: m.text in ['🌐 Наш сайт', '✨ Примеры работ', '💰 Стоимость', '🔒 Политика'])
def handle_menu_buttons(message):
    """Обработчик всех кнопок меню"""
    try:
        text = message.text
        
        if text == '🌐 Наш сайт':
            response = f"🌐 Наш свадебный сайт:\n\n{WEBSITE_URL}\n\nНажмите на ссылку чтобы посмотреть!"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🌐 Открыть сайт", url=WEBSITE_URL))
            bot.send_message(message.chat.id, response, reply_markup=markup, timeout=3)
            
        elif text == '✨ Примеры работ':
            response = "✨ Примеры свадебных сайтов:\n\n1. Классический стиль с золотом\n2. Современный минимализм\n3. Романтический с цветами\n\n🌐 Смотрите пример: " + WEBSITE_URL
            bot.send_message(message.chat.id, response, timeout=3)
            
        elif text == '💰 Стоимость':
            response = """💰 Стоимость:
            
🎯 Базовый - 5 000 руб.
🎯 Стандарт - 8 000 руб.  
🎯 Премиум - 12 000 руб.

Все пакеты включают адаптивный дизайн, галерею и поддержку."""
            bot.send_message(message.chat.id, response, timeout=3)
            
        elif text == '🔒 Политика':
            response = "🔒 Ваши данные защищены и используются только для связи. Не передаются третьим лицам."
            bot.send_message(message.chat.id, response, timeout=3)
        
        # Показываем меню снова
        time.sleep(0.5)
        show_main_menu(message.chat.id)
        
    except Exception as e:
        logger.error(f"❌ Menu button error: {e}")

# Обработчик остальных сообщений (оставьте ваш текущий, но добавьте try-except)

# ========== FLASK РОУТЫ ==========
@app.route('/')
def home():
    return """
    <html>
        <head><title>Wedding Bot</title>
        <meta http-equiv="refresh" content="300">
        </head>
        <body style="text-align:center;padding:50px;">
            <h1>🤵👰 Wedding Bot</h1>
            <p style="color:green;font-size:24px;">✅ Бот работает!</p>
            <p>Последняя активность: """ + datetime.datetime.now().strftime("%H:%M:%S") + """</p>
        </body>
    </html>
    """

@app.route('/health')
def health():
    """Для keep-alive"""
    return 'OK', 200

@app.route('/status')
def status():
    """Статус бота"""
    return {
        'status': 'active',
        'users': len(user_data),
        'orders': len(orders),
        'timestamp': datetime.datetime.now().isoformat()
    }, 200

# ========== НАСТРОЙКА ВЕБ-ХУКА ==========
def setup_webhook():
    """Настраивает веб-хук один раз при запуске"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 Настройка веб-хука, попытка {attempt+1}")
            
            # Удаляем старый веб-хук
            bot.remove_webhook()
            time.sleep(1)
            
            # Устанавливаем новый
            webhook_url = f"{SERVICE_URL}/webhook/{TOKEN}"
            bot.set_webhook(url=webhook_url, timeout=10)
            
            logger.info(f"✅ Веб-хук установлен: {webhook_url}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка веб-хука (попытка {attempt+1}): {e}")
            time.sleep(2)
    
    logger.error("❌ Не удалось установить веб-хук после всех попыток")
    return False

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    logger.info("🚀 Запуск оптимизированного бота...")
    logger.info(f"🌐 Сервис: {SERVICE_URL}")
    
    # Запускаем keep-alive в отдельном потоке
    threading.Thread(target=keep_render_awake, daemon=True).start()
    
    # Настраиваем веб-хук
    if setup_webhook():
        # Запускаем Flask
        port = int(os.environ.get('PORT', 10000))
        logger.info(f"🌐 Flask на порту {port}")
        
        # Важно: отключаем debug и reloader на Render
        app.run(
            host='0.0.0.0', 
            port=port, 
            debug=False, 
            use_reloader=False,
            threaded=True  # Разрешаем многопоточность для Flask
        )
    else:
        logger.error("❌ Бот не запущен из-за ошибки веб-хука")
