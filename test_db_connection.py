
#!/usr/bin/env python3
"""
Скрипт для тестирования подключения к PostgreSQL базе данных на Render.
Использует DATABASE_URL из переменных окружения.
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def test_database_connection():
    """Тестирует подключение к базе данных PostgreSQL"""
    
    # Получаем DATABASE_URL из переменных окружения
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ ОШИБКА: Переменная окружения DATABASE_URL не найдена!")
        print("Убедитесь, что вы установили DATABASE_URL:")
        print("export DATABASE_URL='postgresql://user:password@host:port/database'")
        return False
    
    print(f"🔍 Найдена DATABASE_URL: {database_url[:50]}...")
    
    # Парсим URL для получения компонентов
    try:
        parsed = urlparse(database_url)
        print(f"📊 Компоненты подключения:")
        print(f"   Схема: {parsed.scheme}")
        print(f"   Хост: {parsed.hostname}")
        print(f"   Порт: {parsed.port or 5432}")
        print(f"   База данных: {parsed.path[1:] if parsed.path else 'не указана'}")
        print(f"   Пользователь: {parsed.username}")
        print(f"   Пароль: {'*' * len(parsed.password) if parsed.password else 'не указан'}")
        
        # Проверяем правильность схемы
        if parsed.scheme not in ['postgresql', 'postgres']:
            print(f"⚠️  ПРЕДУПРЕЖДЕНИЕ: Схема '{parsed.scheme}' может быть неправильной.")
            print("   Рекомендуется использовать 'postgresql://' вместо 'postgres://'")
            
    except Exception as e:
        print(f"❌ ОШИБКА при парсинге URL: {e}")
        return False
    
    # Пытаемся подключиться к базе данных
    print("\n🔄 Попытка подключения к базе данных...")
    
    try:
        # Подключаемся к базе данных
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Выполняем простой запрос для проверки
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        
        # Получаем информацию о текущей базе данных
        cursor.execute("SELECT current_database();")
        current_db = cursor.fetchone()[0]
        
        # Получаем информацию о пользователе
        cursor.execute("SELECT current_user;")
        current_user = cursor.fetchone()[0]
        
        print("✅ УСПЕШНО! Подключение к базе данных установлено!")
        print(f"📋 Информация о базе данных:")
        print(f"   Версия PostgreSQL: {version}")
        print(f"   Текущая база данных: {current_db}")
        print(f"   Текущий пользователь: {current_user}")
        
        # Закрываем соединение
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ ОШИБКА подключения: {e}")
        print("\n🔧 Возможные причины:")
        print("   1. Неправильные учетные данные (пользователь/пароль)")
        print("   2. Неправильный хост или порт")
        print("   3. База данных недоступна")
        print("   4. Проблемы с сетью или SSL")
        print("   5. База данных не существует")
        return False
        
    except Exception as e:
        print(f"❌ НЕОЖИДАННАЯ ОШИБКА: {e}")
        return False

def main():
    """Главная функция"""
    print("🚀 Тестирование подключения к PostgreSQL на Render")
    print("=" * 50)
    
    success = test_database_connection()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Тест завершен успешно! База данных доступна.")
        sys.exit(0)
    else:
        print("❌ Тест не пройден. Проверьте настройки подключения.")
        sys.exit(1)

if __name__ == "__main__":
    main()
