import telebot
from telebot import types
import sqlite3
import datetime
import os
import logging
from flask import Flask

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === ВАШИ ДАННЫЕ ===
TOKEN = "8496935356:AAF3UOHTXykrqK6-nOeVFpAPCtewst-02PA"
ADMIN_CHAT_ID ="-5275786758"# Ваш личный ID
GROUP_CHAT_ID ="787419978"# ID группы (если есть)

bot = telebot.TeleBot(TOKEN)

# База данных
def init_db():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  telegram TEXT,
                  phone TEXT,
                  wedding_date TEXT,
                  created_date TIMESTAMP,
                  consent INTEGER DEFAULT 0,
                  user_id INTEGER)''')
    conn.commit()
    conn.close()
    logger.info("✅ База данных готова")

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    logger.info(f"👤 Пользователь {user_id} (@{username}) начал диалог")
    
    # Если переход с сайта
    if len(message.text.split()) > 1:
        param = message.text.split()[1]
        if param == 'siteorder':
            logger.info(f"🌐 Переход с сайта от {user_id}")
            start_order(message)
            return
    
    # Главное меню
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_order = types.KeyboardButton('🎯 Заказать сайт')
    btn_privacy = types.KeyboardButton('🔒 Политика')
    btn_examples = types.KeyboardButton('✨ Примеры работ')
    btn_price = types.KeyboardButton('💰 Стоимость')
    markup.add(btn_order, btn_privacy, btn_examples, btn_price)
    
    welcome_text = """🎉 Добро пожаловать!

Я Анна, и я создаю свадебные сайты-приглашения 
такие же, как у Татьяны и Александра!

✨ Что входит в сайт:
• Адаптивный дизайн (для телефонов и компьютеров)
• Таймер обратного отсчета
• Анкета для гостей (RSVP)
• История любви с фотографиями
• Программа мероприятия
• Карты и контакты
• Фоновая музыка и видео

⏱ Срок создания: 2-3 дня
💝 Стоимость: от 5000 рублей

Выберите действие: ⬇️"""
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode=None)

# Главное меню
@bot.message_handler(func=lambda message: message.text in [
    '🎯 Заказать сайт', '🔒 Политика', '✨ Примеры работ', '💰 Стоимость'
])
def handle_main_menu(message):
    if message.text == '🎯 Заказать сайт':
        start_order(message)
    elif message.text == '🔒 Политика':
        send_privacy(message)
    elif message.text == '✨ Примеры работ':
        send_examples(message)
    elif message.text == '💰 Стоимость':
        send_price(message)

def start_order(message):
    msg = bot.send_message(
        message.chat.id,
        "📋 АНКЕТА ДЛЯ ЗАКАЗА\n\n"
        "Заполните 4 простых поля, и я свяжусь с вами "
        "в течение 24 часов!\n\n"
        "🔹 Шаг 1 из 4\n"
        "Напишите ваше имя и фамилию:",
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode=None
    )
    bot.register_next_step_handler(msg, process_name_step)

def process_name_step(message):
    try:
        name = message.text.strip()
        if len(name) < 2:
            bot.send_message(message.chat.id, 
                           "❌ Имя слишком короткое. Введите имя и фамилию:",
                           parse_mode=None)
            bot.register_next_step_handler(message, process_name_step)
            return
            
        user_data = {
            'name': name, 
            'user_id': message.from_user.id,
            'username': message.from_user.username
        }
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('📱 Поделиться телефоном', request_contact=True))
        
        msg = bot.send_message(
            message.chat.id,
            f"👤 Имя: {name}\n\n"
            "🔹 Шаг 2 из 4\n"
            "Нажмите кнопку ниже, чтобы поделиться номером телефона, "
            "или напишите номер вручную (в формате +7 XXX XXX-XX-XX):",
            reply_markup=markup,
            parse_mode=None
        )
        bot.register_next_step_handler(msg, process_phone_step, user_data)
    except Exception as e:
        logger.error(f"❌ Ошибка в имени: {e}")
        bot.send_message(message.chat.id, 
                        "❌ Что-то пошло не так. Начнем заново /start",
                        parse_mode=None)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    if hasattr(message, 'contact') and message.contact:
        phone = message.contact.phone_number
        user_data = {
            'name': 'Не указано',
            'user_id': message.from_user.id,
            'username': message.from_user.username
        }
        user_data['phone'] = phone
        ask_telegram(message, user_data)

def process_phone_step(message, user_data):
    try:
        if hasattr(message, 'contact') and message.contact:
            phone = message.contact.phone_number
        else:
            phone = message.text.strip()
            
        if not phone:
            bot.send_message(message.chat.id, 
                           "❌ Введите номер телефона:",
                           parse_mode=None)
            bot.register_next_step_handler(message, process_phone_step, user_data)
            return
            
        user_data['phone'] = phone
        ask_telegram(message, user_data)
    except Exception as e:
        logger.error(f"❌ Ошибка в телефоне: {e}")

def ask_telegram(message, user_data):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('➡️ Пропустить'))
    
    msg = bot.send_message(
        message.chat.id,
        f"📱 Телефон: {user_data['phone']}\n\n"
        "🔹 Шаг 3 из 4\n"
        "Укажите ваш Telegram username (например, @username):\n"
        "Можно пропустить, нажав кнопку ниже",
        reply_markup=markup,
        parse_mode=None
    )
    bot.register_next_step_handler(msg, process_telegram_step, user_data)

def process_telegram_step(message, user_data):
    try:
        telegram = message.text.strip() 
        if telegram == '➡️ Пропустить':
            telegram = 'Не указан'
        elif not telegram.startswith('@'):
            telegram = f"@{telegram}"
            
        user_data['telegram'] = telegram
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        years = ['2025', '2026', '2027', '2028', 'Еще не знаю']
        for year in years:
            markup.add(types.KeyboardButton(year))
        
        msg = bot.send_message(
            message.chat.id,
            f"📲 Telegram: {telegram}\n\n"
            "🔹 Шаг 4 из 4\n"
            "Выберите год свадьбы:",
            reply_markup=markup,
            parse_mode=None
        )
        bot.register_next_step_handler(msg, process_date_step, user_data)
    except Exception as e:
        logger.error(f"❌ Ошибка в Telegram: {e}")

def process_date_step(message, user_data):
    try:
        wedding_date = message.text.strip()
        user_data['wedding_date'] = wedding_date
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton('✅ Да, согласен'),
            types.KeyboardButton('❌ Нет, отменить')
        )
        
        summary = f"""📋 ПРОВЕРЬТЕ ВАШИ ДАННЫЕ:

👤 Имя: {user_data['name']}
📱 Телефон: {user_data['phone']}
📲 Telegram: {user_data['telegram']}
📅 Год свадьбы: {wedding_date}

🔒 СОГЛАСИЕ НА ОБРАБОТКУ ДАННЫХ:
Я согласен на обработку моих персональных данных 
в соответствии с Федеральным законом №152-ФЗ 
для связи и обсуждения заказа.

Подтверждаете отправку заявки?"""
        
        bot.send_message(message.chat.id, summary, reply_markup=markup, parse_mode=None)
        bot.register_next_step_handler(message, process_consent_step, user_data)
    except Exception as e:
        logger.error(f"❌ Ошибка в дате: {e}")

def process_consent_step(message, user_data):
    try:
        if message.text == '✅ Да, согласен':
            save_order(user_data)
            notify_admin(user_data, message.from_user.username)
            
            success_text = f"""🎉 {user_data['name']}, ВАША ЗАЯВКА ПРИНЯТА!

✅ Спасибо за доверие!
⏱ Я свяжусь с вами в течение 24 часов.

📞 Мои контакты для связи:
Telegram: @ami_sultanova
До скорой встречи! ✨"""
            
            bot.send_message(message.chat.id, success_text, 
                           reply_markup=types.ReplyKeyboardRemove(),
                           parse_mode=None)
            logger.info(f"✅ Новый заказ от {user_data['name']}")
        else:
            bot.send_message(message.chat.id,
                           "❌ Заказ отменен.\n\n"
                           "Если передумаете — нажмите /start",
                           reply_markup=types.ReplyKeyboardRemove(),
                           parse_mode=None)
    except Exception as e:
        logger.error(f"❌ Ошибка подтверждения: {e}")

def save_order(data):
    try:
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute('''INSERT INTO orders 
                     (name, telegram, phone, wedding_date, created_date, consent, user_id) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (data['name'], data['telegram'], data['phone'], 
                   data['wedding_date'], datetime.datetime.now(), 1, 
                   data['user_id']))
        conn.commit()
        conn.close()
        logger.info(f"💾 Заказ сохранен в БД: {data['name']}")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения: {e}")

