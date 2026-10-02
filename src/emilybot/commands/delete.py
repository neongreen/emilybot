import logging
from datetime import datetime
from discord.ext import commands
from emilybot.discord import EmilyContext

from emilybot.atomic_json_db import DBSaveError
from emilybot.database import Action, ActionDelete
from emilybot.store import StoreUnavailable
from emilybot.utils.list import first
from emilybot.suggestions import format_suggestion_lines
from emilybot.validation import parse_path, ValidationError


def format_not_found_message(alias: str) -> str:
    return f"❓ Alias '{alias}' not found."


def format_validation_error(error_message: str) -> str:
    return f"❌ {error_message}"


def format_deleted_message(alias: str) -> str:
    return f"✅ Fine. '{alias}' was deleted."


@commands.command(name="rm")
async def cmd_rm(ctx: EmilyContext, alias: str) -> None:
    """`.rm [alias]`: Delete an alias."""

    db = ctx.bot.db

    try:
        path = parse_path(alias)
        if len(path) == 0:
            raise ValidationError("Alias cannot be empty")
        if path[-1] == "":
            raise ValidationError("Alias cannot end with a slash")

        server_id = ctx.guild.id if ctx.guild else None
        user_id = ctx.author.id

        # Find existing entry
        entry = first(db.find_alias(alias, server_id=server_id, user_id=user_id))

        if not entry:
            await ctx.send(
                format_not_found_message(alias) + format_suggestion_lines(ctx, alias)
            )
            return

        # Delete entry
        db.remember.remove(entry.id)

        # The log keeps the alias's store, so restoring the alias from the log can restore its state
        store = db.store.get(entry.id)
        action = Action(
            user_id=user_id,
            timestamp=datetime.now(),
            action=ActionDelete(
                kind="delete",
                entry_id=entry.id,
                entry=entry,
                store=store.data if store else None,
            ),
        )
        db.log.add(action)
        if store:
            try:
                db.store.delete(entry.id)
            except (DBSaveError, StoreUnavailable) as e:
                # The alias is gone, so nothing can reach this store any more
                logging.error(f"Could not delete the store of {entry.id}", exc_info=e)

        await ctx.send(format_deleted_message(alias))

    except ValidationError as e:
        await ctx.send(format_validation_error(str(e)))
