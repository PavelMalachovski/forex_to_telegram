
#!/usr/bin/env python3
"""
Скрипт для проверки существования таблиц базы данных
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Ожидаемые таблицы для Telegram бота
EXPECTED_TABLES = [
    'users',
    'user_settings', 
    'notifications',
    'forex_data',
    'trading_signals',
    'user_subscriptions',
    'alembic_version'  # Таблица миграций Alembic
]

def get_database_connection():
    """Получение подключения к базе данных"""
    load_dotenv()
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL не найдена в переменных окружения")
        sys.exit(1)
    
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"❌ Ошибка подключения к базе данных: {e}")
        sys.exit(1)

def get_existing_tables(cursor):
    """Получение списка существующих таблиц"""
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    return [row[0] for row in cursor.fetchall()]

def get_table_info(cursor, table_name):
    """Получение информации о структуре таблицы"""
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position;
    """, (table_name,))
    return cursor.fetchall()

def check_table_structure(cursor, table_name):
    """Проверка структуры конкретной таблицы"""
    print(f"\n📊 Таблица: {table_name}")
    
    try:
        # Получаем информацию о колонках
        columns = get_table_info(cursor, table_name)
        
        if not columns:
            print("  ⚠️  Таблица пуста или недоступна")
            return False
        
        print(f"  Колонок: {len(columns)}")
        for col in columns:
            nullable = "NULL" if col[2] == "YES" else "NOT NULL"
            default = f" DEFAULT {col[3]}" if col[3] else ""
            print(f"    - {col[0]}: {col[1]} {nullable}{default}")
        
        # Проверяем количество записей
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        print(f"  Записей: {count}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка при проверке таблицы: {e}")
        return False

def check_alembic_version(cursor):
    """Проверка версии миграций Alembic"""
    try:
        cursor.execute("SELECT version_num FROM alembic_version;")
        version = cursor.fetchone()
        if version:
            print(f"🔄 Текущая версия миграции: {version[0]}")
            return version[0]
        else:
            print("⚠️  Версия миграции не найдена")
            return None
    except Exception as e:
        print(f"❌ Ошибка при проверке версии Alembic: {e}")
        return None

def main():
    print("🔍 Проверка таблиц базы данных для Telegram бота\n")
    
    # Подключаемся к базе данных
    conn = get_database_connection()
    cursor = conn.cursor()
    
    try:
        # Получаем список существующих таблиц
        existing_tables = get_existing_tables(cursor)
        
        print(f"📋 Найдено таблиц в базе данных: {len(existing_tables)}")
        
        if not existing_tables:
            print("❌ Таблицы не найдены! Необходимо выполнить миграции.")
            return
        
        # Проверяем каждую ожидаемую таблицу
        missing_tables = []
        existing_expected = []
        
        for table in EXPECTED_TABLES:
            if table in existing_tables:
                existing_expected.append(table)
                check_table_structure(cursor, table)
            else:
                missing_tables.append(table)
        
        # Проверяем версию Alembic
        print("\n" + "="*50)
        alembic_version = check_alembic_version(cursor)
        
        # Показываем дополнительные таблицы
        extra_tables = [t for t in existing_tables if t not in EXPECTED_TABLES]
        if extra_tables:
            print(f"\n📊 Дополнительные таблицы: {', '.join(extra_tables)}")
        
        # Итоговый отчет
        print("\n" + "="*50)
        print("📋 ИТОГОВЫЙ ОТЧЕТ:")
        print("="*50)
        
        print(f"✅ Существующие таблицы ({len(existing_expected)}): {', '.join(existing_expected)}")
        
        if missing_tables:
            print(f"❌ Отсутствующие таблицы ({len(missing_tables)}): {', '.join(missing_tables)}")
            print("\n🔧 НЕОБХОДИМЫЕ ДЕЙСТВИЯ:")
            print("1. Выполните миграции: python -m alembic upgrade head")
            print("2. Или создайте недостающие таблицы вручную")
            sys.exit(1)
        else:
            print("✅ Все ожидаемые таблицы присутствуют!")
        
        if alembic_version:
            print(f"✅ Миграции актуальны (версия: {alembic_version})")
        else:
            print("⚠️  Статус миграций неизвестен")
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
