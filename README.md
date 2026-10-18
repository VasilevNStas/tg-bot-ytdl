# tg-bot-ytdl

Telegram bot for downloading YouTube video and audio. Send a YouTube video link and the bot replies with a cover image and the available formats; send a public channel link to save it to your personal cabinet and browse its latest uploads.

> **Status:** MVP is implemented and deployed (long-polling on a VPS).

## Features

- `/start`, `/help`, `/subscriptions` commands, a bot menu button and a persistent reply keyboard so the menu is always one tap away.
- Video link → thumbnail preview + curated format list (MP4 video qualities and MP3 audio).
- Download the selected format and send it as a document named after the video title.
- Telegram file-size guard (~50 MB per file) with a clear message for oversized files.
- Public channel subscriptions ("Мои подписки") with no YouTube login: save a channel, list saved channels, remove them.
- Channel browsing by section — videos, shorts, live streams — shown as cards with a thumbnail and a download button, paginated with a "more" button (5 per page).
- Direct YouTube links keep working alongside the cabinet flow.
- SQLite persistence: users, download history and subscriptions.

## Commands

| Command | Description |
| --- | --- |
| `/start` | Open the menu |
| `/subscriptions` | My saved channels |
| `/help` | Help |

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
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

## Install

```bash
git clone git@github.com:VasilevNStas/tg-bot-ytdl.git
cd tg-bot-ytdl
uv sync
cp .env.example .env
# set BOT_TOKEN in .env
```

## Run

```bash
uv run python -m tg_bot_ytdl
```

## Test & lint

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Project structure

```
pyproject.toml
uv.lock
.python-version
.env.example
src/tg_bot_ytdl/
├── config.py       # settings (pydantic-settings)
├── main.py         # entry point: init DB, bot, dispatcher, polling
├── commands.py     # bot command list + menu button
├── handlers.py     # router: commands, menu, links, callbacks
├── extractor.py    # video metadata via yt-dlp
├── channels.py     # channel detection, metadata, video listings
├── downloader.py   # format download (MP4 / MP3) via yt-dlp
├── keyboards.py    # menu, format and subscription keyboards
├── db.py           # engine, session factory, init
├── models.py       # User, DownloadRequest, Subscription
├── repository.py   # data access helpers
└── ratelimit.py    # per-user rate limiting
tests/
.github/workflows/ci.yml      # lint + tests
.github/workflows/deploy.yml  # deploy to server after green CI
.github/dependabot.yml
```

## CI/CD

- **CI** — GitHub Actions runs `ruff check`, `ruff format --check` and `pytest` on every push and pull request to `main`.
- **CD** — after a green CI run on `main`, a second workflow deploys to the production VPS over SSH. The app runs under systemd (no Docker); `BOT_TOKEN` lives only in a server-side `.env` (mode `600`).

## License

[MIT](LICENSE)

- [Русская версия](README.ru.md)
