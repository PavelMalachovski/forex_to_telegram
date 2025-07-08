#!/usr/bin/env python3
"""
Тест исправлений Telegram бота.
"""

import sys
from datetime import date, timedelta
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

def test_news_service_fallback():
    """Тест NewsService в fallback режиме."""
    print("🧪 Тестирование NewsService в fallback режиме...")
    
    try:
        from app.services.news_service import NewsService
        
        # Создаем NewsService без базы данных (fallback режим)
        news_service = NewsService(db=None)
        
        # Тестируем методы
        today = date.today()
        
        # Тест has_data_for_date
        result = news_service.has_data_for_date(today)
        print(f"✅ has_data_for_date({today}): {result}")
        assert result == False, "В fallback режиме должно возвращать False"
        
        # Тест get_events_by_date_range
        events = news_service.get_events_by_date_range(today, today + timedelta(days=1))
        print(f"✅ get_events_by_date_range: {len(events)} событий")
        assert events == [], "В fallback режиме должно возвращать пустой список"
        
        # Тест get_news_by_date
        news = news_service.get_news_by_date(today)
        print(f"✅ get_news_by_date: {len(news)} новостей")
        assert news == [], "В fallback режиме должно возвращать пустой список"
        
        # Тест get_event_statistics
        stats = news_service.get_event_statistics()
        print(f"✅ get_event_statistics: {stats.get('status', 'unknown')}")
        assert stats.get('status') == 'database_unavailable', "Должен указывать на недоступность БД"
        
        print("✅ Все тесты NewsService в fallback режиме прошли успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте NewsService: {e}")
        return False

def test_bot_handlers_import():
    """Тест импорта BotHandlers."""
    print("🧪 Тестирование импорта BotHandlers...")
    
    try:
        from app.bot.handlers import BotHandlers
        print("✅ BotHandlers импортирован успешно")
        
        # Проверяем, что класс имеет нужные методы
        required_methods = [
            'start_command', 'help_command', 'today_command', 
            'tomorrow_command', 'week_command', 'preferences_command', 
            'status_command'
        ]
        
        for method_name in required_methods:
            if hasattr(BotHandlers, method_name):
                print(f"✅ Метод {method_name} найден")
            else:
                print(f"❌ Метод {method_name} не найден")
                return False
        
        print("✅ Все необходимые методы BotHandlers найдены!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте BotHandlers: {e}")
        return False

def test_database_connection():
    """Тест подключения к базе данных."""
    print("🧪 Тестирование подключения к базе данных...")
    
    try:
        from app.database.connection import get_db_session, SessionLocal
        
        # Тест получения сессии
        session = get_db_session()
        if session is None:
            print("✅ База данных недоступна - корректно возвращается None")
        else:
            print("✅ Сессия базы данных получена")
            session.close()
        
        # Тест SessionLocal
        if SessionLocal is None:
            print("✅ SessionLocal is None - корректно для недоступной БД")
        else:
            print("✅ SessionLocal доступен")
        
        print("✅ Тест подключения к базе данных прошел успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте подключения к БД: {e}")
        return False

def test_production_scheduler():
    """Тест production_scheduler."""
    print("🧪 Тестирование production_scheduler...")
    
    try:
        import production_scheduler
        
        # Проверяем, что основные функции определены
        required_functions = [
            'setup_enhanced_logging', 'create_flask_app', 
            'create_telegram_bot', 'main'
        ]
        
        for func_name in required_functions:
            if hasattr(production_scheduler, func_name):
                print(f"✅ Функция {func_name} найдена")
            else:
                print(f"❌ Функция {func_name} не найдена")
                return False
        
        print("✅ Все необходимые функции production_scheduler найдены!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте production_scheduler: {e}")
        return False

def main():
    """Основная функция тестирования."""
    print("🚀 Запуск тестов исправлений Telegram бота...")
    print("=" * 60)
    
    tests = [
        test_news_service_fallback,
        test_bot_handlers_import,
        test_database_connection,
        test_production_scheduler
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        print()
        if test_func():
            passed += 1
        print("-" * 40)
    
    print()
    print("=" * 60)
    print(f"📊 Результаты тестирования: {passed}/{total} тестов прошли успешно")
    
    if passed == total:
        print("🎉 Все тесты прошли успешно! Исправления работают корректно.")
        return 0
    else:
        print("⚠️  Некоторые тесты не прошли. Требуется дополнительная проверка.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
