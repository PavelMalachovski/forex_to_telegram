
#!/usr/bin/env python3
"""
Скрипт для проверки настроек переменных окружения в Render
"""

import os
import sys
import requests
from urllib.parse import urlparse
import psycopg2
from dotenv import load_dotenv

def check_local_env():
    """Проверка локальных переменных окружения"""
    print("🔍 Проверка локальных переменных окружения...")
    
    # Загружаем .env файл
    load_dotenv()
    
    database_url = os.getenv('DATABASE_URL')
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    webhook_url = os.getenv('WEBHOOK_URL')
    
    print(f"DATABASE_URL: {'✅ Установлена' if database_url else '❌ Не найдена'}")
    print(f"TELEGRAM_BOT_TOKEN: {'✅ Установлен' if bot_token else '❌ Не найден'}")
    print(f"WEBHOOK_URL: {'✅ Установлен' if webhook_url else '❌ Не найден'}")
    
    if database_url:
        parsed = urlparse(database_url)
        print(f"  - Хост: {parsed.hostname}")
        print(f"  - База данных: {parsed.path[1:] if parsed.path else 'Не указана'}")
        print(f"  - Пользователь: {parsed.username}")
    
    return database_url, bot_token, webhook_url

def test_database_connection(database_url):
    """Тестирование подключения к базе данных"""
    if not database_url:
        print("❌ DATABASE_URL не установлена")
        return False
    
    print("\n🔗 Тестирование подключения к базе данных...")
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Подключение успешно! PostgreSQL версия: {version[0]}")
        
        # Проверяем существующие таблицы
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        if tables:
            print(f"📊 Найдено таблиц: {len(tables)}")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("⚠️  Таблицы не найдены - необходимо выполнить миграции")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        return False

def check_render_api_access():
    """Проверка доступа к Render API (если есть API ключ)"""
    render_api_key = os.getenv('RENDER_API_KEY')
    
    if not render_api_key:
        print("\n⚠️  RENDER_API_KEY не установлен - программное управление переменными недоступно")
        return False
    
    print("\n🔑 Проверка доступа к Render API...")
    
    try:
        headers = {
            'Authorization': f'Bearer {render_api_key}',
            'Accept': 'application/json'
        }
        
        response = requests.get('https://api.render.com/v1/services', headers=headers)
        
        if response.status_code == 200:
            services = response.json()
            print(f"✅ API доступ работает! Найдено сервисов: {len(services)}")
            return True
        else:
            print(f"❌ Ошибка API: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при обращении к API: {e}")
        return False

def main():
    print("🚀 Проверка настроек Render для Telegram бота\n")
    
    # Проверяем локальные переменные
    database_url, bot_token, webhook_url = check_local_env()
    
    # Тестируем подключение к БД
    db_ok = test_database_connection(database_url)
    
    # Проверяем API доступ
    api_ok = check_render_api_access()
    
    print("\n" + "="*50)
    print("📋 ИТОГОВЫЙ ОТЧЕТ:")
    print("="*50)
    
    print(f"DATABASE_URL: {'✅' if database_url else '❌'}")
    print(f"Подключение к БД: {'✅' if db_ok else '❌'}")
    print(f"TELEGRAM_BOT_TOKEN: {'✅' if bot_token else '❌'}")
    print(f"WEBHOOK_URL: {'✅' if webhook_url else '❌'}")
    print(f"Render API: {'✅' if api_ok else '⚠️  (опционально)'}")
    
    if not database_url or not db_ok:
        print("\n❌ КРИТИЧЕСКИЕ ПРОБЛЕМЫ ОБНАРУЖЕНЫ!")
        print("Необходимо:")
        print("1. Установить DATABASE_URL в Render Environment Variables")
        print("2. Проверить доступность базы данных")
        sys.exit(1)
    
    if not bot_token:
        print("\n⚠️  TELEGRAM_BOT_TOKEN не установлен - бот не сможет работать")
    
    print("\n✅ Основные настройки в порядке!")

if __name__ == "__main__":
    main()
