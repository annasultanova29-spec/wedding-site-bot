import os
import logging
import telebot
from flask import Flask, request
from telebot import types
import html

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация Flask приложения
app = Flask(__name__)

# ========== ВАШИ ДАННЫЕ ==========
TOKEN = os.environ.get('TELEGRAM_TOKEN', '8496935356:AAF3UOHTXykrqK6-nOeVFpAPCtewst-02PA')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', '787419978')
PORT = os.environ.get('PORT', '10000')
# =================================

# Получаем URL Render
RENDER_EXTERNAL_URL = os.environ.get('RENDER_EXTERNAL_URL', '')
if not RENDER_EXTERNAL_URL:
    # Формируем URL из имени сервиса
    service_name = os.environ.get('RENDER_SERVICE_NAME', 'wedding-site-bot')
    RENDER_EXTERNAL_URL = f"https://{service_name}.onrender.com"

logger.info(f"✅ URL: {RENDER_EXTERNAL_URL}")
logger.info(f"✅ Токен: {TOKEN[:10]}...")
logger.info(f"✅ Админ: {ADMIN_CHAT_ID}")

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# Глобальные переменные для хранения данных пользователей
user_data = {}

# ========== КЛАВИАТУРЫ ==========
def create_service_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton('Создание сайта')
    btn2 = types.KeyboardButton('Дизайн')
    btn3 = types.KeyboardButton('Продвижение')
    btn4 = types.KeyboardButton('Другое')
    markup.add(btn1, btn2, btn3, btn4)
    return markup

def create_contact_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_contact = types.KeyboardButton('📱 Отправить контакт', request_contact=True)
    btn_cancel = types.KeyboardButton('❌ Отмена')
    markup.add(btn_contact, btn_cancel)
    return markup

def create_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_order = types.KeyboardButton('🎉 Оформить заказ')
    btn_contact = types.KeyboardButton('📞 Контакты')
    btn_about = types.KeyboardButton('ℹ️ О нас')
    markup.add(btn_order, btn_contact, btn_about)
    return markup

