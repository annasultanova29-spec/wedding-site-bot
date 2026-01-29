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

# Получение токена из переменных окружения
TOKEN = os.environ.get('TELEGRAM_TOKEN')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', '')  # ID чата для заявок

if not TOKEN:
    logger.error("❌ Токен бота не найден! Установите переменную TELEGRAM_TOKEN")
    exit(1)

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# Глобальные переменные для хранения данных пользователей
user_data = {}

# Клавиатура для выбора услуги
def create_service_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton('Создание сайта')
    btn2 = types.KeyboardButton('Дизайн')
    btn3 = types.KeyboardButton('Продвижение')
    btn4 = types.KeyboardButton('Другое')
    markup.add(btn1, btn2, btn3, btn4)
    return markup

# Клавиатура для контактов
def create_contact_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_contact = types.KeyboardButton('📱 Отправить контакт', request_contact=True)
    btn_cancel = types.KeyboardButton('❌ Отмена')
    markup.add(btn_contact, btn_cancel)
    return markup

# Обычная клавиатура
def create_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_order = types.KeyboardButton('🎉 Оформить заказ')
    btn_contact = types.KeyboardButton('📞 Контакты')
    btn_about = types.KeyboardButton('ℹ️ О нас')
    markup.add(btn_order, btn_contact, btn_about)
    return markup

# Функция для безопасной отправки сообщений (без parse_mode)
def safe_send_message(chat_id, text, reply_markup=None):
    """Безопасная отправка сообщения без форматирования"""
    try:
        # Экранируем HTML-символы чтобы избежать ошибок парсинга
        safe_text = html.escape(text)
        bot.send_message(chat_id, safe_text, reply_markup=reply_markup, parse_mode=None)
        logger.info(f"✅ Сообщение отправлено пользователю {chat_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка отправки сообщения: {e}")
        return False

# Функция для отправки уведомления администратору
def send_to_admin(user_id, username, service, contact, details=""):
    """Отправка заявки администратору"""
    if not ADMIN_CHAT_ID:
        logger.warning("⚠️ ADMIN_CHAT_ID не установлен, уведомление не отправлено")
        return False
    
    try:
        message = f"""
📋 НОВАЯ ЗАЯВКА

👤 Пользователь: @{username if username else 'без username'}
🆔 ID: {user_id}
🎯 Услуга: {service}
📱 Контакт: {contact}
📝 Детали: {details if details else 'не указаны'}

Время: {telebot.formatting.hbold('сейчас')}
        """
        
        # Отправляем без форматирования, чтобы избежать ошибок
        bot.send_message(
            ADMIN_CHAT_ID, 
            message.replace('**', '').replace('__', ''),  # Убираем Markdown
            parse_mode=None  # Отключаем форматирование
        )
        logger.info(f"✅ Уведомление отправлено администратору {ADMIN_CHAT_ID}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления администратору: {e}")
        return False

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    logger.info(f"👤 Пользователь {user_id} (@{username}) начал диалог")
    
    welcome_text = """
🎉 Добро пожаловать в Wedding Site Bot!

Я помогу вам создать идеальный свадебный сайт.

Выберите действие:
🎉 Оформить заказ - оставить заявку на создание сайта
📞 Контакты - связаться с нами
ℹ️ О нас - узнать подробнее о наших услугах
    """
    
    safe_send_message(message.chat.id, welcome_text, create_main_keyboard())

# Обработчик кнопки "Оформить заказ"
@bot.message_handler(func=lambda message: message.text == '🎉 Оформить заказ')
def start_order(message):
    user_id = message.from_user.id
    
    # Сохраняем ID пользователя
    if user_id not in user_data:
        user_data[user_id] = {}
    
    user_data[user_id]['step'] = 'choose_service'
    
    text = "🎯 Выберите услугу:"
    safe_send_message(message.chat.id, text, create_service_keyboard())

# Обработчик выбора услуги
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
    
    # Сохраняем выбранную услугу
    user_data[user_id]['service'] = service
    user_data[user_id]['step'] = 'enter_details'
    
    text = f"📝 Расскажите подробнее о вашем проекте.\n\nУслуга: {service}\n\nЧто бы вы хотели получить?"
    safe_send_message(message.chat.id, text)

# Обработчик ввода деталей
@bot.message_handler(func=lambda message: 
                     message.from_user.id in user_data and 
                     user_data[message.from_user.id].get('step') == 'enter_details')
