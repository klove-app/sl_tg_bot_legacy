# RunTracker Bot v2 — architecture

Last updated: 2026-07-30

## Product boundary

RunTracker v2 is a Telegram group bot. Every run, runner profile, statistic, and
leaderboard is scoped by Telegram `chat_id`. A person's activity in one group
cannot affect another group's leaderboard.

## Runtime

- Python 3.11+
- aiogram 3 using Telegram long polling
- PostgreSQL through SQLAlchemy async + asyncpg
- One Railway replica per Telegram bot token

The service intentionally has no public HTTP endpoint. Railway should deploy the
`v2/` directory as a separate service while legacy remains available for rollback.
Never run legacy and v2 concurrently with the same Telegram bot token: Telegram
permits only one active long-polling consumer.

## Data model

- `runbot_chats`: known Telegram groups
- `runbot_runners`: a runner's current display identity inside a group
- `runbot_runs`: immutable run facts plus a nullable `deleted_at` audit marker

`(chat_id, telegram_message_id)` is unique, making delivery retries idempotent.
Legacy imports use `legacy_log_id` as a second idempotency key.

## Commands

- `@runforestsweaty_bot <km> [note]`: records a run in the current group
- `/run <km> [note]`: backwards-compatible alternative
- `/top`: chat leaderboard with week/month/year/all-time buttons
- `/me`: the caller's month and year statistics in the current group
- `/undo`: soft-deletes the caller's latest active run after confirmation
- `/help`: usage summary

Mentioning the bot is the primary run-entry flow. The bot also accepts a distance
when the user replies to it. `/run` remains a backwards-compatible alternative.
Parent chat and runner rows are flushed before a run insert so the composite
foreign key is satisfied consistently on PostgreSQL.

## Time

Telegram timestamps are converted into `BOT_TIMEZONE` before deriving the run
date and leaderboard period. The default is `Europe/Moscow`.

## Legacy migration

`python -m scripts.import_legacy` is read-only and reports importable rows.
`python -m scripts.import_legacy --apply` creates the v2 schema and imports only
legacy rows with a non-null `chat_id`. Re-running is safe because
`legacy_log_id` is unique.

Private-chat legacy rows and rows without `chat_id` are intentionally excluded:
they cannot be assigned to a group without an explicit owner decision.
