# Discord/Telegram Bot

A utility bot -- reminders, a trivia quiz, and simple moderation -- built
twice: a Discord bot (Node.js, [discord.js](https://discord.js.org/)) and a
Telegram bot (Python, [python-telegram-bot](https://python-telegram-bot.org/)),
sharing the same feature set and the same pure-logic architecture as the rest
of this portfolio.

[![CI](https://github.com/Elilou14/discord-telegram-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/Elilou14/discord-telegram-bot/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

There's no hosted demo -- a bot only does something once it's logged into a
real Discord application or Telegram bot account with its own token, so
"running it" means self-hosting it (see below).

## Features

- **Reminders** -- `10m`, `2h`, `1d` relative durations, or an absolute
  `2026-09-10 14:30`, persisted to SQLite so they survive a restart.
- **Quiz** -- a 5-question round pulled from a shared 24-question bank
  (geography, history, science, general knowledge), optionally filtered by
  category, with a live scoreboard.
- **Moderation** -- a configurable banned-word filter (whole-word,
  case-insensitive) and flood detection (too many messages too fast), plus a
  `/warn` + threshold system that recommends a mute or a kick once a member
  accumulates enough warnings.

## Commands

| Discord | Telegram | Does |
|---|---|---|
| `/remind <quand> <message>` | `/remind <quand> <message>` | Schedule a reminder (`10m`, `2h`, `1d`, or `2026-09-10 14:30`) |
| `/remind-list` | `/remind_list` | List your own active reminders |
| `/remind-cancel <id>` | `/remind_cancel <id>` | Cancel one, by the first 8 characters of its id |
| `/quiz [categorie]` | `/quiz [categorie]` | Start a 5-question round in the current channel/chat |
| `/warn <membre> <raison>` | reply + `/warn <raison>` | Warn a member; recommends mute/kick past a threshold |
| `/mute <membre> <duree>` | reply + `/mute <duree>` | Time out a member for a duration (`10m`, `1h`, ...) |
| `/clear <nombre>` | `/clear <nombre>` | Delete the last N messages in the channel/chat |

Telegram has no concept of Discord's target-a-user dropdown, so `/warn` and
`/mute` there work by replying to the target member's message instead of
naming them as an argument. Discord enforces `/warn`, `/mute` and `/clear` as
moderator-only itself (`setDefaultMemberPermissions`); Telegram has no
equivalent declarative gate, so the bot checks the caller is a chat admin via
`getChatMember` before doing anything.

## Architecture

Both bots split into two layers, and only one of them is actually tested:

- **Pure logic** (`reminders-logic`, `quiz-logic`, `moderation-logic`, plus
  `config` and the message/embed formatting modules) -- no network, no
  timers, no bot connection. Every rule (parsing, scoring, flood detection,
  warning thresholds) lives here as a plain function in, value out, and is
  covered by the test suite.
- **Adapter layer** (`bot.js`/`commands.js`/`scheduler.js` and
  `bot.py`/`commands.py`/`scheduler.py`) -- the actual Discord/Telegram event
  wiring. This is inherently untestable without a real bot token and a live
  connection, so it's kept as thin as possible and built carefully on top of
  the fully-tested core. Its correctness is checked instead by building each
  bot's `Application`/`Client` against a dummy token and confirming every
  handler, command, and data file wires up cleanly with no network access.

Discord's builder classes (`EmbedBuilder`, `ButtonBuilder`,
`SlashCommandBuilder`) and Telegram's `InlineKeyboardMarkup` are pure data
structures -- building one doesn't touch the network -- so all message
formatting is factored into its own module (`discord-format.js` /
`telegram_format.py`) and tested via `.toJSON()` / `.to_dict()`.

Both bots persist reminders and warnings to their own SQLite database
(Node's built-in `node:sqlite`, Python's built-in `sqlite3`) and reload them
into memory on startup; the two bots don't share a database or a wire
format -- they're independent services that happen to implement the same
feature set.

## Setup

You'll need a bot token for whichever platform(s) you want to run:

- **Discord**: create an application at the
  [Discord Developer Portal](https://discord.com/developers/applications),
  add a bot to it, and copy its token + application (client) ID.
- **Telegram**: message [@BotFather](https://t.me/BotFather), `/newbot`, and
  copy the token it gives you.

```bash
cp .env.example .env
# fill in DISCORD_TOKEN / DISCORD_CLIENT_ID and/or TELEGRAM_BOT_TOKEN,
# and optionally the moderation settings (BANNED_WORDS, thresholds, ...)
```

### Discord bot

```bash
cd node
npm install
node deploy-commands.js   # registers the slash commands with Discord (run once, and again after changing commands.js)
node bot.js
```

Set `DISCORD_GUILD_ID` in `.env` while developing to register commands to one
server instantly instead of waiting up to an hour for Discord's global
command cache to refresh.

### Telegram bot

```bash
cd python
pip install -r requirements.txt
python bot.py
```

Telegram commands need no separate registration step -- `python-telegram-bot`
starts polling as soon as `bot.py` runs.

## Tech

- **`node/*-logic.js`, `node/*-store.js`, `node/config.js`,
  `node/discord-format.js`** -- pure logic, storage and formatting, tested
  with `node:test`.
- **`node/commands.js`, `node/scheduler.js`, `node/bot.js`,
  `node/deploy-commands.js`** -- discord.js wiring.
- **`python/*_logic.py`, `python/*_store.py`, `python/config.py`,
  `python/telegram_format.py`** -- the same split, mirrored function-for-
  function, tested with `unittest`.
- **`python/commands.py`, `python/scheduler.py`, `python/bot.py`** --
  python-telegram-bot wiring.
- **`node/data/questions.json` / `python/data/questions.json`** -- the
  shared quiz question bank (copied verbatim, not referenced cross-language --
  no build step ties the two bots together).

The two adapter layers are genuinely different, not just a syntax port: PTB's
`Application`/`bot_data` model, callback-query buttons instead of Discord
message components, chat-admin checks instead of a declarative permission
gate, and a manual walk-and-delete instead of a bulk-delete endpoint.

## Running the tests

```bash
# Python
python -m unittest discover -s python/tests -v

# Node.js
cd node && node --test
```

## CI

`.github/workflows/ci.yml` runs the Python suite (3.10, 3.11, 3.12) and the
Node suite on every push and pull request to `main`. There's no deploy-pages
job -- a bot has nothing static to publish.

## License

MIT -- see [LICENSE](LICENSE).
