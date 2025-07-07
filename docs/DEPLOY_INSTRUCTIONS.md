# 🚀 Инструкции по Деплою с Диагностикой SIGTERM

## ✅ Что Готово

Создана комплексная система диагностики и решения проблем с SIGTERM на Render.com:

### 📁 Новые Файлы
- `enhanced_main.py` - Улучшенное основное приложение с детальным логированием SIGTERM
- `monitor_resources.py` - Автономный мониторинг ресурсов
- `render_resource_check.sh` - Bash-скрипт для проверки ресурсов
- `start_with_monitoring.sh` - Скрипт запуска с автоматическим перезапуском
- `Procfile` - Обновленный файл для Render
- `README_RENDER_DIAGNOSTICS.md` - Подробная документация по диагностике

## 🔧 Шаги для Деплоя

### 1. Коммит и Пуш Изменений
```bash
cd ~/forex_bot_postgresql
git add .
git commit -m "Add enhanced SIGTERM diagnostics and monitoring system"
git push origin main
```

### 2. Обновление Настроек Render

#### 2.1 Health Check Path
1. Перейти в Render Dashboard → Ваш сервис → Settings
2. Найти "Health Check Path"
3. Установить: `/health`
4. Нажать "Save Changes"

#### 2.2 Environment Variables (если нужно)
Добавить переменные окружения:
- `MONITOR_INTERVAL=30` (интервал мониторинга в секундах)
- `MAX_RESTARTS=5` (максимальное количество перезапусков)
- `EXIT_ON_CRITICAL=false` (не выходить при критических условиях)

### 3. Мониторинг После Деплоя

#### 3.1 Просмотр Логов
```bash
# Установить Render CLI (если еще не установлен)
npm install -g @render-com/cli

# Войти в аккаунт
render auth login

# Просмотр логов в реальном времени
render logs -f --service YOUR_SERVICE_NAME
```

#### 3.2 Проверка Health Endpoint
После деплоя проверить:
- `https://YOUR_APP.onrender.com/health` - Базовая проверка здоровья
- `https://YOUR_APP.onrender.com/debug/state` - Детальное состояние системы

### 4. Анализ Логов SIGTERM

Теперь при получении SIGTERM вы увидите детальную информацию:
```
🚨 SIGNAL 15 (SIGTERM) RECEIVED - INITIATING SHUTDOWN
Shutdown initiated at: 2025-07-07T15:30:00.000Z
Application uptime: 847.23 seconds (14.12 minutes)
=== SIGTERM DIAGNOSIS ===
❌ LIKELY CAUSE: Free tier 15-minute timeout (uptime: 14.1 min)
🔍 Running on Render.com - checking Render-specific causes
=== END DIAGNOSIS ===
```

## 🔍 Возможные Причины SIGTERM и Решения

### 1. Free Tier 15-минутный Таймаут
**Признаки**: Uptime ~14-15 минут
**Решение**: 
- Настроить внешний мониторинг (UptimeRobot, cron-job.org)
- Пинговать `/health` каждые 5-10 минут
- Рассмотреть переход на Starter план ($7/мес)

### 2. Превышение Лимита Памяти
**Признаки**: Process memory >480MB
**Решение**:
- Оптимизировать код
- Добавить периодическую сборку мусора
- Upgrade на план с большим объемом RAM

### 3. Health Check Failures
**Признаки**: Раннее завершение (<5 минут uptime)
**Решение**:
- Проверить, что приложение слушает на 0.0.0.0:10000
- Убедиться, что `/health` отвечает быстро (<5 сек)
- Проверить логи на ошибки инициализации

### 4. Worker Timeouts
**Признаки**: WORKER TIMEOUT в логах
**Решение**:
- Увеличить таймауты Gunicorn
- Оптимизировать долгие операции
- Добавить таймауты для внешних API

## 🆘 Экстренные Действия

### Если Приложение Продолжает Падать
1. **Немедленно**: Проверить Render Dashboard → Metrics
2. **Проверить**: Логи на наличие новых диагностических сообщений
3. **Временное решение**: Изменить Procfile на:
   ```
   web: bash start_with_monitoring.sh
   ```
4. **Долгосрочное**: Рассмотреть upgrade на Starter план

### Команды для Быстрой Диагностики
```bash
# Поиск SIGTERM в логах Render
render logs --service YOUR_SERVICE_NAME | grep -i "sigterm\|signal.*15"

# Поиск причин в диагностических сообщениях
render logs --service YOUR_SERVICE_NAME | grep -i "likely cause"

# Проверка использования памяти
render logs --service YOUR_SERVICE_NAME | grep -i "memory.*mb"
```

## 📊 Мониторинг Метрик

### В Render Dashboard
1. Перейти в "Metrics" tab
2. Отслеживать:
   - CPU Usage (должно быть <80%)
   - Memory Usage (должно быть <400MB для free tier)
   - Response Time
   - Error Rate

### Настройка Уведомлений
1. Settings → Notifications
2. Добавить webhook или email для:
   - Deploy failures
   - Service restarts
   - High resource usage

## 🔄 Автоматическое Решение

Система теперь включает:
- **Автоматическую диагностику** причин SIGTERM
- **Детальное логирование** состояния системы
- **Мониторинг ресурсов** в реальном времени
- **Опциональный автоперезапуск** при сбоях
- **Debug endpoints** для ручной диагностики

## 📞 Поддержка

При продолжающихся проблемах:
1. Собрать логи с диагностической информацией
2. Обратиться в Render Community: https://community.render.com/
3. Рассмотреть консультацию по оптимизации приложения

---

**Следующий шаг**: Выполните деплой и наблюдайте за новыми диагностическими сообщениями в логах!
