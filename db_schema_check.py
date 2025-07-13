#!/usr/bin/env python3
"""
Скрипт для проверки соответствия структуры базы данных моделям SQLAlchemy
"""

import os
import sys
from typing import Dict, List, Set
from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.engine import Inspector

# Добавляем путь к проекту
sys.path.insert(0, '/home/ubuntu/forex_bot_postgresql')

# Устанавливаем переменную окружения для базы данных
os.environ['DATABASE_URL'] = 'postgresql://forex_user:0VGr0I02HDKaiVUVT21Z3ORnEiCBAYtC@dpg-d1mkim2li9vc73c7toi0-a.oregon-postgres.render.com:5432/forex_db_0myg'

from app.database.models import Base

def get_model_tables() -> Dict[str, Set[str]]:
    """Получить таблицы и колонки из моделей SQLAlchemy"""
    model_tables = {}
    
    for table_name, table in Base.metadata.tables.items():
        columns = set(column.name for column in table.columns)
        model_tables[table_name] = columns
    
    return model_tables

def get_db_tables(inspector: Inspector) -> Dict[str, Set[str]]:
    """Получить таблицы и колонки из базы данных"""
    db_tables = {}
    
    for table_name in inspector.get_table_names():
        columns = set(column['name'] for column in inspector.get_columns(table_name))
        db_tables[table_name] = columns
    
    return db_tables

def compare_schemas(model_tables: Dict[str, Set[str]], db_tables: Dict[str, Set[str]]) -> bool:
    """Сравнить схемы моделей и базы данных"""
    
    print("🔍 Проверка соответствия схемы базы данных моделям SQLAlchemy\n")
    
    all_good = True
    
    # Проверяем таблицы, которые есть в моделях, но отсутствуют в БД
    missing_tables = set(model_tables.keys()) - set(db_tables.keys())
    if missing_tables:
        print(f"❌ Таблицы отсутствуют в БД: {missing_tables}")
        all_good = False
    
    # Проверяем таблицы, которые есть в БД, но отсутствуют в моделях
    extra_tables = set(db_tables.keys()) - set(model_tables.keys())
    if extra_tables:
        print(f"⚠️  Дополнительные таблицы в БД (не в моделях): {extra_tables}")
    
    # Проверяем колонки для каждой таблицы
    for table_name in model_tables.keys():
        if table_name not in db_tables:
            continue
            
        model_columns = model_tables[table_name]
        db_columns = db_tables[table_name]
        
        # Колонки, которые есть в модели, но отсутствуют в БД
        missing_columns = model_columns - db_columns
        if missing_columns:
            print(f"❌ Таблица '{table_name}': отсутствующие колонки в БД: {missing_columns}")
            all_good = False
        
        # Колонки, которые есть в БД, но отсутствуют в модели
        extra_columns = db_columns - model_columns
        if extra_columns:
            print(f"⚠️  Таблица '{table_name}': дополнительные колонки в БД: {extra_columns}")
        
        # Если все колонки совпадают
        if not missing_columns and not extra_columns:
            print(f"✅ Таблица '{table_name}': все колонки совпадают")
    
    return all_good

def check_specific_table(inspector: Inspector, table_name: str) -> None:
    """Детальная проверка конкретной таблицы"""
    
    print(f"\n📋 Детальная информация о таблице '{table_name}':")
    
    try:
        columns = inspector.get_columns(table_name)
        
        print(f"Колонки в БД ({len(columns)}):")
        for column in columns:
            nullable = "NULL" if column['nullable'] else "NOT NULL"
            default = f", default: {column['default']}" if column['default'] else ""
            print(f"  - {column['name']}: {column['type']} ({nullable}{default})")
        
        # Проверяем индексы
        indexes = inspector.get_indexes(table_name)
        if indexes:
            print(f"\nИндексы ({len(indexes)}):")
            for index in indexes:
                unique = "UNIQUE " if index['unique'] else ""
                print(f"  - {unique}{index['name']}: {index['column_names']}")
        
        # Проверяем внешние ключи
        foreign_keys = inspector.get_foreign_keys(table_name)
        if foreign_keys:
            print(f"\nВнешние ключи ({len(foreign_keys)}):")
            for fk in foreign_keys:
                print(f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
                
    except Exception as e:
        print(f"❌ Ошибка при получении информации о таблице: {e}")

def main():
    """Основная функция"""
    
    try:
        # Подключаемся к базе данных
        database_url = os.environ['DATABASE_URL']
        engine = create_engine(database_url)
        inspector = inspect(engine)
        
        # Получаем схемы
        model_tables = get_model_tables()
        db_tables = get_db_tables(inspector)
        
        # Сравниваем схемы
        schemas_match = compare_schemas(model_tables, db_tables)
        
        # Детальная проверка таблицы user_notification_settings
        if 'user_notification_settings' in db_tables:
            check_specific_table(inspector, 'user_notification_settings')
        
        print(f"\n{'='*60}")
        if schemas_match:
            print("🎉 Схема базы данных полностью соответствует моделям!")
        else:
            print("⚠️  Обнаружены несоответствия в схеме базы данных.")
            print("   Рекомендуется создать и выполнить миграцию Alembic.")
        
        return schemas_match
        
    except Exception as e:
        print(f"❌ Ошибка при проверке схемы: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
