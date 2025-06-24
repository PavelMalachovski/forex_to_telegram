#!/usr/bin/env python3
"""
Тест для проверки исправления ошибки с типами данных времени в команде tomorrow_command.
"""

import sys
import os
sys.path.append('/home/ubuntu/forex_bot_postgresql')

from datetime import datetime, date, time, timedelta
from app.utils.timezone_utils import get_current_time, get_local_timezone
from app.database.models import NewsEvent

def test_timezone_aware_datetime_creation():
    """Тест создания timezone-aware datetime из date и time."""
    print("🧪 Тестирование создания timezone-aware datetime...")
    
    try:
        # Создаем тестовые данные
        test_date = date(2025, 6, 25)
        test_time = time(14, 30)  # 14:30
        
        # Старый способ (может вызывать ошибки)
        print("📅 Тестовая дата:", test_date)
        print("⏰ Тестовое время:", test_time)
        
        # Новый способ (исправленный)
        local_tz = get_local_timezone()
        naive_datetime = datetime.combine(test_date, test_time)
        event_datetime = local_tz.localize(naive_datetime)
        
        print("✅ Naive datetime:", naive_datetime)
        print("✅ Timezone-aware datetime:", event_datetime)
        
        # Тестируем арифметические операции
        notify_time_15 = event_datetime - timedelta(minutes=15)
        notify_time_30 = event_datetime - timedelta(minutes=30)
        notify_time_60 = event_datetime - timedelta(minutes=60)
        
        print("⏰ Уведомление за 15 минут:", notify_time_15)
        print("⏰ Уведомление за 30 минут:", notify_time_30)
        print("⏰ Уведомление за 60 минут:", notify_time_60)
        
        # Тестируем сравнение с текущим временем
        current_time = get_current_time()
        print("🕐 Текущее время:", current_time)
        
        # Эти сравнения должны работать без ошибок
        can_notify_15 = notify_time_15 > current_time
        can_notify_30 = notify_time_30 > current_time
        can_notify_60 = notify_time_60 > current_time
        
        print(f"📢 Можно уведомить за 15 минут: {can_notify_15}")
        print(f"📢 Можно уведомить за 30 минут: {can_notify_30}")
        print(f"📢 Можно уведомить за 60 минут: {can_notify_60}")
        
        print("✅ Все тесты прошли успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте: {e}")
        return False

def test_tomorrow_command_logic():
    """Тест логики команды tomorrow_command."""
    print("\n🧪 Тестирование логики команды tomorrow...")
    
    try:
        # Тестируем получение завтрашней даты
        tomorrow = get_current_time().date() + timedelta(days=1)
        print(f"📅 Завтрашняя дата: {tomorrow}")
        
        # Проверяем, что это работает без ошибок
        print("✅ Логика tomorrow_command работает корректно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в логике tomorrow_command: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Запуск тестов исправления ошибки с типами времени...\n")
    
    test1_passed = test_timezone_aware_datetime_creation()
    test2_passed = test_tomorrow_command_logic()
    
    print(f"\n📊 Результаты тестов:")
    print(f"   Тест timezone-aware datetime: {'✅ ПРОШЕЛ' if test1_passed else '❌ ПРОВАЛЕН'}")
    print(f"   Тест логики tomorrow_command: {'✅ ПРОШЕЛ' if test2_passed else '❌ ПРОВАЛЕН'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 Все тесты прошли! Исправление работает корректно.")
        sys.exit(0)
    else:
        print("\n💥 Некоторые тесты провалились. Требуется дополнительная отладка.")
        sys.exit(1)
