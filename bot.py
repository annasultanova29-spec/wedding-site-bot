import os
import telebot
from telebot import types
import sqlite3
import datetime
import logging
from flask import Flask, request
import time

# ========== ПРАВИЛЬНАЯ КОНФИГУРАЦИЯ ==========
import os
TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_CHAT_ID = "787419978"          # ВАШ личный ID
GROUP_CHAT_ID = "-5275786758"        # ID группы для заявок

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

# ========== ФУНКЦИЯ ДЛЯ ОТПРАВКИ ЗАЯВОК ==========
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
        
        # 1. Отправляем вам (ADMIN_CHAT_ID)
        bot.send_message(ADMIN_CHAT_ID, message)
        logger.info(f"✅ Заявка отправлена администратору")
        
        # 2. Отправляем в группу (GROUP_CHAT_ID)
        bot.send_message(GROUP_CHAT_ID, message)
        logger.info(f"✅ Заявка отправлена в группу")
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки: {e}")

# ========== ОСНОВНЫЕ КОМАНДЫ ==========
@bot.message_handler(commands=['start', 'order'])
def start_command(message):
    """Команда /start и /order"""
    if message.chat.type != 'private':
        return  # Игнорируем группы
        
    user_id = message.from_user.id
    username = message.from_user.username
    logger.info(f"👤 Пользователь {user_id} (@{username}) начал диалог")
    
    # Очищаем предыдущие данные
    if user_id in user_data:
        del user_data[user_id]
    
    # Главное меню
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('🎯 Заказать сайт'),
        types.KeyboardButton('🔒 Политика'),
        types.KeyboardButton('✨ Примеры работ'),
        types.KeyboardButton('💰 Стоимость')
    )
    
    bot.send_message(
        message.chat.id,
        """🎉 Добро пожаловать!

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

Выберите действие: ⬇️""",
        reply_markup=markup
    )

# ========== ОБРАБОТКА КНОПОК ГЛАВНОГО МЕНЮ ==========
@bot.message_handler(func=lambda m: m.text == '🎯 Заказать сайт')
def order_button(message):
    """Кнопка Заказать сайт - НАЧАЛО РАБОТЫ"""
    if message.chat.type != 'private':
        return
        
    user_id = message.from_user.id
    user_data[user_id] = {}
    
    msg = bot.send_message(
        message.chat.id,
        "📋 АНКЕТА ДЛЯ ЗАКАЗА\n\n"
        "Заполните 4 простых поля, и я свяжусь с вами "
        "в течение 24 часов!\n\n"
        "🔹 Шаг 1 из 4\n"
        "Напишите ваше имя и фамилию:",
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, process_name_step)

def process_name_step(message):
    """Шаг 1: Обработка имени"""
    try:
        name = message.text.strip()
        user_id = message.from_user.id
        
        if len(name) < 2:
            bot.send_message(message.chat.id, "❌ Имя слишком короткое. Введите имя и фамилию:")
            bot.register_next_step_handler(message, process_name_step)
            return
        
        if user_id not in user_data:
            user_data[user_id] = {}
        
        user_data[user_id]['name'] = name
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('📱 Поделиться телефоном', request_contact=True))
        
        msg = bot.send_message(
            message.chat.id,
            f"👤 Имя: {name}\n\n"
            "🔹 Шаг 2 из 4\n"
            "Нажмите кнопку ниже, чтобы поделиться номером телефона, "
            "или напишите номер вручную (в формате +7 XXX XXX-XX-XX):",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, process_phone_step)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в имени: {e}")
        bot.send_message(message.chat.id, "❌ Что-то пошло не так. Начнем заново /start")

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    """Обработка контакта из кнопки"""
    if message.chat.type != 'private':
        return
        
    if hasattr(message, 'contact') and message.contact:
        phone = message.contact.phone_number
        user_id = message.from_user.id
        
        if user_id not in user_data:
            user_data[user_id] = {}
        
        user_data[user_id]['phone'] = phone
        ask_telegram_step(message)

def process_phone_step(message):
    """Шаг 2: Обработка телефона вручную"""
    try:
        if hasattr(message, 'contact') and message.contact:
            phone = message.contact.phone_number
        else:
            phone = message.text.strip()
            
        if not phone:
            bot.send_message(message.chat.id, "❌ Введите номер телефона:")
            bot.register_next_step_handler(message, process_phone_step)
            return
            
        user_id = message.from_user.id
        if user_id not in user_data:
            user_data[user_id] = {}
        
        user_data[user_id]['phone'] = phone
        ask_telegram_step(message)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в телефоне: {e}")

def ask_telegram_step(message):
    """Шаг 3: Запрос Telegram"""
    user_id = message.from_user.id
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('➡️ Пропустить'))
    
    msg = bot.send_message(
        message.chat.id,
        f"📱 Телефон: {user_data[user_id]['phone']}\n\n"
        "🔹 Шаг 3 из 4\n"
        "Укажите ваш Telegram username (например, @username):\n"
        "Можно пропустить, нажав кнопку ниже",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, process_telegram_step)

def process_telegram_step(message):
    """Шаг 3: Обработка Telegram"""
    try:
        telegram = message.text.strip()
        if telegram == '➡️ Пропустить':
            telegram = 'Не указан'
        elif not telegram.startswith('@'):
            telegram = f"@{telegram}"
            
        user_id = message.from_user.id
        user_data[user_id]['telegram'] = telegram
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        years = ['2025', '2026', '2027', '2028', 'Еще не знаю']
        for year in years:
            markup.add(types.KeyboardButton(year))
        
        msg = bot.send_message(
            message.chat.id,
            f"📲 Telegram: {telegram}\n\n"
            "🔹 Шаг 4 из 4\n"
            "Выберите год свадьбы:",
            reply_markup=markup
        )
        bot.register_next_step_handler(msg, process_date_step)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в Telegram: {e}")

