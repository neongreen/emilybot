"""EmilyBot Discord bot class."""

import logging
from discord.ext import commands
from typing import Any

from emilybot.atomic_json_db import DBSaveError
from emilybot.database import DB
from emilybot.discord.bot_context import EmilyContext


class EmilyBot(commands.Bot):
    def __init__(self, command_prefix: str | list[str], *args: Any, **kwargs: Any):
        super().__init__(command_prefix, *args, **kwargs)
        self.db = DB()
        # Track which user triggered each bot response so reaction-deletes
        # can be restricted to the original invoker.
        self.message_owners: dict[int, int] = {}
        # Use the first prefix as the primary one for display purposes
        if isinstance(command_prefix, list):
            self.just_command_prefix = command_prefix[0]
        else:
            self.just_command_prefix = command_prefix

    async def get_context(self, *args: Any, **kwargs: Any) -> EmilyContext:
        return await super().get_context(*args, **kwargs, cls=EmilyContext)

    async def on_command_error(
        self, context: commands.Context[Any], exception: commands.CommandError
    ) -> None:
        original = getattr(exception, "original", None)
        if isinstance(original, DBSaveError):
            logging.error("Database save failed", exc_info=original)
            await context.send(format_save_error(self.db, original))
            return
        await super().on_command_error(context, exception)


def format_save_error(db: DB, error: DBSaveError) -> str:
    """User-facing reply for a failed save. Commands save the alias table first, then the log."""
    if error.path == db.log.file_path:
        return "⚠️ The change was saved, but recording it in the history failed."
    if error.replaced:
        return "⚠️ The change was written, but the disk did not confirm it was stored."
    return "❌ Saving failed, so nothing was changed."
