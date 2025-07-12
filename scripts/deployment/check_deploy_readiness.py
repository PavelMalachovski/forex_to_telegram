#!/usr/bin/env python3
"""
Скрипт проверки готовности к деплою после рефакторинга.
"""

import os
import sys
from pathlib import Path

def check_symlinks():
    """Проверка симлинков в корне проекта."""
    print("🔗 Проверка симлинков...")
    
    required_symlinks = {
        'Dockerfile': 'docker/Dockerfile.production',
        'Dockerfile.enhanced': 'docker/Dockerfile.enhanced',
        'Procfile': 'docker/Procfile'
    }
    
    all_good = True
    for symlink, target in required_symlinks.items():
        if os.path.islink(symlink):
            actual_target = os.readlink(symlink)
            if actual_target == target:
                print(f"  ✓ {symlink} -> {target}")
            else:
                print(f"  ✗ {symlink} -> {actual_target} (ожидался {target})")
                all_good = False
        else:
            print(f"  ✗ {symlink} не является симлинком")
            all_good = False
    
    return all_good

def check_config_files():
    """Проверка конфигурационных файлов."""
    print("\n📋 Проверка конфигурационных файлов...")
    
    configs = {
        'config/render.yaml': './Dockerfile',
        'config/render_enhanced.yaml': './Dockerfile.enhanced'
    }
    
    all_good = True
    for config_file, expected_dockerfile in configs.items():
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                content = f.read()
                if f'dockerfilePath: {expected_dockerfile}' in content:
                    print(f"  ✓ {config_file} содержит правильный dockerfilePath")
                else:
                    print(f"  ✗ {config_file} не содержит dockerfilePath: {expected_dockerfile}")
                    all_good = False
        else:
            print(f"  ✗ {config_file} не найден")
            all_good = False
    
    return all_good

def check_required_files():
    """Проверка обязательных файлов."""
    print("\n📁 Проверка обязательных файлов...")
    
    required_files = [
        'main.py',
        'production_scheduler.py',
        'enhanced_main.py',
        'config/production/requirements.production.txt',
        'config/production/requirements_enhanced.txt',
        'docker/Dockerfile.production',
        'docker/Dockerfile.enhanced'
    ]
    
    all_good = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} не найден")
            all_good = False
    
    return all_good

def check_imports():
    """Проверка критических импортов."""
    print("\n🐍 Проверка импортов...")
    
    # Добавляем текущую директорию в путь для импорта app
    current_dir = os.getcwd()
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    imports_to_check = [
        ('app.config', 'Config'),
        ('app.bot.handlers', 'BotHandlers'),
        ('app.database.models', 'User'),
        ('app.services.news_service', 'NewsService'),
        ('app.scrapers.forex_factory_scraper', 'ForexFactoryScraper')
    ]
    
    all_good = True
    for module_name, class_name in imports_to_check:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"  ✓ {module_name}.{class_name}")
        except ImportError as e:
            print(f"  ✗ {module_name}.{class_name}: {e}")
            all_good = False
        except AttributeError as e:
            print(f"  ✗ {module_name}.{class_name}: {e}")
            all_good = False
    
    return all_good

def main():
    """Основная функция проверки."""
    print("🚀 Проверка готовности к деплою Forex Bot\n")
    
    # Переходим в корень проекта
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    checks = [
        check_symlinks(),
        check_config_files(),
        check_required_files(),
        check_imports()
    ]
    
    print("\n" + "="*50)
    if all(checks):
        print("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Проект готов к деплою.")
        print("\nДля деплоя на Render:")
        print("1. Используйте config/render.yaml для стандартного деплоя")
        print("2. Используйте config/render_enhanced.yaml для расширенного деплоя (рекомендуется)")
        return 0
    else:
        print("❌ ЕСТЬ ПРОБЛЕМЫ! Исправьте ошибки перед деплоем.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
