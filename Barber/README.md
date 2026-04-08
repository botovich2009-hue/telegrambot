# Telegram-бот барбершопа (aiogram + SQLite)

Бот для записи на стрижку с календарём, слотами времени, админ-панелью и автонапоминаниями за 24 часа.

## Возможности

- Запись через inline-календарь и выбор времени
- Один активный слот на пользователя (нельзя записаться на несколько дат одновременно)
- Отмена записи (слот снова становится доступным)
- Проверка подписки на канал перед записью
- Уведомление администратора о новой записи
- Публикация расписания в отдельный канал/чат
- Админ-панель: рабочие дни, слоты, просмотр расписания, отмена записей, закрытие дня
- Автонапоминания за 24 часа (APScheduler) + восстановление задач после перезапуска
- Кнопки "Прайсы" и "Портфолио" в главном меню

## Установка

1) Создайте и активируйте виртуальное окружение:

```bash
python -m venv .venv
.venv\Scripts\activate
```

2) Установите зависимости:

```bash
pip install -r requirements.txt
```

3) Создайте `.env` рядом с `bot.py` и заполните по примеру `.env.example`.

## Запуск

```bash
python bot.py
```

## Быстрый старт (важно)

- **Проверка подписки**: добавьте бота в канал `CHANNEL_ID` как администратора (или дайте право читать участников), иначе `getChatMember` может не работать корректно.
- **Расписание**: слоты появляются только в тех датах, которые админ добавил как рабочие и добавил временные слоты.

## Структура проекта

```
Barber/
  bot.py
  requirements.txt
  README.md
  .env.example
  app/
    __init__.py
    config.py
    constants.py
    scheduler.py
    middlewares/
      __init__.py
      subscription.py
    database/
      __init__.py
      db.py
      schema.py
    keyboards/
      __init__.py
      common.py
      calendar.py
      booking.py
      admin.py
    handlers/
      __init__.py
      start.py
      prices_portfolio.py
      booking.py
      admin.py
    states/
      __init__.py
      booking.py
      admin.py
    utils/
      __init__.py
      formatters.py
      phone.py
```
