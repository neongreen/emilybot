"""Command for setting attributes on existing entries."""

import logging
from dataclasses import replace
from datetime import datetime
from discord.ext import commands
from emilybot.discord import EmilyContext
from emilybot.database import Action, ActionEdit
from emilybot.utils.list import first
from emilybot.suggestions import format_suggestion_lines
from emilybot.validation import validate_path, ValidationError
from emilybot.execute.code_validation import (
    InvalidCode,
    ValidatorFailed,
    validate_command_code,
)
from emilybot.execute.javascript_executor import extract_js_code


def format_not_found_message(alias: str, command_prefix: str) -> str:
    """Format a helpful error message when an alias is not found."""
    return (
        f"❓ Alias '{alias}' not found.\n"
        f"💡 Use `{command_prefix}add {alias} [text]` to create this alias first."
    )


def format_invalid_code_message(alias: str, invalid: InvalidCode) -> str:
    return (
        f"❌ The code for `{alias}` has a JavaScript syntax error at {invalid.describe()}\n"
        f"The alias was not changed."
    )


def format_validator_failed_message(alias: str) -> str:
    return (
        f"⚠️ Could not save the code for `{alias}`: checking it failed. "
        f"The alias was not changed; try again."
    )


def format_deleted_during_validation_message(alias: str) -> str:
    return f"❓ Alias '{alias}' was deleted while its code was being checked. Nothing was saved."


def format_validation_error(error_message: str) -> str:
    """Format validation error messages for user-friendly display."""
    return f"❌ {error_message}"


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
        # Split alias and attribute (last part if split by dots, from the end)
        if "." not in place:
            raise ValidationError(
                f"Write `{prefix}set {place}.run [JS code]` to give '{place}' code."
            )
        alias, attr = place.rsplit(".", 1)

        # Validate alias
        validate_path(
            alias,
            normalize_dashes=False,
            normalize_dots=True,
            check_component_length=True,
            allow_trailing_slash=False,
        )

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
            await ctx.send(
                format_not_found_message(alias, prefix)
                + format_suggestion_lines(ctx, alias)
            )
            return

        # Handle .run attribute
        if attr == "run":
            # Parse and clean JavaScript code
            code = extract_js_code(value)

            # Check the code before replacing anything; empty code just clears `run`
            if code.strip():
                try:
                    invalid = await validate_command_code(code)
                except ValidatorFailed as e:
                    logging.error(f"Validating code for {alias!r} failed: {e}")
                    await ctx.send(format_validator_failed_message(alias))
                    return
                if invalid:
                    await ctx.send(format_invalid_code_message(alias, invalid))
                    return

            # Validation awaited a subprocess: apply the edit to the entry as it is now
            current = db.remember.get(entry.id)
            if current is None:
                await ctx.send(format_deleted_during_validation_message(alias))
                return
            old_run_value = current.run
            db.remember.update(replace(current, run=code))

            # Log the action as an edit
            action = Action(
                user_id=user_id,
                timestamp=datetime.now(),
                action=ActionEdit(
                    kind="edit",
                    entry_id=current.id,
                    # TODO: this should be a separate kind of edit
                    old_content=f"run: {old_run_value}"
                    if old_run_value
                    else "run: None",
                    new_content=f"run: {code}",
                ),
            )
            db.log.add(action)

            await ctx.react_success()

    except ValidationError as e:
        await ctx.send(format_validation_error(str(e)))
