# Управление зависимостями проекта

## Проблема

Вы столкнулись с повторяющимися ошибками типа `ModuleNotFoundError` при деплое:
- `ModuleNotFoundError: No module named 'loguru'`
- И другие недостающие модули

## Причина

Файл `config/requirements.production.txt` был неполным и не содержал все модули, которые фактически используются в коде проекта.

## Решение

### 1. Обновленный requirements.production.txt

Файл `config/requirements.production.txt` был обновлен и теперь включает все необходимые зависимости:

```bash
# Ключевые добавленные модули:
loguru==0.7.2          # Для логирования
tqdm==4.66.1           # Для прогресс-баров  
telebot==0.0.5         # Telegram bot API
lxml==4.9.3            # XML/HTML парсинг
openai==1.3.7          # OpenAI API
```

### 2. Автоматическая генерация requirements

Создан скрипт `scripts/generate_requirements.py` для автоматического анализа импортов:

```bash
cd ~/forex_bot_postgresql
python scripts/generate_requirements.py
```

Этот скрипт:
- Сканирует все Python файлы проекта
- Извлекает все импорты
- Исключает стандартную библиотеку
- Генерирует requirements.auto.txt с версиями

### 3. Улучшенный Dockerfile

Создан `docker/Dockerfile.production.enhanced` с:
- Проверкой критических модулей при сборке
- Fallback на разные requirements файлы
- Явной установкой часто отсутствующих пакетов

## Рекомендации для будущего

### 1. Используйте автоматические инструменты

```bash
# Установите pipreqs для автоматической генерации
pip install pipreqs

# Генерируйте requirements из кода
pipreqs . --force --encoding=utf8
```

### 2. Регулярно проверяйте зависимости

```bash
# Проверьте, что все импорты доступны
python -c "
import ast
import pathlib
for f in pathlib.Path('.').rglob('*.py'):
    try:
        with open(f) as file:
            tree = ast.parse(file.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    print(f'import {alias.name}')
            elif isinstance(node, ast.ImportFrom):
                print(f'from {node.module} import ...')
    except: pass
"
```

### 3. Используйте виртуальные окружения

```bash
# Создайте чистое окружение для тестирования
python -m venv test_env
source test_env/bin/activate
pip install -r config/requirements.production.txt

# Протестируйте импорты
python -c "import loguru, flask, telebot, sqlalchemy"
```

### 4. CI/CD проверки

Добавьте в CI/CD pipeline проверку зависимостей:

```yaml
# .github/workflows/dependencies.yml
- name: Check dependencies
  run: |
    pip install -r requirements.production.txt
    python -c "
    import sys
    modules = ['loguru', 'flask', 'telebot', 'sqlalchemy', 'psutil']
    for m in modules:
        try:
            __import__(m)
            print(f'✓ {m}')
        except ImportError:
            print(f'✗ {m} MISSING')
            sys.exit(1)
    "
```

## Текущий статус

✅ **Исправлено**: `config/requirements.production.txt` обновлен со всеми зависимостями  
✅ **Добавлено**: `loguru==0.7.2` и другие недостающие модули  
✅ **Создано**: Скрипт автоматической генерации requirements  
✅ **Создано**: Улучшенный Dockerfile с проверками  

## Деплой

Теперь можно безопасно деплоить:

```bash
# Используйте обновленный requirements
docker build -f docker/Dockerfile.production .

# Или используйте улучшенную версию
docker build -f docker/Dockerfile.production.enhanced .
```

## Поддержка

При добавлении новых зависимостей:
1. Добавьте их в `config/requirements.production.txt`
2. Или запустите `python scripts/generate_requirements.py`
3. Протестируйте локально перед деплоем
