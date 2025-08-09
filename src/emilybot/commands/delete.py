from datetime import datetime
from discord.ext import commands
from emilybot.discord import EmilyContext

from emilybot.database import Action, ActionDelete
from emilybot.utils.list import first
from emilybot.validation import validate_path, ValidationError


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
        validate_path(alias, allow_trailing_slash=False)

        server_id = ctx.guild.id if ctx.guild else None
        user_id = ctx.author.id

        # Find existing entry
        entry = first(db.find_alias(alias, server_id=server_id, user_id=user_id))

        if not entry:
            await ctx.send(format_not_found_message(alias))
            return

        # Delete entry
        db.remember.remove(entry.id)

        action = Action(
            user_id=user_id,
            timestamp=datetime.now(),
            action=ActionDelete(
                kind="delete",
                entry_id=entry.id,
                entry=entry,
            ),
        )
        db.log.add(action)

        await ctx.send(format_deleted_message(alias))

    except ValidationError as e:
        await ctx.send(format_validation_error(str(e)))
