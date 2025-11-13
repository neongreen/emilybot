"""Command for executing JavaScript code directly."""

import json
from discord.ext import commands
from emilybot.commands.show import format_not_found_message, format_validation_error
from emilybot.discord import EmilyContext
from emilybot.execute.javascript_executor import extract_js_code
from emilybot.execute.run_code import run_code
from emilybot.format import format_show_content
from emilybot.utils.list import first
from emilybot.validation import parse_path, ValidationError


@commands.command(name="run")
async def cmd_run(
    ctx: EmilyContext,
    *,  # treat the rest as a single string
    code: str,
) -> None:
    """`.run [JS code]`: Execute JavaScript code directly."""

    try:
        success, output, value = await run_code(ctx, code=extract_js_code(code))
        if success:
            await ctx.send(format_show_content(output, value))
        else:
            await ctx.send(output)  # Error message is already formatted

    except Exception as e:
        # Handle unexpected errors gracefully
        await ctx.send(f"❌ **JavaScript error:**\nUnexpected error: {str(e)}")


@commands.command(name="cmd")
async def cmd_cmd(ctx: EmilyContext, alias: str, *, args: list[str]) -> None:
    """`.cmd [alias] [args...]`: Run a command by its alias with arguments. Just use .[alias] instead"""

    db = ctx.bot.db
    command_prefix = ctx.bot.just_command_prefix

    try:
        path = parse_path(alias)
        if len(path) == 0:
            raise ValidationError("Command cannot be empty")
        if path[-1] == "":
            raise ValidationError("Command cannot end with a slash")

        server_id = ctx.guild.id if ctx.guild else None

        # Find existing entry
        entry = first(db.find_alias(alias, server_id=server_id, user_id=ctx.author.id))

        if not entry:
            await ctx.send(format_not_found_message(alias, command_prefix))
            return

        # Parse arguments
        # Convert arguments to JSON strings for JavaScript
        arg_strings = [json.dumps(arg) for arg in args]
        args_code = ", ".join(arg_strings)

        # Run the command with arguments
        success, output, value = await run_code(
            ctx, code=f"$.cmd({json.dumps(entry.name)}, {args_code})"
        )
        if success:
            await ctx.send(format_show_content(output, value))
        else:
            await ctx.send(output)  # Error message is already formatted

    except ValidationError as e:
        await ctx.send(format_validation_error(str(e)))
