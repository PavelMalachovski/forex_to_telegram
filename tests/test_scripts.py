#!/usr/bin/env python3
"""
Простой тест для проверки работы скриптов управления данными.
"""

import subprocess
import sys
import os
from datetime import date, timedelta

def run_command(command, input_text=None):
    """Выполнить команду и вернуть результат."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            input=input_text,
            timeout=60
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"
    except Exception as e:
        return False, "", str(e)

def test_clean_database_dry_run():
    """Тест предварительного просмотра очистки."""
    print("Тестирую предварительный просмотр очистки...")
    success, stdout, stderr = run_command("python clean_database.py --dry-run")
    
    if success and "РЕЖИМ ПРЕДВАРИТЕЛЬНОГО ПРОСМОТРА" in stdout:
        print("✓ Предварительный просмотр очистки работает")
        return True
    else:
        print("✗ Ошибка в предварительном просмотре очистки")
        print(f"Stdout: {stdout}")
        print(f"Stderr: {stderr}")
        return False

def test_bulk_load_single_day():
    """Тест загрузки данных за один день."""
    print("Тестирую загрузку данных за один день...")
    yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    success, stdout, stderr = run_command(f"python bulk_load_data.py --from {yesterday} --to {yesterday}")
    
    if success and "Загрузка данных завершена успешно" in stdout:
        print("✓ Загрузка данных за один день работает")
        return True
    else:
        print("✗ Ошибка при загрузке данных за один день")
        print(f"Stdout: {stdout}")
        print(f"Stderr: {stderr}")
        return False

def test_bulk_load_no_overwrite():
    """Тест загрузки без перезаписи."""
    print("Тестирую загрузку без перезаписи...")
    yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    success, stdout, stderr = run_command(f"python bulk_load_data.py --from {yesterday} --to {yesterday} --no-overwrite")
    
    if success and ("пропущено" in stdout.lower() or "skipped" in stdout.lower()):
        print("✓ Загрузка без перезаписи работает")
        return True
    else:
        print("✗ Ошибка при загрузке без перезаписи")
        print(f"Stdout: {stdout}")
        print(f"Stderr: {stderr}")
        return False

def test_help_commands():
    """Тест команд помощи."""
    print("Тестирую команды помощи...")
    
    # Тест help для clean_database
    success1, stdout1, stderr1 = run_command("python clean_database.py --help")
    
    # Тест help для bulk_load_data
    success2, stdout2, stderr2 = run_command("python bulk_load_data.py --help")
    
    if success1 and success2 and "usage:" in stdout1.lower() and "usage:" in stdout2.lower():
        print("✓ Команды помощи работают")
        return True
    else:
        print("✗ Ошибка в командах помощи")
        return False

def main():
    """Главная функция тестирования."""
    print("=== ТЕСТИРОВАНИЕ СКРИПТОВ УПРАВЛЕНИЯ ДАННЫМИ ===")
    print(f"Рабочая директория: {os.getcwd()}")
    print()
    
    tests = [
        test_help_commands,
        test_clean_database_dry_run,
        test_bulk_load_single_day,
        test_bulk_load_no_overwrite,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"✗ Ошибка в тесте {test.__name__}: {e}")
            print()
    
    print("=== РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ ===")
    print(f"Пройдено: {passed}/{total}")
    print(f"Успешность: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 Все тесты пройдены успешно!")
        return True
    else:
        print("❌ Некоторые тесты не пройдены")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
