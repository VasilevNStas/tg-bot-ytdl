# tg-bot-ytdl

Telegram-бот для скачивания видео и аудио с YouTube. Пользователь отправляет ссылку на YouTube, а бот в ответ предлагает доступные варианты (форматы), найденные по этой ссылке.

> **Статус:** MVP — проект инициализирован, каркас кода в процессе.

## Возможности (запланировано)

- [ ] Команды `/start` и `/help`
- [ ] Определение и проверка ссылок YouTube в сообщениях
- [ ] Извлечение метаданных через yt-dlp и показ вариантов форматов (inline-клавиатура)
- [ ] Скачивание и отправка выбранного видео/аудио
- [ ] Ограничение по размеру (Telegram ~50 МБ на файл)
- [ ] Хранение в SQLite

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

## Установка

```bash
git clone git@github.com:VasilevNStas/tg-bot-ytdl.git
cd tg-bot-ytdl
uv sync          # [TODO: после каркаса]
cp .env.example .env
# укажите BOT_TOKEN в .env
```

## Запуск

```bash
uv run python -m tg_bot_ytdl   # [TODO: после каркаса]
```

## Тесты и линт

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Структура проекта (план)

```
pyproject.toml
uv.lock
src/tg_bot_ytdl/
tests/
.github/workflows/ci.yml
.env.example
```

## Лицензия

[MIT](LICENSE)

- [English version](README.md)