def process_date_step(message):
    """Шаг 4: Обработка даты"""
    try:
        wedding_date = message.text.strip()
        user_id = message.from_user.id
        
        user_data[user_id]['wedding_date'] = wedding_date
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton('✅ Да, согласен'),
            types.KeyboardButton('❌ Нет, отменить')
        )
        
        summary = f"""📋 ПРОВЕРЬТЕ ВАШИ ДАННЫЕ:

👤 Имя: {user_data[user_id]['name']}
📱 Телефон: {user_data[user_id]['phone']}
📲 Telegram: {user_data[user_id]['telegram']}
📅 Год свадьбы: {wedding_date}

🔒 СОГЛАСИЕ НА ОБРАБОТКУ ДАННЫХ:
Я согласен на обработку моих персональных данных 
в соответствии с Федеральным законом №152-ФЗ 
для связи и обсуждения заказа.

Подтверждаете отправку заявки?"""
        
        bot.send_message(message.chat.id, summary, reply_markup=markup)
        bot.register_next_step_handler(message, process_consent_step)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в дате: {e}")

def process_consent_step(message):
    """Финальное подтверждение"""
    try:
        user_id = message.from_user.id
        
        if message.text == '✅ Да, согласен':
            # Сохраняем в БД
            save_order_to_db(user_id)
            
            # Отправляем уведомления
            send_order_notification({
                'name': user_data[user_id]['name'],
                'phone': user_data[user_id]['phone'],
                'telegram': user_data[user_id]['telegram'],
                'wedding_date': user_data[user_id]['wedding_date'],
                'user_id': user_id,
                'username': message.from_user.username
            })
            
            success_text = f"""🎉 {user_data[user_id]['name']}, ВАША ЗАЯВКА ПРИНЯТА!

✅ Спасибо за доверие!
⏱ Я свяжусь с вами в течение 24 часов.

📞 Мои контакты для связи:
Telegram: @ami_sultanova
До скорой встречи! ✨"""
            
            bot.send_message(message.chat.id, success_text, reply_markup=types.ReplyKeyboardRemove())
            logger.info(f"✅ Новый заказ от {user_data[user_id]['name']}")
            
        else:
            bot.send_message(message.chat.id,
                           "❌ Заказ отменен.\n\n"
                           "Если передумаете — нажмите /start",
                           reply_markup=types.ReplyKeyboardRemove())
        
        # Очищаем данные пользователя
        if user_id in user_data:
            del user_data[user_id]
            
    except Exception as e:
        logger.error(f"❌ Ошибка подтверждения: {e}")

def save_order_to_db(user_id):
    """Сохранение заказа в базу данных"""
    try:
        conn = sqlite3.connect('orders.db', check_same_thread=False)
        c = conn.cursor()
        c.execute('''INSERT INTO orders 
                     (name, telegram, phone, wedding_date, created_date, consent, user_id) 
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (user_data[user_id]['name'], 
                   user_data[user_id]['telegram'], 
                   user_data[user_id]['phone'], 
                   user_data[user_id]['wedding_date'], 
                   datetime.datetime.now(), 
                   1, 
                   user_id))
        conn.commit()
        conn.close()
        logger.info(f"💾 Заказ сохранен в БД: {user_data[user_id]['name']}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения: {e}")

# ========== ДРУГИЕ КНОПКИ МЕНЮ ==========
@bot.message_handler(func=lambda m: m.text == '🔒 Политика')
def privacy_button(message):
    if message.chat.type != 'private':
        return
        
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
    
    bot.send_message(message.chat.id, privacy_text)

@bot.message_handler(func=lambda m: m.text == '✨ Примеры работ')
def examples_button(message):
    if message.chat.type != 'private':
        return
        
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
    
    bot.send_message(message.chat.id, examples_text)

@bot.message_handler(func=lambda m: m.text == '💰 Стоимость')
def price_button(message):
    if message.chat.type != 'private':
        return
        
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
    
    bot.send_message(message.chat.id, price_text)

# ========== ОБРАБОТКА ДРУГИХ СООБЩЕНИЙ ==========
@bot.message_handler(func=lambda m: True)
def handle_other_messages(message):
    """Обработка всех остальных сообщений"""
    if message.chat.type != 'private':
        return  # Игнорируем группы
        
    # Показываем главное меню
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('🎯 Заказать сайт'),
        types.KeyboardButton('🔒 Политика'),
        types.KeyboardButton('✨ Примеры работ'),
        types.KeyboardButton('💰 Стоимость')
    )
    
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
        reply_markup=markup
    )

# ========== FLASK ДЛЯ RENDER ==========
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
                <p>Заявки приходят администратору и в группу</p>
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
    logger.info(f"👑 Администратор: {ADMIN_CHAT_ID}")
    logger.info(f"👥 Группа: {GROUP_CHAT_ID}")
    
    init_db()
    
    # Запускаем Flask в отдельном потоке
    import threading
    
    def run_flask():
        port = int(os.environ.get('PORT', 10000))
        logger.info(f"🌐 Запуск веб-сервера на порту {port}")
        app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Даем Flask время на запуск
    time.sleep(2)
    
    # Запускаем бота
       logger.info("🤖 Запуск polling бота...")

    while True:
        try:
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            logger.error(f"❌ Polling упал: {e}")
            time.sleep(5)
