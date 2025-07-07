
# Render.com SIGTERM Диагностика и Решение Проблем

## 🚨 Проблема
Приложение на Render.com получает сигнал SIGTERM и останавливается, несмотря на работающие health checks.

## 📋 Возможные Причины SIGTERM на Render

### 1. Превышение Лимитов Ресурсов
- **Память**: Бесплатный план ограничен 512MB RAM
- **CPU**: Превышение лимитов CPU может вызвать принудительную остановку
- **Трафик**: Высокий исходящий трафик может привести к приостановке

### 2. Таймауты Free Tier
- **15-минутный таймаут**: Бесплатные сервисы засыпают после 15 минут бездействия
- **750 часов в месяц**: Лимит времени работы для бесплатного плана

### 3. Health Check Проблемы
- Неправильная конфигурация health check endpoint
- Медленный отклик на health checks (>5 секунд)
- Приложение не слушает на правильном порту (0.0.0.0:10000)

### 4. Worker Timeouts
- Долгие запросы превышают таймауты Gunicorn/Flask
- Блокирующие операции в основном потоке

## 🔧 Решения

### Шаг 1: Переключение на Enhanced Main
```bash
# Обновить Procfile для использования enhanced_main.py
echo "web: python enhanced_main.py" > Procfile

# Или использовать скрипт с мониторингом
echo "web: bash start_with_monitoring.sh" > Procfile
```

### Шаг 2: Деплой Обновленного Кода
```bash
# Добавить все файлы
git add .

# Коммит изменений
git commit -m "Add enhanced SIGTERM diagnostics and monitoring"

# Пуш на Render
git push origin main
```

### Шаг 3: Настройка Render Dashboard

#### 3.1 Обновление Health Check
1. Перейти в Render Dashboard → Ваш сервис → Settings
2. Установить Health Check Path: `/health`
3. Сохранить изменения

#### 3.2 Включение Автоматического Перезапуска
1. В Settings найти "Auto-Deploy"
2. Включить "Auto-deploy from Git"
3. Включить "Auto-restart on failure" (если доступно)

#### 3.3 Мониторинг Метрик
1. Перейти в "Metrics" tab
2. Отслеживать CPU и Memory usage
3. Настроить уведомления при превышении лимитов

### Шаг 4: Локальное Тестирование SIGTERM
```bash
# Запустить приложение локально
python enhanced_main.py &
APP_PID=$!

# Подождать несколько секунд
sleep 5

# Отправить SIGTERM
kill -15 $APP_PID

# Проверить логи
tail -f logs/enhanced_app.log
```

### Шаг 5: Мониторинг Ресурсов
```bash
# Запустить мониторинг ресурсов
python monitor_resources.py --interval 10 --log-file logs/resources.log

# Или использовать bash скрипт
bash render_resource_check.sh
```

## 📊 Мониторинг и Диагностика

### Доступные Endpoints
- `GET /health` - Базовая проверка здоровья
- `GET /debug/state` - Дамп текущего состояния системы
- `POST /debug/gc` - Принудительная сборка мусора
- `GET /api/status` - Статус приложения

### Логи для Анализа
```bash
# Основные логи приложения
tail -f logs/enhanced_app.log

# Логи мониторинга ресурсов
tail -f logs/resource_monitor.log

# Логи проверки ресурсов
tail -f logs/resource_check.log
```

### Команды Render CLI
```bash
# Установить Render CLI
npm install -g @render-com/cli

# Войти в аккаунт
render auth login

# Просмотр логов в реальном времени
render logs -f --service YOUR_SERVICE_NAME

# Перезапуск сервиса
render services restart YOUR_SERVICE_NAME
```

## 🔍 Диагностические Команды

### Проверка Состояния Системы
```bash
# Проверка памяти
free -h

# Проверка CPU
top -bn1 | head -20

# Проверка процессов Python
ps aux | grep python

# Проверка портов
netstat -tlnp | grep :10000
```

### Анализ Логов на Предмет SIGTERM
```bash
# Поиск SIGTERM в логах
grep -i "sigterm\|signal.*15" logs/*.log

# Поиск ошибок памяти
grep -i "memory\|oom" logs/*.log

# Поиск таймаутов
grep -i "timeout\|worker.*timeout" logs/*.log
```

## ⚡ Временные Решения

### 1. Автоматический Перезапуск
Используйте `start_with_monitoring.sh` в Procfile:
```
web: bash start_with_monitoring.sh
```

### 2. Предотвращение Sleep Mode (Free Tier)
Настройте внешний мониторинг:
- UptimeRobot: пинг каждые 5 минут на `/health`
- cron-job.org: GET запрос каждые 10 минут

### 3. Оптимизация Ресурсов
```python
# В коде приложения добавить:
import gc

# Периодическая сборка мусора
gc.collect()

# Ограничение размера логов
logging.getLogger().handlers[0].setLevel(logging.WARNING)
```

## 📈 Upgrade План

### Переход на Paid Plan
1. **Starter Plan ($7/мес)**: 512MB RAM, 0.5 CPU, без sleep mode
2. **Standard Plan ($25/мес)**: 2GB RAM, 1 CPU, автоскейлинг
3. **Pro Plan ($85/мес)**: 4GB RAM, 2 CPU, расширенные возможности

### Преимущества Paid Plans
- Отсутствие 15-минутного таймаута
- Больше ресурсов (RAM/CPU)
- Автоматическое масштабирование
- Расширенный мониторинг
- Техническая поддержка

## 🆘 Экстренные Действия

### При Критических Проблемах
1. **Немедленно**: Проверить логи в Render Dashboard
2. **Проверить**: Использование памяти и CPU в Metrics
3. **Перезапустить**: Сервис через Dashboard или CLI
4. **Откатиться**: К предыдущей рабочей версии если нужно

### Контакты Поддержки
- Render Community: https://community.render.com/
- Render Support: support@render.com (для paid plans)
- Документация: https://render.com/docs

## 📝 Чеклист Диагностики

- [ ] Проверены логи приложения на наличие SIGTERM
- [ ] Проверено использование памяти (< 512MB для free tier)
- [ ] Проверено использование CPU
- [ ] Проверен health check endpoint
- [ ] Проверена конфигурация порта (0.0.0.0:10000)
- [ ] Проверены таймауты worker'ов
- [ ] Настроен мониторинг ресурсов
- [ ] Настроены уведомления
- [ ] Рассмотрен upgrade на paid plan

## 🔗 Полезные Ссылки

- [Render Health Checks](https://render.com/docs/health-checks)
- [Render Free Tier Limits](https://render.com/docs/free)
- [Render Troubleshooting](https://render.com/docs/troubleshooting-deploys)
- [Render Scaling](https://render.com/docs/scaling)
