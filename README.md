# tg-bot-ytdl

Telegram bot for downloading YouTube video and audio. The user sends a YouTube link, and the bot replies with the available format options found for that link.

> **Status:** MVP — project initialized, code scaffold in progress.

## Features (planned)

- [ ] `/start` and `/help` commands
- [ ] Detect/validate YouTube links in messages
- [ ] Extract metadata via yt-dlp and show format options (inline keyboard)
- [ ] Download and send the selected video/audio
- [ ] Size-limit guard (Telegram ~50 MB per file)
- [ ] SQLite persistence

## Tech stack

- Python 3.12+
- [aiogram](https://github.com/aiogram/aiogram) 3
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (as a library)
- SQLite + SQLAlchemy
- [uv](https://docs.astral.sh/uv/) — package manager
- pytest / pytest-asyncio, ruff

## Requirements

- Python 3.12+
- uv
- ffmpeg (required by yt-dlp for merging and audio extraction)

## Install

```bash
git clone git@github.com:VasilevNStas/tg-bot-ytdl.git
cd tg-bot-ytdl
uv sync          # [TODO: after scaffold]
cp .env.example .env
# set BOT_TOKEN in .env
```

## Run

```bash
uv run python -m tg_bot_ytdl   # [TODO: after scaffold]
```

## Test & lint

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Project structure (planned)

```
pyproject.toml
uv.lock
src/tg_bot_ytdl/
tests/
.github/workflows/ci.yml
.env.example
```

## License

[MIT](LICENSE)

- [Русская версия](README.ru.md)