# ========== ФУНКЦИИ ==========
def safe_send_message(chat_id, text, reply_markup=None):
    try:
        bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=None)
        logger.info(f"✅ Сообщение отправлено {chat_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        return False

def send_to_admin(user_id, username, service, contact, details=""):
    try:
        message = f"""
📋 НОВАЯ ЗАЯВКА

👤 Пользователь: @{username if username else 'без username'}
🆔 ID: {user_id}
🎯 Услуга: {service}
📱 Контакт: {contact}
📝 Детали: {details if details else 'не указаны'}

⏰ Время: сейчас
        """
        
        bot.send_message(ADMIN_CHAT_ID, message, parse_mode=None)
        logger.info(f"✅ Уведомление отправлено администратору")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка отправки: {e}")
        return False

# ========== ОБРАБОТЧИКИ ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    logger.info(f"👤 Пользователь {user_id} (@{username}) начал диалог")
    
    welcome_text = """
🎉 Добро пожаловать в Wedding Site Bot!

Выберите действие:
🎉 Оформить заказ - оставить заявку
📞 Контакты - связаться с нами
ℹ️ О нас - узнать подробнее
    """
    
    safe_send_message(message.chat.id, welcome_text, create_main_keyboard())

@bot.message_handler(func=lambda message: message.text == '🎉 Оформить заказ')
def start_order(message):
    user_id = message.from_user.id
    
    if user_id not in user_data:
        user_data[user_id] = {}
    
    user_data[user_id]['step'] = 'choose_service'
    safe_send_message(message.chat.id, "🎯 Выберите услугу:", create_service_keyboard())

@bot.message_handler(func=lambda message: 
                     message.from_user.id in user_data and 
                     user_data[message.from_user.id].get('step') == 'choose_service')
def choose_service(message):
    user_id = message.from_user.id
    service = message.text
    
    if service == '❌ Отмена':
        safe_send_message(message.chat.id, "Заказ отменен.", create_main_keyboard())
        if user_id in user_data:
            del user_data[user_id]
        return
    
    user_data[user_id]['service'] = service
    user_data[user_id]['step'] = 'enter_details'
    safe_send_message(message.chat.id, f"📝 Расскажите подробнее о проекте.\n\nУслуга: {service}\n\nЧто бы вы хотели получить?")

@bot.message_handler(func=lambda message: 
                     message.from_user.id in user_data and 
                     user_data[message.from_user.id].get('step') == 'enter_details')
def enter_details(message):
    user_id = message.from_user.id
    details = message.text
    
    user_data[user_id]['details'] = details
    user_data[user_id]['step'] = 'get_contact'
    safe_send_message(message.chat.id, "📱 Теперь поделитесь вашим контактом:", create_contact_keyboard())

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.from_user.id
    
    if user_id not in user_data or user_data[user_id].get('step') != 'get_contact':
        return
    
    contact = message.contact
    contact_info = f"{contact.first_name or ''} {contact.last_name or ''}".strip()
    if contact.phone_number:
        contact_info += f"\n📱 Телефон: {contact.phone_number}"
    
    user_data[user_id]['contact'] = contact_info
    user_data[user_id]['username'] = message.from_user.username or "без username"
    user_data[user_id]['step'] = 'confirm'
    
    order_summary = f"""
📋 Сводка заказа:

🎯 Услуга: {user_data[user_id]['service']}
📝 Детали: {user_data[user_id]['details']}
👤 Контакт: {contact_info}

✅ Всё верно? Заявка будет отправлена нашему менеджеру.
    """
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_yes = types.KeyboardButton('✅ Да, отправить')
    btn_no = types.KeyboardButton('❌ Нет, изменить')
    markup.add(btn_yes, btn_no)
    
    safe_send_message(message.chat.id, order_summary, markup)

@bot.message_handler(func=lambda message: 
                     message.from_user.id in user_data and 
                     user_data[message.from_user.id].get('step') == 'confirm')
def confirm_order(message):
    user_id = message.from_user.id
    answer = message.text
    
    if answer == '❌ Нет, изменить':
        safe_send_message(message.chat.id, "Начнем заново.", create_main_keyboard())
        if user_id in user_data:
            del user_data[user_id]
        return
    
    if answer == '✅ Да, отправить':
        success = send_to_admin(
            user_id=user_id,
            username=user_data[user_id]['username'],
            service=user_data[user_id]['service'],
            contact=user_data[user_id]['contact'],
            details=user_data[user_id]['details']
        )
        
        if success:
            response = "✅ Ваша заявка успешно отправлена! Менеджер свяжется с вами."
            logger.info(f"💾 Заказ: {user_data[user_id]['service']} от {user_id}")
        else:
            response = "⚠️ Заявка сохранена, но возникла проблема с уведомлением."
        
        safe_send_message(message.chat.id, response, create_main_keyboard())
        
        if user_id in user_data:
            del user_data[user_id]
    
    elif answer == '❌ Отмена':
        safe_send_message(message.chat.id, "Заказ отменен.", create_main_keyboard())
        if user_id in user_data:
            del user_data[user_id]

@bot.message_handler(func=lambda message: message.text == '📞 Контакты')
def send_contacts(message):
    contacts_text = """
📞 Наши контакты:

Email: info@wedding-site.ru
Телефон: +7 (999) 123-45-67
Telegram: @wedding_site_support

📍 Мы работаем с 10:00 до 20:00 по МСК
    """
    safe_send_message(message.chat.id, contacts_text)

@bot.message_handler(func=lambda message: message.text == 'ℹ️ О нас')
def about_us(message):
    about_text = """
🎩 Wedding Site Bot

Мы создаем уникальные свадебные сайты:
• Рассказываем вашу историю любви
• Помогаем гостям с информацией
• Принимаем поздравления
• Интегрируем с соцсетями

Работаем с 2018 года!
    """
    safe_send_message(message.chat.id, about_text)

@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    if message.text:
        safe_send_message(message.chat.id, "Выберите действие из меню 👇", create_main_keyboard())

# ========== ВЕБ-ХУКИ ==========

@app.route('/')
def index():
    return f"""
    <html>
        <head><title>Wedding Bot</title></head>
        <body style="text-align: center; padding: 50px;">
            <h1>🤵👰 Wedding Bot</h1>
            <p style="color: green; font-size: 24px;">✅ Бот работает через веб-хук!</p>
            <p>URL: {RENDER_EXTERNAL_URL}</p>
            <p><a href="/health">Проверить здоровье</a></p>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return 'OK', 200

# Веб-хук для Telegram
@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'Bad request', 400

# Настройка веб-хука при старте
@app.before_first_request
def setup_webhook():
    try:
        # Удаляем старый веб-хук
        bot.remove_webhook()
        
        # Устанавливаем новый веб-хук
        webhook_url = f"{RENDER_EXTERNAL_URL}/webhook/{TOKEN}"
        bot.set_webhook(url=webhook_url)
        logger.info(f"✅ Веб-хук установлен: {webhook_url}")
    except Exception as e:
        logger.error(f"❌ Ошибка настройки веб-хука: {e}")

# ========== ЗАПУСК ==========

if __name__ == '__main__':
    # Настраиваем веб-хук сразу
    try:
        bot.remove_webhook()
        webhook_url = f"{RENDER_EXTERNAL_URL}/webhook/{TOKEN}"
        bot.set_webhook(url=webhook_url)
        logger.info(f"🚀 Веб-хук установлен: {webhook_url}")
    except Exception as e:
        logger.error(f"⚠️ Ошибка веб-хука: {e}")
    
    # Запускаем Flask
    port = int(PORT)
    logger.info(f"🌐 Запуск сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