def notify_admin(data, username):
    try:
        timestamp = datetime.datetime.now().strftime('%H:%M %d.%m.%Y')
        
        # Убираем все Markdown символы, чтобы не было ошибок
        message = f"""🎯 НОВЫЙ ЗАКАЗ САЙТА!

👤 Имя: {data['name']}
📱 Телефон: {data['phone']}
📲 Telegram: {data['telegram']}
📅 Год свадьбы: {data['wedding_date']}
🆔 Username: @{username if username else 'нет'}
🆔 User ID: {data['user_id']}
⏰ Время: {timestamp}

заказсайт"""
        
        # Отправляем ТОЛЬКО вам (ADMIN_CHAT_ID = 787419978)
        bot.send_message(ADMIN_CHAT_ID, message, parse_mode=None)
        
        logger.info(f"📨 Уведомление отправлено администратору")
    except Exception as e:
        logger.error(f"❌ Ошибка уведомления: {e}")

def send_privacy(message):
    privacy_text = """🔒 ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ

1. Общие положения
Мы соблюдаем требования Федерального закона №152-ФЗ 
"О персональных данных".

2. Какие данные собираем:
• Имя и фамилия
• Номер телефона
• Telegram username
• Планируемая дата свадьбы

3. Для чего используем:
• Для связи с вами
• Для обсуждения деталей заказа
• Для подготовки коммерческого предложения

4. Срок хранения:
6 месяцев с момента получения

5. Ваши права:
• Право на доступ к данным
• Право на исправление
• Право на удаление данных
• Право на отзыв согласия

6. Контакты:
По вопросам обработки данных обращайтесь:
Telegram: @ami_sultanova"""
    bot.send_message(message.chat.id, privacy_text, parse_mode=None)

