from __future__ import annotations

import html
import re
from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.keyboards import top_period_keyboard, undo_keyboard
from app.parsing import ParsedRun, RunParseError, parse_run_text
from app.periods import Period, period_label, period_range
from app.repository import (
    RunInput,
    add_run,
    get_latest_active_run,
    get_ranking,
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
            "Добавьте меня в групповой чат и используйте там <code>/run 5.2</code>."
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


def _format_km(value: Decimal) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


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
            f"Эта пробежка уже учтена: <b>{_format_km(run.distance_km)} км</b>."
        )
        return

    await session.commit()
    today = _local_date(message, settings)
    month_stats = await get_user_stats(
        session,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        date_range=period_range(Period.MONTH, today),
    )
    await message.reply(
        "✅ Пробежка записана\n"
        f"🏃 <b>{_format_km(parsed.distance_km)} км</b>\n"
        f"📅 {run.run_date:%d.%m.%Y}\n\n"
        f"За месяц: <b>{_format_km(month_stats.total_km)} км</b> "
        f"за {month_stats.runs_count} пробежек."
    )


@router.message(CommandStart())
async def start(message: Message, settings: Settings) -> None:
    if message.chat.type in GROUP_TYPES:
        if not _chat_allowed(message, settings):
            await message.answer("Этот чат не включён в список разрешённых.")
            return
        await message.answer(
            "Я считаю километры отдельно для этого чата.\n\n"
            "Добавить пробежку: <code>/run 5.2</code>\n"
            "Рейтинг: /top\n"
            "Моя статистика: /me\n"
            "Отменить последнюю запись: /undo"
        )
        return
    await _require_group(message, settings)


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(
        "<b>Команды</b>\n"
        "<code>/run 5.2</code> — записать пробежку\n"
        "<code>/run 10 утренний парк</code> — добавить заметку\n"
        "/top — рейтинг этой группы\n"
        "/me — моя статистика в этой группе\n"
        "/undo — удалить свою последнюю запись\n\n"
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
    today,
) -> str:
    date_range = period_range(period, today)
    ranking = await get_ranking(
        session,
        chat_id=chat_id,
        date_range=date_range,
    )
    totals = await get_totals(
        session,
        chat_id=chat_id,
        date_range=date_range,
    )
    if not ranking:
        return f"За {period_label(period)} пробежек пока нет."

    medals = ["🥇", "🥈", "🥉"]
    lines = [
        f"🏆 <b>Рейтинг за {period_label(period)}</b>",
        (
            f"{totals.runners_count} участников · {totals.runs_count} пробежек · "
            f"{_format_km(totals.total_km)} км"
        ),
        "",
    ]
    for index, entry in enumerate(ranking, start=1):
        place = medals[index - 1] if index <= len(medals) else f"{index}."
        name = html.escape(entry.display_name)
        lines.append(
            f"{place} <b>{name}</b> — {_format_km(entry.total_km)} км "
            f"({entry.runs_count})"
        )
    return "\n".join(lines)


@router.message(Command("top"))
async def top_command(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if not await _require_group(message, settings):
        return
    period = Period.MONTH
    text = await _render_top(
        session,
        chat_id=message.chat.id,
        period=period,
        today=_local_date(message, settings),
    )
    await message.answer(text, reply_markup=top_period_keyboard(period))


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
        period = Period(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Неизвестный период", show_alert=True)
        return

    today = datetime.now(ZoneInfo(settings.bot_timezone)).date()
    text = await _render_top(
        session,
        chat_id=callback.message.chat.id,
        period=period,
        today=today,
    )
    await callback.message.edit_text(text, reply_markup=top_period_keyboard(period))
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
    month = await get_user_stats(
        session,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        date_range=period_range(Period.MONTH, today),
    )
    year = await get_user_stats(
        session,
        chat_id=message.chat.id,
        user_id=message.from_user.id,
        date_range=period_range(Period.YEAR, today),
    )
    await message.reply(
        f"👤 <b>{html.escape(_display_name(message))}</b>\n\n"
        f"Этот месяц: <b>{_format_km(month.total_km)} км</b> "
        f"({month.runs_count} пробежек)\n"
        f"Этот год: <b>{_format_km(year.total_km)} км</b> "
        f"({year.runs_count} пробежек)\n"
        f"Лучшая пробежка года: <b>{_format_km(year.best_run_km)} км</b>"
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
        f"Удалить последнюю запись: <b>{_format_km(run.distance_km)} км</b> "
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
        f"🗑 Запись на <b>{_format_km(run.distance_km)} км</b> удалена."
    )
    await callback.answer()


@router.message(F.text | F.caption)
async def mentioned_run(
    message: Message,
    bot: Bot,
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
    replied_to_bot = bool(
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot.id
    )
    if not mention and not replied_to_bot:
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