def enter_details(message):
    user_id = message.from_user.id
    details = message.text
    
    user_data[user_id]['details'] = details
    user_data[user_id]['step'] = 'get_contact'
    
    text = "📱 Теперь поделитесь вашим контактом для связи:"
    safe_send_message(message.chat.id, text, create_contact_keyboard())

# Обработчик контакта
@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.from_user.id
    
    if user_id not in user_data or user_data[user_id].get('step') != 'get_contact':
        return
    
    contact = message.contact
    
    # Формируем контактную информацию
    contact_info = f"{contact.first_name or ''} {contact.last_name or ''}".strip()
    if contact.phone_number:
        contact_info += f"\n📱 Телефон: {contact.phone_number}"
    
    user_data[user_id]['contact'] = contact_info
    user_data[user_id]['username'] = message.from_user.username or "без username"
    user_data[user_id]['step'] = 'confirm'
    
    # Показываем сводку заказа
    order_summary = f"""
📋 Сводка заказа:

🎯 Услуга: {user_data[user_id]['service']}
📝 Детали: {user_data[user_id]['details']}
👤 Контакт: {contact_info}

✅ Всё верно? Заявка будет отправлена нашему менеджеру.
    """
    
    # Создаем клавиатуру подтверждения
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_yes = types.KeyboardButton('✅ Да, отправить')
    btn_no = types.KeyboardButton('❌ Нет, изменить')
    markup.add(btn_yes, btn_no)
    
    safe_send_message(message.chat.id, order_summary, markup)

# Обработчик подтверждения
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
        # Отправляем заявку администратору
        success = send_to_admin(
            user_id=user_id,
            username=user_data[user_id]['username'],
            service=user_data[user_id]['service'],
            contact=user_data[user_id]['contact'],
            details=user_data[user_id]['details']
        )
        
        if success:
            response = "✅ Ваша заявка успешно отправлена! Наш менеджер свяжется с вами в ближайшее время."
            logger.info(f"💾 Заказ сохранен: {user_data[user_id]['service']} от пользователя {user_id}")
        else:
            response = "⚠️ Заявка сохранена, но возникла проблема с уведомлением администратора."
        
        safe_send_message(message.chat.id, response, create_main_keyboard())
        
        # Очищаем данные пользователя
        if user_id in user_data:
            del user_data[user_id]
    
    elif answer == '❌ Отмена':
        safe_send_message(message.chat.id, "Заказ отменен.", create_main_keyboard())
        if user_id in user_data:
            del user_data[user_id]

# Обработчик кнопки "Контакты"
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

# Обработчик кнопки "О нас"
@bot.message_handler(func=lambda message: message.text == 'ℹ️ О нас')
def about_us(message):
    about_text = """
🎩 Wedding Site Bot

Мы создаем уникальные свадебные сайты, которые:
• Рассказывают вашу историю любви
• Помогают гостям с информацией
• Принимают поздравления и подарки
• Интегрируются с социальными сетями

Наши услуги:
🎯 Создание сайта - от идеи до запуска
🎨 Дизайн - уникальный стиль для вашей пары
🚀 Продвижение - привлечение гостей на сайт

Работаем с 2018 года, создали более 500 свадебных сайтов!
    """
    safe_send_message(message.chat.id, about_text)

# Обработчик всех остальных сообщений
@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    if message.text:
        safe_send_message(message.chat.id, 
                         "Выберите действие из меню ниже 👇", 
                         create_main_keyboard())

# ========== FLASK РОУТЫ ДЛЯ RENDER ==========

@app.route('/')
def index():
    return "🤵👰 Wedding Site Bot работает! ✅"

@app.route('/health')
def health():
    return 'OK', 200

# Webhook endpoint (опционально)
@app.route(f'/webhook/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    return 'Bad request', 400

# Polling endpoint для запуска бота
@app.route('/start_bot', methods=['POST'])
def start_bot_polling():
    try:
        bot.remove_webhook()
        bot.polling(none_stop=True, timeout=60)
        return 'Bot started', 200
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return f'Error: {e}', 500

# ========== ЗАПУСК ПРИЛОЖЕНИЯ ==========

if __name__ == '__main__':
    # Получаем порт из переменных окружения Render
    port = int(os.environ.get('PORT', 5000))
    
    logger.info(f"🚀 Запуск бота на порту {port}")
    
    # Запускаем Flask приложение
    app.run(host='0.0.0.0', port=port)
