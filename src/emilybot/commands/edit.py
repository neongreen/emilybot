from datetime import datetime
from discord.ext import commands
from emilybot.discord import EmilyContext

from emilybot.database import Action, ActionEdit
from emilybot.utils.list import first
from emilybot.validation import AliasValidator, ValidationError


def format_not_found_message(alias: str, command_prefix: str) -> str:
    """Format a helpful error message when an alias is not found."""
    return (
        f"❓ Alias '{alias}' not found.\n"
        f"💡 Use `{command_prefix}add {alias} [text]` to create this alias."
    )


def format_validation_error(error_message: str) -> str:
    """Format validation error messages for user-friendly display."""
    return f"❌ {error_message}"


def format_success_message(alias: str, action: str = "stored") -> str:
    """Format success message for remember operations."""
    return f"✅ Alias '{alias}' {action} successfully."


@commands.command(name="edit")
async def cmd_edit(ctx: EmilyContext, alias: str, *, new_content: str) -> None:
    """`.edit [alias] [text]`: Overwrite an existing alias."""

    db = ctx.bot.db
    prefix = ctx.bot.just_command_prefix

    try:
        AliasValidator.validate_alias(alias, "create")
        if not new_content.strip():
            raise ValidationError("Text cannot be empty.")

        server_id = ctx.guild.id if ctx.guild else None
        user_id = ctx.author.id

        # Find existing entry
        entry = first(db.find_alias(alias, server_id=server_id, user_id=user_id))

        if not entry:
            await ctx.send(format_not_found_message(alias, prefix))
            return

        # Update entry
        old_content = entry.content
        entry.content = new_content
        db.remember.update(entry)

        action = Action(
            user_id=user_id,
            timestamp=datetime.now(),
            action=ActionEdit(
                kind="edit",
                entry_id=entry.id,
                old_content=old_content,
                new_content=new_content,
            ),
        )
        db.log.add(action)

        await ctx.send(format_success_message(alias, "updated"))

    except ValidationError as e:
        await ctx.send(format_validation_error(str(e)))
