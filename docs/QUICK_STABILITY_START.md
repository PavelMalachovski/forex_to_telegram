# Быстрый Старт - Улучшенная Стабильность

## 🚀 Мгновенный Запуск

### 1. Установка Зависимостей
```bash
cd /home/ubuntu/forex_bot_postgresql
pip3 install -r requirements_enhanced.txt
```

### 2. Тест Системы Стабильности
```bash
# Тест основных компонентов
python3 test_stability.py

# Тест health checks
./scripts/health_check.sh

# Запуск улучшенного приложения
python3 enhanced_main.py
```

### 3. Установка как Системный Сервис
```bash
# Установка сервиса (требует sudo)
sudo ./scripts/install_service.sh install

# Проверка статуса
sudo systemctl status forex_bot
./scripts/health_check.sh
```

## 🔧 Основные Команды

### Управление Сервисом
```bash
sudo systemctl start forex_bot      # Запуск
sudo systemctl stop forex_bot       # Остановка
sudo systemctl restart forex_bot    # Перезапуск
sudo systemctl status forex_bot     # Статус
```

### Мониторинг
```bash
./scripts/health_check.sh           # Проверка здоровья
./scripts/health_check.sh --restart # С автоперезапуском
./scripts/monitor.sh start          # Непрерывный мониторинг
```

### Логи
```bash
tail -f logs/app.log                # Основные логи
tail -f logs/error.log              # Только ошибки
journalctl -u forex_bot -f          # Системные логи
```

## 📊 Health Check Endpoints

```bash
curl http://localhost:5000/health           # Базовая проверка
curl http://localhost:5000/health/detailed  # Детальная информация
curl http://localhost:5000/metrics          # Prometheus метрики
```

## 🛠️ Ключевые Улучшения

✅ **Graceful Shutdown** - Корректное завершение с сохранением состояния  
✅ **Auto Restart** - Автоматический перезапуск при сбоях  
✅ **Health Monitoring** - Комплексный мониторинг здоровья  
✅ **Enhanced Logging** - Ротация логов и структурированное логирование  
✅ **Signal Handling** - Улучшенная обработка системных сигналов  
✅ **Resource Monitoring** - Мониторинг CPU, памяти, диска  
✅ **Database Health** - Проверка подключения к БД  
✅ **External Services** - Мониторинг внешних зависимостей  

## 📁 Новые Файлы

### Основные Компоненты
- `enhanced_main.py` - Улучшенное основное приложение
- `forex_bot.service` - Systemd сервис
- `requirements_enhanced.txt` - Расширенные зависимости

### Утилиты Стабильности
- `app/utils/enhanced_logging.py` - Система логирования
- `app/utils/signal_handler.py` - Обработка сигналов  
- `app/utils/health_monitor.py` - Мониторинг здоровья

### Скрипты Управления
- `scripts/health_check.sh` - Проверка здоровья
- `scripts/monitor.sh` - Непрерывный мониторинг
- `scripts/install_service.sh` - Установка сервиса

### Документация
- `STABILITY_GUIDE.md` - Полное руководство по стабильности
- `IMPLEMENTATION_REPORT.md` - Отчет о реализации

## 🔍 Диагностика Проблем

### Если Сервис Не Запускается
```bash
sudo systemctl status forex_bot     # Проверить статус
journalctl -u forex_bot --since "10 minutes ago"  # Посмотреть логи
python3 enhanced_main.py            # Запустить вручную для диагностики
```

### Если Health Check Не Проходит
```bash
./scripts/health_check.sh --detailed  # Детальная диагностика
curl http://localhost:5000/health/detailed | jq  # Прямая проверка API
```

### Высокое Потребление Ресурсов
```bash
curl http://localhost:5000/metrics | grep system_  # Метрики системы
htop  # Мониторинг процессов
```

## 📈 Мониторинг в Продакшене

### Автоматические Проверки
- Cron job каждые 5 минут проверяет здоровье
- Автоматический перезапуск при сбоях
- Ротация логов для предотвращения переполнения диска

### Интеграция с Мониторингом
- Prometheus метрики: `http://localhost:5000/metrics`
- Health endpoints для load balancers
- Structured JSON логи для ELK stack

---

**Для полной документации см. `STABILITY_GUIDE.md`**
