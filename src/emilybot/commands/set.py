"""Command for setting attributes on existing entries."""

from datetime import datetime
from discord.ext import commands
from emilybot.discord import EmilyContext
from emilybot.database import Action, ActionEdit
from emilybot.utils.list import first
from emilybot.validation import AliasValidator, ValidationError
from emilybot.javascript_executor import extract_js_code


def format_not_found_message(alias: str, command_prefix: str) -> str:
    """Format a helpful error message when an alias is not found."""
    return (
        f"❓ Alias '{alias}' not found.\n"
        f"💡 Use `{command_prefix}add {alias} [text]` to create this alias first."
    )


def format_validation_error(error_message: str) -> str:
    """Format validation error messages for user-friendly display."""
    return f"❌ {error_message}"


def format_success_message(alias: str, attribute: str) -> str:
    """Format success message for set operations."""
    return f"✅ Set .{attribute} for alias '{alias}' successfully."


@commands.command(name="set")
async def cmd_set(
    ctx: EmilyContext,
    place: str,
    *,  # you need * to treat the rest as a single string!
    value: str,
) -> None:
    """`.set [alias].run [JS code]`: Turn an alias into a JS command."""

    db = ctx.bot.db
    prefix = ctx.bot.just_command_prefix

    try:
        # Validate
        alias, attr = place.split(".", 1)
        AliasValidator.validate_alias(alias, "lookup_no_endslash")

        # Validate attribute name
        if attr != "run":
            raise ValidationError(
                f"Unknown attribute '{attr}'. Only 'run' is supported."
            )

        server_id = ctx.guild.id if ctx.guild else None
        user_id = ctx.author.id

        # Find existing entry
        entry = first(db.find_alias(alias, server_id=server_id, user_id=user_id))

        if not entry:
            await ctx.send(format_not_found_message(alias, prefix))
            return

        # Handle .run attribute
        if attr == "run":
            # Parse and clean JavaScript code
            code = extract_js_code(value)

            # Store old value for logging
            old_run_value = entry.run

            # Update entry with JavaScript code
            entry.run = code
            db.remember.update(entry)

            # Log the action as an edit
            action = Action(
                user_id=user_id,
                timestamp=datetime.now(),
                action=ActionEdit(
                    kind="edit",
                    entry_id=entry.id,
                    # TODO: this should be a separate kind of edit
                    old_content=f"run: {old_run_value}"
                    if old_run_value
                    else "run: None",
                    new_content=f"run: {code}",
                ),
            )
            db.log.add(action)

            await ctx.send(format_success_message(alias, "run"))

    except ValidationError as e:
        await ctx.send(format_validation_error(str(e)))
