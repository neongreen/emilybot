from datetime import datetime
from discord.ext import commands
import uuid
from emilybot.discord import EmilyContext

from emilybot.database import Entry, Action, ActionEdit, ActionCreate
from emilybot.utils.list import first
from emilybot.validation import validate_path, ValidationError


def format_validation_error(error_message: str) -> str:
    """Format validation error messages for user-friendly display."""
    return f"❌ {error_message}"


@commands.command(name="add")
async def cmd_add(
    ctx: EmilyContext,
    alias: str,
    *,  # you need * to treat the rest as a single string!
    content: str,
) -> None:
    """`.add [alias] [text]`: Add content to an existing entry or create a new one."""

    import logging
    logging.info(f"cmd_add called: alias={repr(alias)}, content={repr(content)}")

    db = ctx.bot.db
    server_id = ctx.guild.id if ctx.guild else None

    try:
        # Validate alias and content
        validate_path(
            alias,
            normalize_dashes=False,
            normalize_dots=True,
            check_component_length=True,
            allow_trailing_slash=False,
        )
        if not content.strip():
            raise ValidationError("Text to add cannot be empty.")

        # Find existing entry
        entry = first(db.find_alias(alias, server_id=server_id, user_id=ctx.author.id))

        if entry:
            # Entry exists - append content with blank line
            old_content = entry.content
            entry.content = f"{old_content}\n\n{content}"
            db.remember.update(entry)

            action = Action(
                user_id=ctx.author.id,
                timestamp=datetime.now(),
                action=ActionEdit(
                    kind="edit",
                    entry_id=entry.id,
                    old_content=old_content,
                    new_content=entry.content,
                ),
            )
            db.log.add(action)

            await ctx.react_success()
        else:
            # Entry doesn't exist - create new one
            doc = Entry(
                id=uuid.uuid4(),
                server_id=server_id,
                user_id=ctx.author.id,
                created_at=datetime.now().isoformat(),
                name=alias.lower(),
                content=content,
                promoted=False,
            )
            db.remember.add(doc)

            action = Action(
                user_id=ctx.author.id,
                timestamp=datetime.now(),
                action=ActionCreate(
                    kind="create",
                    entry_id=doc.id,
                    server_id=server_id,
                    name=alias.lower(),
                    content=content,
                ),
            )
            db.log.add(action)

            await ctx.react_success()

    except ValidationError as e:
        await ctx.send(format_validation_error(str(e)))
