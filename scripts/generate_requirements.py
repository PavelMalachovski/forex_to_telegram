#!/usr/bin/env python3
"""
Автоматическая генерация requirements.txt на основе импортов в проекте
Использование: python scripts/generate_requirements.py
"""

import pathlib
import re
import sys
import subprocess
from typing import Set, List

def get_stdlib_modules() -> Set[str]:
    """Получить список модулей стандартной библиотеки Python"""
    return {
        'os', 'sys', 'time', 'datetime', 'json', 'logging', 'threading', 'signal',
        'traceback', 'gc', 'pathlib', 're', 'collections', 'functools', 'itertools',
        'typing', 'asyncio', 'concurrent', 'multiprocessing', 'subprocess', 'shutil',
        'tempfile', 'urllib', 'http', 'socket', 'ssl', 'hashlib', 'base64', 'uuid',
        'random', 'math', 'decimal', 'fractions', 'statistics', 'copy', 'pickle',
        'csv', 'configparser', 'argparse', 'getpass', 'platform', 'warnings',
        'contextlib', 'weakref', 'abc', 'enum', 'dataclasses', 'operator', 'sqlite3',
        'calendar', 'email', 'html', 'xml', 'zipfile', 'tarfile', 'gzip', 'bz2'
    }

def extract_imports_from_project(project_path: pathlib.Path) -> Set[str]:
    """Извлечь все импорты из Python файлов проекта"""
    python_files = list(project_path.rglob('*.py'))
    
    # Исключить виртуальные окружения и кэш
    python_files = [
        f for f in python_files 
        if not any(part.startswith('.') or part in ['test_env', '__pycache__', 'venv', 'env', 'build', 'dist'] 
                  for part in f.parts)
    ]
    
    print(f"Анализируем {len(python_files)} Python файлов...")
    
    imports = set()
    for py_file in python_files:
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            for line in content.splitlines():
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    # Извлечь имя модуля
                    if line.startswith('import '):
                        match = re.match(r'^import\s+([a-zA-Z0-9_\.]+)', line)
                    elif line.startswith('from '):
                        match = re.match(r'^from\s+([a-zA-Z0-9_\.]+)', line)
                    
                    if match:
                        module = match.group(1).split('.')[0]
                        imports.add(module)
        except Exception as e:
            print(f"Ошибка при чтении {py_file}: {e}", file=sys.stderr)
    
    return imports

def get_installed_version(package: str) -> str:
    """Получить версию установленного пакета"""
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'show', package], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith('Version:'):
                    return line.split(':', 1)[1].strip()
    except Exception:
        pass
    return "latest"

def main():
    project_path = pathlib.Path('.')
    
    # Извлечь все импорты
    all_imports = extract_imports_from_project(project_path)
    
    # Исключить стандартную библиотеку
    stdlib_modules = get_stdlib_modules()
    third_party = sorted(all_imports - stdlib_modules)
    
    # Исключить локальные модули проекта
    local_modules = {'app', 'api_server', 'webhook_utils'}  # Добавить другие локальные модули
    third_party = [mod for mod in third_party if mod not in local_modules]
    
    print(f"\nНайдено {len(third_party)} сторонних модулей:")
    
    # Создать requirements с версиями
    requirements_lines = [
        "# Auto-generated requirements.txt",
        f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "# Third-party dependencies:"
    ]
    
    for module in third_party:
        version = get_installed_version(module)
        if version != "latest":
            requirements_lines.append(f"{module}=={version}")
            print(f"  {module}=={version}")
        else:
            requirements_lines.append(f"{module}")
            print(f"  {module} (version not found)")
    
    # Записать в файл
    output_file = project_path / 'config' / 'requirements.auto.txt'
    output_file.write_text('\n'.join(requirements_lines) + '\n')
    
    print(f"\nRequirements сохранены в: {output_file}")
    print("\nРекомендация: проверьте файл и скопируйте в requirements.production.txt")

if __name__ == '__main__':
    from datetime import datetime
    main()
