import re
from typing import List
from discord.ext import commands
from emilybot.discord import EmilyContext

from emilybot.database import Entry
from emilybot.utils.list import sorted_by_order
from emilybot.validation import validate_path


def format_preview(content: str) -> str:
    lines = content.split("\n")
    first_line = lines[0]

    if len(first_line) > 100:
        return first_line[:100] + " [...]"

    if len(lines) > 1:
        return first_line + " [...]"

    return first_line


def format_aliases_section(aliases: List[Entry]) -> str:
    """Format a section of aliases"""
    alias_lines: List[str] = []
    top_level_names = sorted(
        list(set(validate_path(e.name).split("/")[0] for e in aliases))
    )

    for name in top_level_names:
        top_level_entry = next((e for e in aliases if e.name == name), None)

        # Get all children for this top-level name
        children = [e for e in aliases if validate_path(e.name).startswith(name + "/")]

        if top_level_entry:
            line = f"`.{name}`: {format_preview(top_level_entry.content)}"
        else:
            line = f"`.{name}/`"
        alias_lines.append(line)

        if children:
            children_line = "-# " + ", ".join(f".{child.name}" for child in children)
            alias_lines.append(children_line)
        alias_lines.append("")

    if alias_lines:
        alias_lines.pop()  # Remove last empty line

    return "\n".join(alias_lines)


@commands.command(name="help")
async def cmd_help(ctx: EmilyContext) -> None:
    """Shows this help message."""

    db = ctx.bot.db
    server_id = ctx.guild.id if ctx.guild else None
    user_id = ctx.author.id

    # Aliases section
    all_aliases = db.find_alias(re.compile(".*"), server_id=server_id, user_id=user_id)
    all_aliases.sort(key=lambda e: e.name)

    # Get top-level aliases and their promotion status
    top_level_aliases = {
        validate_path(e.name).split("/")[0]: getattr(e, "promoted", True)
        for e in all_aliases
    }

    # Separate aliases based on top-level promotion status
    promoted_aliases: list[Entry] = []

    for alias in all_aliases:
        top_level_name = validate_path(alias.name).split("/")[0]
        # If top-level is promoted, include in promoted section
        if top_level_aliases.get(top_level_name, True):
            promoted_aliases.append(alias)

    # Format promoted aliases
    promoted_str = format_aliases_section(promoted_aliases)

    # Don't show demoted aliases, we quickly run into the 2k char limit
    and_more = "Use `.list` to see all aliases."

    # Builtins section
    builtins = sorted_by_order(
        ctx.bot.commands,
        key=lambda cmd: cmd.name,
        key_order=["add", "edit", "rm", "random", "promote", "demote"],
    )
    builtins_str = "\n".join(
        [f"-# {cmd.help}" for cmd in builtins if cmd.name != "help"],
    )

    # Build the final message
    message_parts = ["__What Emily knows__"]

    if promoted_str:
        message_parts.append(promoted_str)
        message_parts.append("")
    message_parts.append(and_more)

    message_parts.extend(["", f"__Teach Emily stuff__", builtins_str])

    message_parts.extend(
        [
            "",
            f"__Full docs__",
            f"https://github.com/neongreen/emilybot/tree/main/docs/README.md",
        ]
    )

    await ctx.send("\n\n".join(filter(None, message_parts)))
