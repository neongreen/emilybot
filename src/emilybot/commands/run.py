"""Command for executing JavaScript code directly."""

import json
from discord.ext import commands
from emilybot.commands.show import format_not_found_message, format_validation_error
from emilybot.discord import EmilyContext
from emilybot.execute.run_code import run_code
from emilybot.format import format_show_content
from emilybot.utils.list import first
from emilybot.validation import AliasValidator, ValidationError


@commands.command(name="run")
async def cmd_run(
    ctx: EmilyContext,
    *,  # treat the rest as a single string
    code: str,
) -> None:
    """`.run [JS code]`: Execute JavaScript code directly."""

    try:
        success, output, value = await run_code(ctx, code=code)
        if success:
            await ctx.send(format_show_content(output, value))
        else:
            await ctx.send(output)  # Error message is already formatted

    except Exception as e:
        # Handle unexpected errors gracefully
        await ctx.send(f"❌ **JavaScript error:**\nUnexpected error: {str(e)}")


@commands.command(name="cmd")
async def cmd_cmd(ctx: EmilyContext, alias: str) -> None:
    """`.cmd [alias]`: Run a command by its alias. Just use .[alias] instead"""

    db = ctx.bot.db
    command_prefix = ctx.bot.just_command_prefix

    try:
        # Validate alias
        AliasValidator.validate_alias(alias, "lookup_no_endslash")

        server_id = ctx.guild.id if ctx.guild else None

        # Find existing entry
        entry = first(db.find_alias(alias, server_id=server_id, user_id=ctx.author.id))

        if not entry:
            await ctx.send(format_not_found_message(alias, command_prefix))
            return

        # Run the command
        success, output, _ = await run_code(
            ctx, code=f"$.cmd('{json.dumps(entry.name)}')"
        )
        if not success:
            await ctx.send(f"❌ Error executing JavaScript: {output}")

    except ValidationError as e:
        await ctx.send(format_validation_error(str(e)))
