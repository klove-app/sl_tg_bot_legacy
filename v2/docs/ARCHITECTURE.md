# RunTracker Bot v2 — architecture

Last updated: 2026-08-09

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
- `runbot_league_memberships`: immutable per-month league assignments
- `runbot_summary_deliveries`: idempotency ledger for scheduled chat summaries
- `runbot_achievement_awards`: permanent, idempotent runner medals with the date
  on which each condition was first met

`(chat_id, telegram_message_id)` is unique, making delivery retries idempotent.
Legacy imports use `legacy_log_id` as a second idempotency key.

## Commands

- `@runforestsweaty_bot <km> [note]`: records a run in the current group
- `/run <km> [note]`: backwards-compatible alternative
- `/top`: the two league leaderboards for the current week, current month, or
  previous month
- `/me`: the caller's week/month statistics and current league
- `/undo`: soft-deletes the caller's latest active run after confirmation
- `/help`: usage summary

Mentioning the bot is the primary run-entry flow. Ordinary replies to the bot are
ignored unless their own text or photo caption explicitly mentions the bot.
`/run` remains a backwards-compatible alternative.
Parent chat and runner rows are flushed before a run insert so the composite
foreign key is satisfied consistently on PostgreSQL.

Successful run replies show the recorded distance and date, optional note,
month-to-date distance and run count, current monthly leaderboard position, and
shortcuts to `/top`, `/me`, and `/undo`. The same period buttons used by `/top`
are attached to the confirmation. Leaderboards show one compact row per runner
plus group runner, run, and distance totals.

Newly earned medals are appended to the successful run reply. `/me` shows the
runner's dynamic activity title and all permanent medals. Existing run history
is evaluated silently at startup, so deploying the feature neither loses old
achievements nor emits backfill messages into Telegram.

## Titles and achievements

Activity titles are derived at read time. A runner is a «Спящая ячейка» after
60 days without a run and «Снова в эфире» for 14 days after returning from a
60-day gap. Active runners progress through «Новая ячейка», «На связи», and
«Полевой сотрудник»; a 15–59 day gap is «Вне эфира».

Permanent achievements cover:

- single-run clubs at 2, 5, and 10 km
- «С дивана» I–III for a 2 km start/return, a second run within 10 days, and
  four runs within 30 days
- three lifetime runs, three runs in a calendar week, and four consecutive
  active calendar weeks
- lifetime totals of 100, 500, and 1000 km

The award key is unique by chat, runner, code, and period key. Evaluation is
therefore safe to repeat after restarts. Scheduled summaries include awards
whose first qualifying date falls inside the closed period. Monthly summaries
also name each active league leader and list runners inactive for 60 days.

## Leagues

Each runner has one league assignment per calendar month:

- `trail` / «Тропа» for new and developing runners
- `tempo` / «Темп» for the stronger cohort

The first assignment seeds roughly the strongest 40% of known runners into
«Темп», using the trailing 30 days. The assignment then stays fixed for the
month. At the next month boundary, up to two active «Тропа» leaders are promoted
and the same number from the bottom of «Темп» are relegated. At least one runner
remains in «Темп». Runners who join after monthly assignments exist start in
«Тропа».

League tables include every assigned runner, including zero-distance rows, while
the group totals count only runners who recorded a run in the selected period.
Interactive `/top` tables hide zero-distance rows and name the selected calendar
month explicitly. The previous-month button makes a run from the prior calendar
month discoverable instead of displaying that runner as `0 km` in the current
month. Scheduled summaries still include all assigned participants.

## Scheduled summaries

The bot runs a lightweight scheduler alongside long polling. It publishes:

- a summary of the closed week on Monday at `SUMMARY_HOUR` (09:00 by default)
- a summary of the closed month on the first calendar day at `SUMMARY_HOUR` plus
  `MONTHLY_SUMMARY_MINUTE` (09:10 by default)

Both summaries show every participant in both leagues, new achievements, and
group totals. Monthly summaries also show league titles and sleeping cells. Empty
periods are recorded but not posted. `runbot_summary_deliveries` prevents a
restart from duplicating a summary. The service remains single-replica because
both Telegram polling and summary delivery assume one active process.

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
