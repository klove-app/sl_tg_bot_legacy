from __future__ import annotations

import html
import re
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.keyboards import top_period_keyboard, undo_keyboard
from app.leagues import LEAGUE_EMOJI, LEAGUE_TITLES, League
from app.parsing import ParsedRun, RunParseError, parse_run_text
from app.periods import (
    MONTH_NAMES_NOMINATIVE,
    DateRange,
    Period,
    month_date_range,
    month_start,
    period_range,
    previous_month_start,
)
from app.presentation import (
    format_km,
    pluralize,
    render_league_ranking,
    render_run_confirmation,
)
from app.repository import (
    RankingEntry,
    RunInput,
    add_run,
    ensure_month_leagues,
    get_latest_active_run,
    get_league_ranking,
    get_totals,
    get_user_stats,
    soft_delete_owned_run,
)

router = Router(name="runtracker")
GROUP_TYPES = {"group", "supergroup"}


def _chat_allowed(message: Message, settings: Settings) -> bool:
    allowed = settings.allowed_chat_id_set
    return not allowed or message.chat.id in allowed


async def _require_group(message: Message, settings: Settings) -> bool:
    if message.chat.type not in GROUP_TYPES:
        await message.answer(
            "Добавьте меня в групповой чат и напишите там "
            "<code>@runforestsweaty_bot 5.2</code>."
        )
        return False
    if not _chat_allowed(message, settings):
        await message.answer("Этот чат не включён в список разрешённых.")
        return False
    return True


def _local_date(message: Message, settings: Settings):
    timestamp = message.date
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.astimezone(ZoneInfo(settings.bot_timezone)).date()


def _chat_title(message: Message) -> str:
    return message.chat.title or str(message.chat.id)


def _display_name(message: Message) -> str:
    if message.from_user is None:
        return "Неизвестный бегун"
    return message.from_user.full_name[:255]


async def _save_parsed_run(
    message: Message,
    parsed: ParsedRun,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить автора сообщения.")
        return

    run, created = await add_run(
        session,
        RunInput(
            chat_id=message.chat.id,
            chat_title=_chat_title(message),
            user_id=message.from_user.id,
            username=message.from_user.username,
            display_name=_display_name(message),
            telegram_message_id=message.message_id,
            distance_km=parsed.distance_km,
            run_date=_local_date(message, settings),
            note=parsed.note,
        ),
    )
    if not created:
        await message.reply(
            f"Эта пробежка уже учтена: <b>{format_km(run.distance_km)} км</b>."
        )
        return

    today = _local_date(message, settings)
    current_month = month_start(today)
    assignments = await ensure_month_leagues(
        session,
        chat_id=message.chat.id,
        membership_month=current_month,
        seed_end=today,
    )
    await session.commit()
    month_range = period_range(Period.MONTH, today)
    month_stats = await get_user_stats(
        session,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        date_range=month_range,
    )
    league = assignments.get(message.from_user.id)
    league_ranking = (
        await get_league_ranking(
            session,
            chat_id=message.chat.id,
            membership_month=current_month,
            league=league,
            date_range=month_range,
        )
        if league is not None
        else []
    )
    league_place = next(
        (
            index
            for index, entry in enumerate(league_ranking, start=1)
            if entry.user_id == message.from_user.id
        ),
        None,
    )
    await message.reply(
        render_run_confirmation(
            distance_km=parsed.distance_km,
            run_date=run.run_date,
            note=parsed.note,
            month_stats=month_stats,
            league=league,
            league_place=league_place,
            league_runners_count=len(league_ranking),
        ),
        reply_markup=top_period_keyboard(Period.MONTH, today=today),
    )


async def _league_rankings(
    session: AsyncSession,
    *,
    chat_id: int,
    date_range: DateRange,
    membership_month: date,
    seed_end: date,
) -> dict[League, list[RankingEntry]]:
    await ensure_month_leagues(
        session,
        chat_id=chat_id,
        membership_month=membership_month,
        seed_end=seed_end,
    )
    return {
        league: await get_league_ranking(
            session,
            chat_id=chat_id,
            membership_month=membership_month,
            league=league,
            date_range=date_range,
        )
        for league in League
    }


@router.message(CommandStart())
async def start(message: Message, settings: Settings) -> None:
    if message.chat.type in GROUP_TYPES:
        if not _chat_allowed(message, settings):
            await message.answer("Этот чат не включён в список разрешённых.")
            return
        await message.answer(
            "Я считаю километры отдельно для этого чата.\n\n"
            "Добавить пробежку: <code>@runforestsweaty_bot 5.2</code>\n"
            "Рейтинг двух лиг за неделю или месяц: /top\n"
            "Моя статистика: /me\n"
            "Отменить последнюю запись: /undo"
        )
        return
    await _require_group(message, settings)


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "<b>Как записать пробежку</b>\n"
        "<code>@runforestsweaty_bot 5.2</code>\n"
        "<code>@runforestsweaty_bot 10 утренний парк</code> — с заметкой\n\n"
        "<b>Команды</b>\n"
        "/top — две лиги за неделю или месяц\n"
        "/me — моя статистика за неделю и месяц\n"
        "/undo — удалить свою последнюю запись\n\n"
        "Лиги закрепляются на месяц. Новые участники начинают в «Тропе».\n"
        "Итоги недели и месяца бот публикует автоматически.\n\n"
        "Поддерживаются точка и запятая: <code>5.2</code> или <code>5,2</code>."
    )


