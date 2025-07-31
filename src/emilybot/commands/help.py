import re
from typing import List
from discord.ext import commands
from emilybot.discord import EmilyContext

from emilybot.database import Entry
from emilybot.utils.list import sorted_by_order


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
    top_level_names = sorted(list(set(e.name.split("/")[0] for e in aliases)))

    for name in top_level_names:
        top_level_entry = next((e for e in aliases if e.name == name), None)

        # Get all children for this top-level name
        children = [
            e for e in aliases if e.name.startswith(name + "/") and e.name != name
        ]

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
        e.name.split("/")[0]: getattr(e, "promoted", True)
        for e in all_aliases
        if "/" not in e.name
    }

    # Separate aliases based on top-level promotion status
    promoted_aliases: list[Entry] = []
    demoted_aliases: list[Entry] = []

    for alias in all_aliases:
        top_level_name = alias.name.split("/")[0]
        # If top-level is promoted, include in promoted section
        # If top-level is demoted, include in demoted section
        if top_level_aliases.get(top_level_name, True):
            promoted_aliases.append(alias)
        else:
            demoted_aliases.append(alias)

    # Format promoted aliases normally
    promoted_str = format_aliases_section(promoted_aliases)

    # Format demoted aliases as grey text
    demoted_str = (
        "-# And more: " + ", ".join(f"`.{e.name}`" for e in demoted_aliases)
        if demoted_aliases
        else ""
    )

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

    if demoted_str:
        if promoted_str:
            message_parts.append("")  # Add spacing
        message_parts.append(demoted_str)

    message_parts.extend(["", f"__Teach Emily stuff__", builtins_str])

    message_parts.extend(
        [
            "",
            f"__Full docs__",
            f"https://github.com/neongreen/emilybot/tree/main/docs/README.md",
        ]
    )

    await ctx.send("\n\n".join(filter(None, message_parts)))
