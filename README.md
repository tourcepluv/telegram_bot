# Telegram бот для продажи доступа (баланс + посуточное списание)

Проект: Python 3.11+, aiogram 3.x, FastAPI (webhook YooKassa), APScheduler (биллинг/уведомления), SQLAlchemy 2.0 async.

## Быстрый старт локально

1) Создайте виртуальное окружение и установите зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Скопируйте и заполните `.env`:

```bash
cp .env.example .env
```

3) Запустите приложение:

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Локальный webhook через ngrok

1) Запустите приложение и ngrok:

```bash
ngrok http 8080
```

2) Укажите в YooKassa webhook URL:

```
https://<ngrok>.ngrok-free.app<WEBHOOK_PATH>
```

3) Укажите `RETURN_URL` в `.env`:

```
RETURN_URL=https://<ngrok>.ngrok-free.app/pay/return
```

## Деплой на сервере

1) Настройте `.env` с доменом проекта.
2) Настройте HTTPS и проксирование до `localhost:8080`.
3) Укажите webhook в YooKassa:

```
https://<domain><WEBHOOK_PATH>
```

## Запуск

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```
