import re
import random
from discord.ext import commands
from emilybot.discord import EmilyContext

from emilybot.database import Entry
from emilybot.utils.list import first
from emilybot.validation import AliasValidator, ValidationError
from emilybot.utils.inflect import inflect


def format_not_found_message(alias: str, command_prefix: str) -> str:
    """Format a helpful error message when an alias is not found."""
    return (
        f"❓ Alias '{alias}' not found.\n"
        f"💡 Use `{command_prefix}add {alias} [text]` to create this alias."
    )


def format_validation_error(error_message: str) -> str:
    """Format validation error messages for user-friendly display."""
    return f"❌ {error_message}"


def format_show_content(content: str) -> str:
    # trim if >2000char, *then* trim if >100 lines
    if len(content) > 2000:
        content = content[:2000] + "..."
    if content.count("\n") > 100:
        content = "\n".join(content.split("\n")[:100]) + "..."
    return content


def format_entry_line(entry: Entry) -> str:
    first_line = entry.content.split("\n")[0]
    if len(first_line) > 100:
        first_line = first_line[:100] + "..."
    return f"- {entry.name}: {first_line}"


@commands.command(name="show")
async def cmd_show(ctx: EmilyContext, alias: str) -> None:
    """`.show [alias][/]`: Show content of the alias. You can just use `.[alias]` instead."""

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
            await ctx.send(format_show_content(entry.content))
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
        AliasValidator.validate_alias(alias, "lookup_no_endslash")

        server_id = ctx.guild.id if ctx.guild else None

        # Find existing entry
        entry = first(db.find_alias(alias, server_id=server_id, user_id=ctx.author.id))

        if not entry:
            await ctx.send(format_not_found_message(alias, command_prefix))
            return

        # Split content into lines and filter out blank lines
        lines = [line.strip() for line in entry.content.split("\n")]
        non_blank_lines = [line for line in lines if line]

        if not non_blank_lines:
            await ctx.send(f"❓ Alias '{alias}' has no non-blank lines.")
            return

        # Select a random non-blank line
        random_line = random.choice(non_blank_lines)
        await ctx.send(random_line)

    except ValidationError as e:
        await ctx.send(format_validation_error(str(e)))