def send_examples(message):
    examples_text = """✨ ПРИМЕРЫ РАБОТ:

1. Свадьба Татьяны и Александра
   (пример, который вы видели)

2. Свадьба в стиле "Винтаж"
   - Пастельные тона
   - Старинные фотографии
   - Классическая музыка

3. Современная свадьба
   - Яркие цвета
   - Анимации
   - Интерактивные элементы

Каждый сайт уникален! 
Я создам дизайн специально под вашу пару."""
    bot.send_message(message.chat.id, examples_text, parse_mode=None)

def send_price(message):
    price_text = """💰 СТОИМОСТЬ И УСЛУГИ:

БАЗОВЫЙ ПАКЕТ (5000 руб.):
✅ Адаптивный дизайн
✅ 6 основных разделов
✅ Форма для гостей
✅ Таймер обратного отсчета
✅ До 20 фотографий
✅ Поддержка 7 дней

ПРЕМИУМ ПАКЕТ (8000 руб.):
✅ Всё из базового пакета
✅ Видео-фон на главной
✅ Анимации и эффекты
✅ Интеграция с музыкой
✅ Индивидуальный дизайн
✅ Поддержка 30 дней

СРОКИ:
• Базовая версия: 2-3 дня
• Премиум версия: 3-5 дней

ОПЛАТА:
50% предоплата, 50% после готовности"""
    bot.send_message(message.chat.id, price_text, parse_mode=None)

# Обработка остальных сообщений
@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    bot.send_message(
        message.chat.id,
        "Используйте кнопки меню:\n"
        "🎯 Заказать сайт - начать оформление\n"
        "🔒 Политика - конфиденциальность\n"
        "✨ Примеры работ - наши проекты\n"
        "💰 Стоимость - цены и пакеты\n\n"
        "Или команды:\n"
        "/start - перезапустить бота\n"
        "/order - заказать сайт\n"
        "/privacy - политика",
        parse_mode=None
    )

# ========== Flask для Render ==========

app = Flask(__name__)

@app.route('/')
def home():
    return """
    <html>
        <head>
            <title>Wedding Site Bot</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                }
                .container {
                    max-width: 600px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 15px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                }
                .status {
                    color: green;
                    font-size: 24px;
                    font-weight: bold;
                }
                .heart {
                    color: #ff4081;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤵<span class="heart">💍</span>👰 Wedding Site Bot</h1>
                <div class="status">✅ Бот активен и работает!</div>
                <p>Бот для создания свадебных сайтов-приглашений</p>
                <p>Все заявки приходят прямо администратору</p>
                <p><a href="/health" style="color: #4CAF50;">🩺 Проверить здоровье системы</a></p>
            </div>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return 'OK', 200

# ========== ЗАПУСК ==========

if __name__ == '__main__':
    logger.info("🚀 Бот запускается...")
    logger.info(f"🤖 Токен: {TOKEN[:10]}...")
    logger.info(f"👑 Администратор (Вы): {ADMIN_CHAT_ID}")
    
    init_db()
    
    # Запускаем Flask в отдельном потоке
    import threading
    
    def run_flask():
        port = int(os.environ.get("PORT", 10000))
        logger.info(f"🌐 Запуск веб-сервера на порту {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Запускаем бота
     try:
        bot.delete_webhook(drop_pending_updates=True)
        bot.polling(none_stop=True, timeout=60)
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