@router.message(Command("run"))
async def add_run_command(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if not await _require_group(message, settings):
        return
    text = message.text or message.caption
    try:
        parsed = parse_run_text(
            text,
            max_distance_km=settings.max_distance_km,
            require_command=True,
        )
    except RunParseError as exc:
        await message.reply(f"⚠️ {html.escape(str(exc))}")
        return
    await _save_parsed_run(message, parsed, session, settings)


async def _render_top(
    session: AsyncSession,
    *,
    chat_id: int,
    period: Period,
    today: date,
    month_offset: int = 0,
) -> str:
    if period is Period.MONTH and month_offset == -1:
        target_month = previous_month_start(today)
        date_range = month_date_range(target_month)
        membership_month = target_month
    else:
        date_range = period_range(period, today)
        membership_month = month_start(today)
    rankings = await _league_rankings(
        session,
        chat_id=chat_id,
        membership_month=membership_month,
        date_range=date_range,
        seed_end=date_range.end,
    )
    totals = await get_totals(
        session,
        chat_id=chat_id,
        date_range=date_range,
    )
    active_rankings = {
        league: [entry for entry in entries if entry.runs_count > 0]
        for league, entries in rankings.items()
    }
    title = (
        f"{MONTH_NAMES_NOMINATIVE[membership_month.month - 1]} {membership_month.year}"
        if period is Period.MONTH
        else None
    )
    return render_league_ranking(
        period=period,
        rankings=active_rankings,
        totals=totals,
        title=title,
    )


@router.message(Command("top"))
async def top_command(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if not await _require_group(message, settings):
        return
    period = Period.MONTH
    today = _local_date(message, settings)
    text = await _render_top(
        session,
        chat_id=message.chat.id,
        period=period,
        today=today,
    )
    await message.answer(
        text,
        reply_markup=top_period_keyboard(period, today=today),
    )


@router.callback_query(F.data.startswith("top:"))
async def top_callback(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if callback.message is None or callback.data is None:
        await callback.answer()
        return
    allowed = settings.allowed_chat_id_set
    if allowed and callback.message.chat.id not in allowed:
        await callback.answer("Этот чат не включён в список разрешённых.", show_alert=True)
        return
    try:
        parts = callback.data.split(":")
        period = Period(parts[1])
        month_offset = int(parts[2]) if len(parts) > 2 else 0
    except (IndexError, ValueError):
        await callback.answer("Неизвестный период", show_alert=True)
        return
    if period not in {Period.WEEK, Period.MONTH}:
        await callback.answer("Теперь доступны неделя и месяц", show_alert=True)
        return
    if month_offset not in {-1, 0}:
        await callback.answer("Неизвестный месяц", show_alert=True)
        return

    today = datetime.now(ZoneInfo(settings.bot_timezone)).date()
    text = await _render_top(
        session,
        chat_id=callback.message.chat.id,
        period=period,
        today=today,
        month_offset=month_offset,
    )
    await callback.message.edit_text(
        text,
        reply_markup=top_period_keyboard(
            period,
            today=today,
            month_offset=month_offset,
        ),
    )
    await callback.answer()


@router.message(Command("me"))
async def me_command(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if not await _require_group(message, settings) or message.from_user is None:
        return
    today = _local_date(message, settings)
    current_month = month_start(today)
    assignments = await ensure_month_leagues(
        session,
        chat_id=message.chat.id,
        membership_month=current_month,
        seed_end=today,
    )
    week = await get_user_stats(
        session,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        date_range=period_range(Period.WEEK, today),
    )
    month = await get_user_stats(
        session,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        date_range=period_range(Period.MONTH, today),
    )
    league = assignments.get(message.from_user.id)
    league_line = (
        f"{LEAGUE_EMOJI[league]} Лига «{LEAGUE_TITLES[league]}»\n\n"
        if league is not None
        else ""
    )
    await message.reply(
        f"👤 <b>{html.escape(_display_name(message))}</b>\n\n"
        f"{league_line}"
        f"📅 Эта неделя: <b>{format_km(week.total_km)} км</b> "
        f"· {pluralize(week.runs_count, 'пробежка', 'пробежки', 'пробежек')}\n"
        f"📊 Этот месяц: <b>{format_km(month.total_km)} км</b> "
        f"· {pluralize(month.runs_count, 'пробежка', 'пробежки', 'пробежек')}\n"
        f"⚡ Лучшая за месяц: <b>{format_km(month.best_run_km)} км</b>\n\n"
        "🏆 /top · ↩️ /undo"
    )


@router.message(Command("undo"))
async def undo_command(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if not await _require_group(message, settings) or message.from_user is None:
        return
    run = await get_latest_active_run(
        session,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
    )
    if run is None:
        await message.reply("У вас нет пробежек, которые можно удалить.")
        return
    await message.reply(
        f"Удалить последнюю запись: <b>{format_km(run.distance_km)} км</b> "
        f"от {run.run_date:%d.%m.%Y}?",
        reply_markup=undo_keyboard(run.id),
    )


@router.callback_query(F.data.startswith("undo:"))
async def undo_callback(
    callback: CallbackQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if callback.message is None or callback.data is None or callback.from_user is None:
        await callback.answer()
        return
    allowed = settings.allowed_chat_id_set
    if allowed and callback.message.chat.id not in allowed:
        await callback.answer("Этот чат не включён в список разрешённых.", show_alert=True)
        return
    value = callback.data.split(":", 1)[1]
    if value == "cancel":
        await callback.message.edit_text("Удаление отменено.")
        await callback.answer()
        return
    try:
        run_id = int(value)
    except ValueError:
        await callback.answer("Некорректная запись", show_alert=True)
        return

    run = await soft_delete_owned_run(
        session,
        run_id=run_id,
        chat_id=callback.message.chat.id,
        user_id=callback.from_user.id,
    )
    if run is None:
        await callback.answer(
            "Запись уже удалена или принадлежит другому участнику",
            show_alert=True,
        )
        return
    await session.commit()
    await callback.message.edit_text(
        f"🗑 Запись на <b>{format_km(run.distance_km)} км</b> удалена."
    )
    await callback.answer()


@router.message(F.text | F.caption)
async def mentioned_run(
    message: Message,
    session: AsyncSession,
    settings: Settings,
    bot_username: str,
) -> None:
    if message.chat.type not in GROUP_TYPES:
        return
    text = message.text or message.caption or ""
    if text.lstrip().startswith("/"):
        return

    mention = f"@{bot_username}".lower() in text.lower()
    if not mention:
        return
    if not _chat_allowed(message, settings):
        await message.reply("Этот чат не включён в список разрешённых.")
        return

    cleaned = text
    if bot_username:
        cleaned = re.sub(
            rf"@{re.escape(bot_username)}",
            " ",
            cleaned,
            flags=re.IGNORECASE,
        )
    try:
        parsed = parse_run_text(
            cleaned,
            max_distance_km=settings.max_distance_km,
            require_command=False,
        )
    except RunParseError as exc:
        await message.reply(f"⚠️ {html.escape(str(exc))}")
        return
    await _save_parsed_run(message, parsed, session, settings)
