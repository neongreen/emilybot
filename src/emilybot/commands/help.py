import re
from dataclasses import dataclass
from typing import List, Optional
from discord.ext import commands
from emilybot.discord import EmilyContext

from emilybot.database import Entry
from emilybot.utils.list import sorted_by_order
from emilybot.validation import parse_path


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
    top_level_names = sorted(list(set(parse_path(e.name)[0] for e in aliases)))

    for name in top_level_names:
        top_level_entry = next((e for e in aliases if e.name == name), None)

        # Get all children for this top-level name
        children = [e for e in aliases if parse_path(e.name)[0] == name]

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


@dataclass(frozen=True)
class Example:
    """One message a user can send, and text the reply contains (None: the
    bot only reacts). Help renders these, and tests send each one through
    the real bot and check the reply, so the help text cannot drift from
    the bot's behavior."""

    message: str
    reply: Optional[str] = None
    note: Optional[str] = None
    """Shown instead of `reply` when the reply is too long to quote."""


@dataclass(frozen=True)
class Topic:
    explanation: str
    examples: tuple[Example, ...]


QUICK_START = Topic(
    explanation="Make a command, run it, look at it and change it:",
    examples=(
        Example(".add greet Hello"),
        Example(".greet", "Hello"),
        Example(".set greet.run print(this.content + ', ' + args[0] + '!')"),
        Example(".greet Emily", "Hello, Emily!"),
        Example(".show greet", "print(this.content", note="its text and code"),
        Example(".edit greet Hi"),
        Example(".greet Emily", "Hi, Emily!"),
    ),
)

TOPICS: dict[str, Topic] = {
    "add": Topic(
        explanation=(
            "Saves text under a name. If the name exists, adds the text at the end"
            " after a blank line. Names use letters, digits, `-` and `_`;"
            " `/` makes folders, like `games/dice`."
        ),
        examples=(
            Example(".add pets cat"),
            Example(".add pets dog"),
            Example(".pets", "cat\n\ndog"),
        ),
    ),
    "set": Topic(
        explanation=(
            "Gives an existing alias JavaScript code. The code runs when someone"
            " types the alias. In the code, `this.content` is the alias text and"
            " `args` is the list of words after the name. Use `print(...)` to reply."
            " Running `.set` again replaces the code and keeps the text."
        ),
        examples=(
            Example(".add shout Shouts its arguments"),
            Example(".set shout.run print(args.join(' ').toUpperCase())"),
            Example(".shout hi there", "HI THERE"),
        ),
    ),
    "edit": Topic(
        explanation=(
            "Replaces the text of an existing alias. Code added with `.set` stays;"
            " use `.set` again to change the code."
        ),
        examples=(
            Example(".add motto Be kind"),
            Example(".edit motto Be brave"),
            Example(".motto", "Be brave"),
        ),
    ),
    "show": Topic(
        explanation=(
            "Shows the text and code of an alias without running it."
            " `.show name/` lists the aliases in a folder."
        ),
        examples=(
            Example(".add hello Hi!"),
            Example(".set hello.run print(this.content)"),
            Example(".show hello", "print(this.content)", note="its text and code"),
        ),
    ),
}


def command_usage(command: commands.Command[None, ..., None]) -> str:
    """The "`.add [alias] [text]`" part at the start of a built-in's docstring."""
    help_text = command.help or ""
    if match := re.match(r"`[^`]+`", help_text):
        return match.group(0)
    return f"`.{command.name}`"


def format_quick_start() -> str:
    more = ", ".join(f"`.help {name}`" for name in TOPICS)
    return "\n".join(
        [
            QUICK_START.explanation,
            format_topic_examples(QUICK_START.examples),
            f"-# More: {more}",
        ]
    )


def format_topic_help(ctx: EmilyContext, topic: str) -> str:
    name = topic.lower().lstrip(".$")
    command = ctx.bot.get_command(name)
    if command is not None:
        parts = [(command.help or command_usage(command))]
        if detail := TOPICS.get(command.name):
            parts.append(detail.explanation)
            parts.append("Example:\n" + format_topic_examples(detail.examples))
        return "\n\n".join(parts)

    server_id = ctx.guild.id if ctx.guild else None
    if ctx.bot.db.find_alias(name, server_id=server_id, user_id=ctx.author.id):
        return (
            f"`{name}` is an alias, not a built-in command."
            f" `.show {name}` shows its text and code."
        )

    topics = ", ".join(
        f"`{c.name}`" for c in sorted(ctx.bot.commands, key=lambda c: c.name)
    )
    return f"❓ No help for '{topic}'. Try one of: {topics}"


def format_topic_examples(examples: tuple[Example, ...]) -> str:
    lines: list[str] = []
    for e in examples:
        if e.note:
            lines.append(f"`{e.message}` → shows {e.note}")
        elif e.reply is None:
            lines.append(f"`{e.message}`")
        elif "\n" in e.reply:
            lines.append(f"`{e.message}` → shows:\n```\n{e.reply}\n```")
        else:
            lines.append(f"`{e.message}` → {e.reply}")
    return "\n".join(lines)


@commands.command(name="help")
async def cmd_help(ctx: EmilyContext, topic: Optional[str] = None) -> None:
    """`.help [command]`: Show how to use Emily, or explain one command."""

    if topic is not None:
        await ctx.send(format_topic_help(ctx, topic))
        return

    db = ctx.bot.db
    server_id = ctx.guild.id if ctx.guild else None
    user_id = ctx.author.id

    # Aliases section
    all_aliases = db.find_alias(re.compile(".*"), server_id=server_id, user_id=user_id)
    all_aliases.sort(key=lambda e: e.name)

    # Get top-level aliases and their promotion status
    top_level_aliases = {
        parse_path(e.name)[0]: getattr(e, "promoted", True) for e in all_aliases
    }

    # Separate aliases based on top-level promotion status
    promoted_aliases: list[Entry] = []

    for alias in all_aliases:
        top_level_name = parse_path(alias.name)[0]
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
    message_parts = ["__Quick start__", format_quick_start(), "", "__What Emily knows__"]

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
