import requests
import time
import threading

def keep_alive():
    """Отправляет запросы каждые 5 минут чтобы Render не спал"""
    while True:
        try:
            # Ваш URL на Render
            response = requests.get('https://your-bot-name.onrender.com/health')
            print(f"✅ Keep-alive: {response.status_code} - {time.ctime()}")
        except Exception as e:
            print(f"❌ Keep-alive error: {e}")
        time.sleep(300)  # 5 минут

# Запуск в отдельном потоке
threading.Thread(target=keep_alive, daemon=True).start()
