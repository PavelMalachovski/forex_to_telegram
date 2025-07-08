
#!/usr/bin/env python3
"""
Быстрая проверка токена Telegram бота
"""

import os
import requests
from dotenv import load_dotenv

def check_telegram_token():
    """Проверка токена Telegram бота"""
    load_dotenv()
    
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN не найден в .env")
        return False
    
    if token.startswith('your_'):
        print("❌ TELEGRAM_BOT_TOKEN содержит placeholder значение")
        print(f"Текущее значение: {token}")
        return False
    
    print(f"🔍 Проверяем токен: {token[:10]}...")
    
    try:
        response = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get('ok'):
                bot_data = bot_info['result']
                print(f"✅ Токен валиден!")
                print(f"🤖 Бот: @{bot_data.get('username', 'unknown')}")
                print(f"📝 Имя: {bot_data.get('first_name', 'Unknown')}")
                print(f"🆔 ID: {bot_data.get('id', 'Unknown')}")
                return True
            else:
                print(f"❌ Ошибка API: {bot_info.get('description', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            if response.status_code == 401:
                print("💡 Токен недействителен. Получите новый от @BotFather")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")
        return False

def main():
    print("🤖 ПРОВЕРКА ТОКЕНА TELEGRAM БОТА")
    print("=" * 40)
    
    if check_telegram_token():
        print("\n🎉 Токен работает! Бот готов к использованию.")
    else:
        print("\n🔧 КАК ИСПРАВИТЬ:")
        print("1. Перейдите к @BotFather в Telegram")
        print("2. Найдите вашего бота или создайте нового")
        print("3. Получите токен командой /token")
        print("4. Обновите TELEGRAM_BOT_TOKEN в .env или Render")
        print("5. Перезапустите приложение")

if __name__ == "__main__":
    main()
