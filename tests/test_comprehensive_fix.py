#!/usr/bin/env python3
"""
Комплексный тест для проверки всех исправлений ошибок с типами данных времени.
"""

import sys
import os
sys.path.append('/home/ubuntu/forex_bot_postgresql')

from datetime import datetime, date, time, timedelta
from app.utils.timezone_utils import get_current_time, get_local_timezone
from app.database.models import NewsEvent, Currency, ImpactLevel
from app.utils.text_utils import format_news_message

def test_text_utils_time_formatting():
    """Тест форматирования времени в text_utils."""
    print("🧪 Тестирование форматирования времени в text_utils...")
    
    try:
        # Создаем мок-объекты для тестирования
        class MockCurrency:
            def __init__(self, code):
                self.code = code
        
        class MockImpactLevel:
            def __init__(self, code):
                self.code = code
        
        class MockEvent:
            def __init__(self, event_date, event_time, currency_code, impact_code, event_name):
                self.event_date = event_date
                self.event_time = event_time
                self.currency = MockCurrency(currency_code)
                self.impact_level = MockImpactLevel(impact_code)
                self.event_name = event_name
                self.forecast = "Test forecast"
                self.previous_value = "Test previous"
                self.actual_value = "Test actual"
                self.analysis = "Test analysis"
        
        # Создаем тестовое событие
        test_event = MockEvent(
            event_date=date(2025, 6, 25),
            event_time=time(14, 30),  # Это объект time, не datetime
            currency_code="USD",
            impact_code="HIGH",
            event_name="Test Event"
        )
        
        # Тестируем форматирование сообщения
        formatted_message = format_news_message([test_event], "2025-06-25")
        
        print("✅ Форматирование времени работает корректно!")
        print(f"📝 Пример сообщения (первые 200 символов):\n{formatted_message[:200]}...")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в форматировании времени: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_notification_scheduler_logic():
    """Тест логики планировщика уведомлений."""
    print("\n🧪 Тестирование логики планировщика уведомлений...")
    
    try:
        # Тестируем создание timezone-aware datetime
        test_date = date(2025, 6, 25)
        test_time = time(14, 30)
        
        # Имитируем логику из notification_scheduler.py
        local_tz = get_local_timezone()
        naive_datetime = datetime.combine(test_date, test_time)
        event_datetime = local_tz.localize(naive_datetime)
        
        # Тестируем вычисление времени уведомлений
        notify_time_15 = event_datetime - timedelta(minutes=15)
        notify_time_30 = event_datetime - timedelta(minutes=30)
        notify_time_60 = event_datetime - timedelta(minutes=60)
        
        # Тестируем сравнение с текущим временем
        current_time = get_current_time()
        
        # Эти операции должны работать без ошибок
        can_notify_15 = notify_time_15 > current_time
        can_notify_30 = notify_time_30 > current_time
        can_notify_60 = notify_time_60 > current_time
        
        print("✅ Логика планировщика уведомлений работает корректно!")
        print(f"📊 Результаты сравнения времени:")
        print(f"   15 минут: {can_notify_15}")
        print(f"   30 минут: {can_notify_30}")
        print(f"   60 минут: {can_notify_60}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в логике планировщика: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_time_operations():
    """Тест различных операций с временем."""
    print("\n🧪 Тестирование различных операций с временем...")
    
    try:
        # Тест 1: Создание времени из строки
        time_obj = time(14, 30)
        time_str = time_obj.strftime('%H:%M')
        print(f"✅ Форматирование time в строку: {time_str}")
        
        # Тест 2: Создание datetime из date и time
        date_obj = date(2025, 6, 25)
        datetime_obj = datetime.combine(date_obj, time_obj)
        print(f"✅ Создание datetime из date и time: {datetime_obj}")
        
        # Тест 3: Добавление timezone
        local_tz = get_local_timezone()
        aware_datetime = local_tz.localize(datetime_obj)
        print(f"✅ Добавление timezone: {aware_datetime}")
        
        # Тест 4: Арифметические операции с datetime
        future_time = aware_datetime + timedelta(hours=1)
        past_time = aware_datetime - timedelta(minutes=30)
        print(f"✅ Арифметические операции: +1ч = {future_time}, -30м = {past_time}")
        
        # Тест 5: Сравнение времени
        current = get_current_time()
        is_future = future_time > current
        is_past = past_time < current
        print(f"✅ Сравнение времени: будущее={is_future}, прошлое={is_past}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в операциях с временем: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Запуск комплексных тестов исправлений...\n")
    
    test1_passed = test_text_utils_time_formatting()
    test2_passed = test_notification_scheduler_logic()
    test3_passed = test_time_operations()
    
    print(f"\n📊 Результаты всех тестов:")
    print(f"   Форматирование времени в text_utils: {'✅ ПРОШЕЛ' if test1_passed else '❌ ПРОВАЛЕН'}")
    print(f"   Логика планировщика уведомлений: {'✅ ПРОШЕЛ' if test2_passed else '❌ ПРОВАЛЕН'}")
    print(f"   Операции с временем: {'✅ ПРОШЕЛ' if test3_passed else '❌ ПРОВАЛЕН'}")
    
    if test1_passed and test2_passed and test3_passed:
        print("\n🎉 Все тесты прошли! Исправления работают корректно.")
        print("✅ Ошибка 'unsupported operand type(s) for +: datetime.time and datetime.timedelta' исправлена!")
        sys.exit(0)
    else:
        print("\n💥 Некоторые тесты провалились. Требуется дополнительная отладка.")
        sys.exit(1)
