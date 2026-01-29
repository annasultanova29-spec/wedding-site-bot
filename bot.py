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
WEBSITE_URL = "https://annasultanova29-spec.github.io/wedding-site-89/"

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
def save_to_db(order_data):
    """Сохраняет заявку в базу данных"""
    try:
        conn = sqlite3.connect('orders.db', check_same_thread=False)
        c = conn.cursor()
        c.execute('''INSERT INTO orders 
                     (name, telegram, phone, wedding_date, created_date, user_id)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (order_data['name'], order_data['telegram'], order_data['phone'],
                   order_data['wedding_date'], datetime.datetime.now(), order_data['user_id']))
        conn.commit()
        conn.close()
        logger.info("✅ Заявка сохранена в БД")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения в БД: {e}")

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
🌐 Сайт: {WEBSITE_URL}

#заказсайт"""
        
        bot.send_message(ADMIN_CHAT_ID, message)
        bot.send_message(GROUP_CHAT_ID, message)
        
        # Сохраняем в БД
        save_to_db(order_data)
        logger.info("✅ Заявка отправлена и сохранена")
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки: {e}")

def show_main_menu(chat_id):
    """Показывает главное меню"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('🎯 Заказать сайт'),
        types.KeyboardButton('🔒 Политика'),
        types.KeyboardButton('✨ Примеры работ'),
        types.KeyboardButton('💰 Стоимость'),
        types.KeyboardButton('🌐 Наш сайт')
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
    
    welcome_text = f"""🤵👰 Добро пожаловать в бот по созданию свадебных сайтов!

Я помогу вам создать идеальный сайт для вашей свадьбы.

✨ Что я могу:
• Создать уникальный свадебный сайт
• Разместить информацию для гостей
• Добавить галерею ваших фото
• Встроить карту проезда
• Настроить форму RSVP (подтверждения присутствия)
• И многое другое!

Выберите действие в меню ниже:"""
    
    bot.send_message(message.chat.id, welcome_text)
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

# ========== ДОБАВЬТЕ ЭТИ НОВЫЕ ОБРАБОТЧИКИ ==========
@bot.message_handler(func=lambda m: m.text == '🌐 Наш сайт')
def website_button(message):
    """Обработчик кнопки 'Наш сайт'"""
    website_text = f"""🌐 Наш свадебный сайт:

{WEBSITE_URL}

✨ На сайте вы можете увидеть:
• Пример свадебного сайта вживую
• Все функции и возможности
• Дизайн и анимации
• Адаптивную верстку для телефонов

📱 Перейдите по ссылке, чтобы увидеть реальный пример работы!"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🌐 Открыть сайт", url=WEBSITE_URL))
    
    bot.send_message(
        message.chat.id,
        website_text,
        reply_markup=markup,
        disable_web_page_preview=False
    )
    show_main_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == '✨ Примеры работ')
def examples_button(message):
    """Обработчик кнопки 'Примеры работ'"""
    examples_text = """✨ Примеры наших свадебных сайтов:

1. **Классическая свадьба** 
   - Элегантный дизайн с золотыми акцентами
   - Галерея фотографий пары
   - Таймер до свадьбы
   - Карта проезда к месту торжества

2. **Современный минимализм**
   - Чистый белый дизайн
   - Анимации при прокрутке
   - Интерактивная форма RSVP
   - Онлайн-книга пожеланий

3. **Романтический стиль**
   - Нежные пастельные тона
   - Фон с цветами и текстурами
   - Раздел "Наша история"
   - Интеграция с Instagram

4. **Тематическая свадьба**
   - Дизайн под конкретную тему
   - Кастомные иллюстрации
   - Интерактивные элементы
   - Музыкальное сопровождение

🌐 Посмотреть живой пример: {WEBSITE_URL}""".format(WEBSITE_URL=WEBSITE_URL)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🌐 Посмотреть пример", url=WEBSITE_URL))
    
    bot.send_message(
        message.chat.id,
        examples_text,
        reply_markup=markup
    )
    show_main_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == '💰 Стоимость')
def price_button(message):
    """Обработчик кнопки 'Стоимость'"""
    price_text = """💰 Стоимость свадебного сайта:

✨ **Базовый пакет** - 5 000 руб.
• Одностраничный сайт-лендинг
• Адаптивный дизайн (ПК + телефон)
• До 10 фотографий в галерее
• Форма для связи
• Карта проезда
• Таймер до свадьбы
• Срок: 3-5 дней

✨ **Стандартный пакет** - 8 000 руб.
• Всё из базового пакета +
• Раздел "Наша история"
• Онлайн-книга пожеланий
• Форма RSVP (подтверждения)
• Интеграция с календарем
• Анимации и эффекты
• До 20 фотографий
• Срок: 5-7 дней

✨ **Премиум пакет** - 12 000 руб.
• Всё из стандартного пакета +
• Уникальный дизайн с нуля
• Интерактивные элементы
• Интеграция с Instagram
• Музыкальное сопровождение
• Доменное имя на год
• Неограниченное число фото
• Техподдержка 1 месяц
• Срок: 7-10 дней

💎 **Что входит во все пакеты:**
• Бесплатные правки в течение 3 дней
• Инструкция по управлению
• Поддержка при запуске
• Оптимизация для поисковиков

🎯 Нажмите «Заказать сайт» для начала работы!"""
    
    bot.send_message(message.chat.id, price_text)
    show_main_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == '🔒 Политика')
def policy_button(message):
    """Обработчик кнопки 'Политика'"""
    policy_text = """🔒 Политика конфиденциальности и обработки данных:

**1. Сбор информации**
Мы собираем только необходимую информацию:
• Имя и фамилия
• Контактный телефон
• Telegram username
• Год свадьбы

**2. Использование информации**
Ваши данные используются исключительно для:
• Связи с вами по вопросам заказа
• Обсуждения деталей проекта
• Отправки уведомлений о статусе заказа
• Не передаются третьим лицам

**3. Хранение данных**
• Данные хранятся в зашифрованной базе
• Доступ имеют только ответственные лица
• Хранятся 1 год после завершения проекта
• Можете запросить удаление в любой момент

**4. Безопасность**
Мы обеспечиваем защиту данных:
• SSL-шифрование соединения
• Регулярное обновление защиты
• Резервное копирование данных

**5. Ваши права**
Вы имеете право:
• Знать, какие данные мы храним
• Запросить копию ваших данных
• Исправить неточности
• Удалить свои данные
• Отозвать согласие на обработку

📞 По вопросам защиты данных: @annasultanova29"""
    
    bot.send_message(message.chat.id, policy_text)
    show_main_menu(message.chat.id)

# ========== СТАРЫЕ ОБРАБОТЧИКИ (оставляем как есть) ==========
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
                f"""🎉 {session['name']}, заявка принята!

✅ Я получил ваши данные:
• Имя: {session['name']}
• Телефон: {session['phone']}
• Telegram: {session['telegram']}
• Год свадьбы: {session['date']}

📞 Свяжусь с вами в Telegram в течение 24 часов для обсуждения деталей.

А пока посмотрите пример свадебного сайта: {WEBSITE_URL}""",
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

# ========== FLASK РОУТЫ ==========
@app.route('/')
def home():
    return f"""
    <html>
        <head><title>Wedding Bot</title></head>
        <body style="text-align:center;padding:50px;font-family:Arial;">
            <h1>🤵👰 Wedding Bot</h1>
            <p style="color:green;font-size:24px;">✅ Бот работает через веб-хук!</p>
            <p>Сайт-пример: <a href="{WEBSITE_URL}" target="_blank">{WEBSITE_URL}</a></p>
            <p style="margin-top:50px;">Токен: {TOKEN[:10]}...</p>
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
        
        # Важно: НЕ запускаем polling!
        
    except Exception as e:
        logger.error(f"❌ Ошибка веб-хука: {e}")

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    logger.info("🚀 Запуск бота с веб-хуками...")
    logger.info(f"🤖 Токен: {TOKEN[:10]}...")
    logger.info(f"👑 Админ: {ADMIN_CHAT_ID}")
    logger.info(f"👥 Группа: {GROUP_CHAT_ID}")
    logger.info(f"🌐 Сайт: {WEBSITE_URL}")
    
    init_db()
    
    # Настраиваем веб-хук
    setup_webhook()
    
    # Запускаем Flask
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🌐 Запуск Flask на порту {port}")
    
    # ВАЖНО: НЕ запускаем bot.polling() - только Flask!
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
