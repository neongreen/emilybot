import json
import re
import random
from discord.ext import commands
from emilybot.execute.run_code import run_code
from emilybot.discord import EmilyContext

from emilybot.database import Entry
from emilybot.utils.list import first
from emilybot.validation import validate_path, ValidationError
from emilybot.utils.inflect import inflect


def format_not_found_message(command: str, command_prefix: str) -> str:
    """Format a helpful error message when a command is not found."""
    return (
        f"❓ Command '{command}' not found.\n"
        f"💡 Use `{command_prefix}add {command} [text]` to create this command."
    )


def format_validation_error(error_message: str) -> str:
    """Format validation error messages for user-friendly display."""
    return f"❌ {error_message}"


async def format_entry_content(entry: Entry, ctx: EmilyContext) -> str:
    """Format entry content, *not* executing JavaScript.

    Args:
        entry: The database entry to format
        ctx: Discord context for accessing database and user info

    Returns:
        Formatted content and JS code
    """

    # Format the entry content without executing JavaScript
    formatted_content = f"**{entry.name}**\n"
    formatted_content += f"**Content:**\n{entry.content}\n"
    if entry.run and entry.run.strip():
        formatted_content += f"**JavaScript Code:**\n```js\n{entry.run}\n```"

    return formatted_content


def format_entry_line(entry: Entry) -> str:
    first_line = entry.content.split("\n")[0]
    if len(first_line) > 100:
        first_line = first_line[:100] + "..."
    return f"- {entry.name}: {first_line}"


@commands.command(name="show")
async def cmd_show(ctx: EmilyContext, alias: str) -> None:
    """`.show [alias][/]`: Show content of the alias."""

    db = ctx.bot.db
    command_prefix = ctx.bot.just_command_prefix
    server_id = ctx.guild.id if ctx.guild else None

    # `.show foo/` - list all aliases starting with "foo/"
    if alias.endswith("/"):
        # list by prefix
        results = db.find_alias(
            re.compile("^" + re.escape(alias), re.IGNORECASE),
            server_id=server_id,
            user_id=ctx.author.id,
        )
        if not results:
            await ctx.send(f"❓ No entries found for prefix '{alias}'.")
        else:
            await ctx.send(
                inflect(f"📜 Found no('entry', {len(results)})")
                + f" for '{alias}':\n"
                + "\n".join(format_entry_line(entry) for entry in results),
            )

    else:
        entry = first(db.find_alias(alias, server_id=server_id, user_id=ctx.author.id))
        if entry:
            formatted_content = await format_entry_content(entry, ctx)
            await ctx.send(formatted_content)
        else:
            await ctx.send(format_not_found_message(alias, command_prefix))


@commands.command(name="list")
async def cmd_list(ctx: EmilyContext) -> None:
    """`.list`: List all aliases."""

    db = ctx.bot.db
    server_id = ctx.guild.id if ctx.guild else None

    results = db.find_alias(
        re.compile(".*"), server_id=server_id, user_id=ctx.author.id
    )
    if not results:
        await ctx.send(f"❓ No entries found.")
    else:
        await ctx.send(", ".join(entry.name for entry in results))


@commands.command(name="random")
async def cmd_random(ctx: EmilyContext, alias: str) -> None:
    """`.random [alias]`: Get a random non-blank line from an entry."""

    db = ctx.bot.db
    command_prefix = ctx.bot.just_command_prefix

    try:
        # Validate alias
        validate_path(alias, allow_trailing_slash=False)

        server_id = ctx.guild.id if ctx.guild else None

        # Find existing entry
        entry = first(db.find_alias(alias, server_id=server_id, user_id=ctx.author.id))

        if not entry:
            await ctx.send(format_not_found_message(alias, command_prefix))
            return

        # Run
        success, output, _ = await run_code(
            ctx, code=f"$.cmd('{json.dumps(entry.name)}')"
        )
        if not success:
            await ctx.send(f"❌ Error executing JavaScript: {output}")
            return

        # Split content into lines and filter out blank lines
        lines = [line.strip() for line in output.split("\n")]
        non_blank_lines = [line for line in lines if line]

        if not non_blank_lines:
            await ctx.send(f"❓ '{alias}' gave no non-blank lines.")
            return

        # Select a random non-blank line
        random_line = random.choice(non_blank_lines)
        await ctx.send(random_line)

    except ValidationError as e:
        await ctx.send(format_validation_error(str(e)))
