"""Command for executing JavaScript code directly."""

import logging
import uuid

from discord import DMChannel, Message, Thread
from emilybot.discord import EmilyContext
from emilybot.execute.javascript_executor import (
    JavaScriptExecutor,
    Context,
    CtxMessage,
    CtxReplyTo,
    CtxUser,
    CtxServer,
    CtxChannel,
)
from emilybot.command_query_service import CommandQueryService
from emilybot.execute.admission import BUSY_MESSAGE, ExecutorBusy, get_admission
from emilybot.atomic_json_db import DBSaveError
from emilybot.execute.executor import STORE_BUSY_MESSAGE
from emilybot.store import StoreConflict, StoreQuotaExceeded, StoreUnavailable

__all__ = ["STORE_BUSY_MESSAGE", "run_code"]

STORE_SAVE_FAILED_MESSAGE = (
    "⚠️ Could not save this command's stored data. Nothing was changed; try again."
)


async def run_code(
    ctx: EmilyContext,
    *,
    code: str,
) -> tuple[bool, str, str | None]:
    """Run JavaScript code directly and return the result."""
    # Admission comes before collecting commands, so a burst queues cheaply
    try:
        async with get_admission().slot(caller=str(ctx.author.id)):
            return await _run_code(ctx, code=code)
    except ExecutorBusy:
        return False, BUSY_MESSAGE, None


async def _run_code(
    ctx: EmilyContext,
    *,
    code: str,
) -> tuple[bool, str, str | None]:
    js_executor = JavaScriptExecutor()

    # Get available commands using command query service
    command_query_service = CommandQueryService(ctx.bot.db)
    available_commands = command_query_service.get_available_commands(
        user_id=ctx.author.id, server_id=ctx.guild.id if ctx.guild else None
    )

    # Create Context for direct execution.
    # When changing this, also change `make_ctx` in conftest.py

    # Extract reply information if available
    reply_to = None
    if (
        ctx.message.reference
        and ctx.message.reference.resolved
        and not hasattr(ctx.message.reference.resolved, "_deleted")
    ):
        try:
            resolved_message = ctx.message.reference.resolved
            if isinstance(resolved_message, Message):
                reply_to = CtxReplyTo(
                    text=str(resolved_message.content),
                    user=CtxUser(
                        id=str(resolved_message.author.id),
                        handle=str(resolved_message.author.name),
                        name=str(resolved_message.author.display_name),
                        global_name=resolved_message.author.global_name,
                        avatar_url=str(resolved_message.author.display_avatar.url),
                    ),
                )
        except (AttributeError, TypeError):
            # Handle cases where the resolved message doesn't have expected attributes
            pass

    context = Context(
        message=CtxMessage(
            text=ctx.message.content,
        ),
        reply_to=reply_to,
        user=CtxUser(
            id=str(ctx.author.id),
            handle=ctx.author.name,
            name=ctx.author.display_name,
            global_name=ctx.author.global_name,
            avatar_url=ctx.author.display_avatar.url,
        ),
        server=CtxServer(id=str(ctx.guild.id)) if ctx.guild else None,
        channel=channel_context(ctx),
    )

    server_id = ctx.guild.id if ctx.guild else None
    db = ctx.bot.db
    # Stores exist for server aliases only; in DMs `this.store` is undefined
    stores = db.store.access(server_id) if server_id is not None else None
    run_at_start = {c.get("id"): c["run"] for c in available_commands}

    outcome = await js_executor.run(code, context, available_commands, stores=stores)
    if not outcome.success or outcome.store is None or server_id is None:
        return outcome.success, outcome.output, outcome.value

    # Commit before the caller shows any output: a run whose writes are refused shows nothing
    def alias_unchanged(alias_id: uuid.UUID) -> bool:
        entry = db.remember.get(alias_id)
        return (
            entry is not None
            and entry.server_id == server_id
            and entry.run == run_at_start.get(str(alias_id))
        )

    try:
        db.store.commit(server_id, outcome.store, alias_unchanged)
    except StoreConflict:
        return False, STORE_BUSY_MESSAGE, None
    except StoreQuotaExceeded as e:
        return False, f"📦 {e}", None
    except StoreUnavailable as e:
        return False, f"⚠️ this.store is unavailable: {e}", None
    except DBSaveError as e:
        logging.error("Saving store.json failed", exc_info=e)
        if e.file_state != "new":
            return False, STORE_SAVE_FAILED_MESSAGE, None
    return outcome.success, outcome.output, outcome.value


def channel_context(ctx: EmilyContext) -> CtxChannel:
    channel = ctx.channel
    if isinstance(channel, DMChannel) or ctx.guild is None:
        return CtxChannel(id=str(channel.id), name=None, parent_id=None)
    parent_id = channel.parent_id if isinstance(channel, Thread) else None
    name = getattr(channel, "name", None)
    return CtxChannel(
        id=str(channel.id),
        name=name if isinstance(name, str) else None,
        parent_id=str(parent_id) if parent_id is not None else None,
    )
