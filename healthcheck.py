
#!/usr/bin/env python3
"""
Полная проверка системы Forex Bot
Проверяет переменные окружения, подключение к БД, таблицы и основные функции
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

def check_environment_variables():
    """Проверка переменных окружения"""
    print("🔍 Проверка переменных окружения...")
    
    load_dotenv()
    
    required_vars = {
        'DATABASE_URL': os.getenv('DATABASE_URL'),
        'TELEGRAM_BOT_TOKEN': os.getenv('TELEGRAM_BOT_TOKEN'),
        'WEBHOOK_URL': os.getenv('WEBHOOK_URL'),
        'BOT_MODE': os.getenv('BOT_MODE')
    }
    
    optional_vars = {
        'RENDER_API_KEY': os.getenv('RENDER_API_KEY'),
        'REDIS_URL': os.getenv('REDIS_URL')
    }
    
    all_good = True
    
    print("\n📋 Обязательные переменные:")
    for var_name, var_value in required_vars.items():
        status = "✅" if var_value else "❌"
        print(f"  {var_name}: {status}")
        if not var_value:
            all_good = False
    
    print("\n📋 Опциональные переменные:")
    for var_name, var_value in optional_vars.items():
        status = "✅" if var_value else "⚠️"
        print(f"  {var_name}: {status}")
    
    return all_good, required_vars

def check_database_connection(database_url):
    """Проверка подключения к базе данных"""
    print("\n🔗 Проверка подключения к базе данных...")
    
    if not database_url:
        print("❌ DATABASE_URL не установлена")
        return False
    
    try:
        from app.database.connection import create_database_engine
        engine = create_database_engine()
        
        if not engine:
            print("❌ Не удалось создать engine базы данных")
            return False
        
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Подключение успешно! PostgreSQL: {version[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return False

def check_database_tables():
    """Проверка существования таблиц"""
    print("\n📊 Проверка таблиц базы данных...")
    
    try:
        from app.database.connection import create_database_engine
        engine = create_database_engine()
        
        if not engine:
            print("❌ Engine базы данных недоступен")
            return False
        
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result.fetchall()]
        
        expected_tables = [
            'bot_users',
            'currencies', 
            'impact_levels',
            'news_events',
            'scraping_logs',
            'user_currency_preferences',
            'user_notification_settings'
        ]
        
        print(f"📋 Найдено таблиц: {len(tables)}")
        
        missing_tables = []
        for table in expected_tables:
            if table in tables:
                print(f"  ✅ {table}")
            else:
                print(f"  ❌ {table} - отсутствует")
                missing_tables.append(table)
        
        if missing_tables:
            print(f"\n⚠️  Отсутствуют таблицы: {', '.join(missing_tables)}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка проверки таблиц: {e}")
        return False

def test_basic_functionality():
    """Тестирование основных функций"""
    print("\n🧪 Тестирование основных функций...")
    
    try:
        # Тест создания пользователя
        from app.database.connection import get_db_session
        from app.database.models import BotUser
        
        db = get_db_session()
        if not db:
            print("❌ Не удалось получить сессию БД")
            return False
        
        # Проверяем, можем ли мы выполнить простой запрос
        test_user = db.query(BotUser).first()
        print("✅ Запрос к таблице bot_users выполнен успешно")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования функций: {e}")
        return False

def check_telegram_bot_token(bot_token):
    """Проверка токена Telegram бота"""
    print("\n🤖 Проверка токена Telegram бота...")
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN не установлен")
        return False
    
    if bot_token.startswith('your_'):
        print("❌ TELEGRAM_BOT_TOKEN содержит placeholder значение")
        return False
    
    # Проверяем формат токена
    if ':' not in bot_token or len(bot_token.split(':')) != 2:
        print("❌ Неверный формат токена (должен быть: bot_id:token)")
        return False
    
    try:
        import requests
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=10)
        
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get('ok'):
                bot_data = bot_info['result']
                print(f"✅ Токен валиден! Бот: @{bot_data.get('username', 'unknown')}")
                return True
            else:
                print(f"❌ Ошибка API: {bot_info.get('description', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP ошибка: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка проверки токена: {e}")
        return False

def explain_render_api_key():
    """Объяснение про RENDER_API_KEY"""
    print("\n🔑 Информация о RENDER_API_KEY:")
    print("=" * 50)
    print("RENDER_API_KEY - это опциональная переменная для программного управления Render.")
    print("\n📝 Что это дает:")
    print("  • Автоматическое управление переменными окружения")
    print("  • Программный деплой и перезапуск сервисов")
    print("  • Мониторинг статуса сервисов через API")
    print("\n🔧 Как получить:")
    print("  1. Зайдите в Render Dashboard")
    print("  2. Перейдите в Account Settings")
    print("  3. Создайте новый API Key")
    print("  4. Добавьте его в Environment Variables как RENDER_API_KEY")
    print("\n⚠️  Альтернативы:")
    print("  • Управление через веб-интерфейс Render")
    print("  • Использование Render CLI")
    print("  • Ручная настройка переменных окружения")
    print("\n✅ Вывод: RENDER_API_KEY не обязателен для работы бота!")

def main():
    """Основная функция проверки"""
    print("🚀 ПОЛНАЯ ПРОВЕРКА СИСТЕМЫ FOREX BOT")
    print("=" * 60)
    print(f"Время проверки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Проверка переменных окружения
    env_ok, env_vars = check_environment_variables()
    
    # Проверка подключения к БД
    db_connection_ok = check_database_connection(env_vars['DATABASE_URL'])
    
    # Проверка таблиц
    db_tables_ok = check_database_tables() if db_connection_ok else False
    
    # Тестирование функций
    functionality_ok = test_basic_functionality() if db_tables_ok else False
    
    # Проверка токена бота
    bot_token_ok = check_telegram_bot_token(env_vars['TELEGRAM_BOT_TOKEN'])
    
    # Объяснение про RENDER_API_KEY
    explain_render_api_key()
    
    # Итоговый отчет
    print("\n" + "=" * 60)
    print("📋 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 60)
    
    checks = [
        ("Переменные окружения", env_ok),
        ("Подключение к БД", db_connection_ok),
        ("Таблицы БД", db_tables_ok),
        ("Основные функции", functionality_ok),
        ("Токен Telegram бота", bot_token_ok)
    ]
    
    passed = 0
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
        if result:
            passed += 1
    
    print(f"\n📊 Результат: {passed}/{len(checks)} проверок пройдено")
    
    if passed == len(checks):
        print("\n🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Система готова к работе!")
        return True
    else:
        print(f"\n⚠️  ОБНАРУЖЕНЫ ПРОБЛЕМЫ! Исправьте {len(checks) - passed} ошибок.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
