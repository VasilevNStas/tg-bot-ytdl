# tg-bot-ytdl

Telegram-бот для скачивания видео и аудио с YouTube. Отправь ссылку на видео YouTube — бот в ответ пришлёт обложку и доступные форматы; отправь ссылку на публичный канал, чтобы сохранить его в личный кабинет и просматривать свежие загрузки.

> **Статус:** MVP реализован и задеплоен (long-polling на VPS).

## Возможности

- Команды `/start`, `/help`, `/subscriptions`, кнопка меню бота и постоянная reply-клавиатура — меню всегда доступно в один тап.
- Ссылка на видео → превью-обложка + список форматов (MP4-качества и MP3-аудио).
- Скачивание выбранного формата и отправка файла как документа с именем по названию видео.
- Ограничение по размеру (Telegram ~50 МБ на файл) с понятным сообщением для слишком больших файлов.
- Подписки на публичные каналы («Мои подписки») без входа в YouTube: сохранение канала, список сохранённых, удаление.
- Просмотр содержимого канала по разделам — видео, шортс, трансляции — карточками с обложкой и кнопкой скачивания, с пагинацией кнопкой «Ещё» (по 5 записей).
- Прямые ссылки на YouTube продолжают работать наравне с кабинетом.
- Хранение в SQLite: пользователи, история скачиваний и подписки.

## Команды

| Команда | Описание |
| --- | --- |
| `/start` | Открыть меню |
| `/subscriptions` | Мои подписки |
| `/help` | Справка |

## Технологии

- Python 3.12+
- [aiogram](https://github.com/aiogram/aiogram) 3
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (как библиотека)
- SQLite + SQLAlchemy
- [uv](https://docs.astral.sh/uv/) — пакетный менеджер
- pytest / pytest-asyncio, ruff

## Требования

- Python 3.12+
- uv
- ffmpeg (нужен yt-dlp для объединения потоков и извлечения аудио)
- Токен бота Telegram от [@BotFather](https://t.me/BotFather)

## Установка

```bash
git clone git@github.com:VasilevNStas/tg-bot-ytdl.git
cd tg-bot-ytdl
uv sync
cp .env.example .env
# укажите BOT_TOKEN в .env
```

## Запуск

```bash
uv run python -m tg_bot_ytdl
```

## Тесты и линт

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Структура проекта

```
pyproject.toml
uv.lock
.python-version
.env.example
src/tg_bot_ytdl/
├── config.py       # настройки (pydantic-settings)
├── main.py         # точка входа: init БД, бот, dispatcher, polling
├── commands.py     # список команд бота + кнопка меню
├── handlers.py     # роутер: команды, меню, ссылки, колбэки
├── extractor.py    # метаданные видео через yt-dlp
├── channels.py     # определение канала, метаданные, списки видео
├── downloader.py   # скачивание формата (MP4 / MP3) через yt-dlp
├── keyboards.py    # клавиатуры меню, форматов и подписок
├── db.py           # engine, session factory, init
├── models.py       # User, DownloadRequest, Subscription
├── repository.py   # доступ к данным
└── ratelimit.py    # ограничение частоты запросов на пользователя
tests/
.github/workflows/ci.yml      # линт + тесты
.github/workflows/deploy.yml  # деплой на сервер после зелёного CI
.github/dependabot.yml
```

## CI/CD

- **CI** — GitHub Actions прогоняет `ruff check`, `ruff format --check` и `pytest` на каждый push и pull request в `main`.
- **CD** — после зелёного CI в `main` второй workflow деплоит на production VPS по SSH. Приложение работает под systemd (без Docker); `BOT_TOKEN` хранится только в серверном `.env` (права `600`).

## Лицензия

[MIT](LICENSE)

- [English version](README.md)
