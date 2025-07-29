import re
from typing import List
from discord.ext.commands import Context, Bot  # pyright: ignore[reportMissingTypeStubs]

import emilybot.db as db


class HelpCommands:
    """Commands for providing help and information."""

    def __init__(self, bot: Bot, database: db.DB, command_prefix: str) -> None:
        self.bot = bot
        self.db = database
        self.command_prefix = command_prefix

    async def help(self, ctx: Context[Bot]) -> None:
        """Shows this help message."""
        server_id = ctx.guild.id if ctx.guild else None
        user_id = ctx.author.id

        # Aliases section
        all_aliases = self.db.find_alias(
            re.compile(".*"), server_id=server_id, user_id=user_id
        )
        all_aliases.sort(key=lambda e: e.name)

        # Separate promoted and demoted aliases
        promoted_aliases = [e for e in all_aliases if getattr(e, "promoted", True)]
        demoted_aliases = [e for e in all_aliases if not getattr(e, "promoted", True)]

        def format_preview(content: str) -> str:
            lines = content.split("\n")
            first_line = lines[0]

            if len(first_line) > 100:
                return first_line[:100] + " [...]"

            if len(lines) > 1:
                return first_line + " [...]"

            return first_line

        def format_aliases_section(
            aliases: List[db.Entry], grey_text: bool = False
        ) -> str:
            """Format a section of aliases, optionally as grey text."""
            alias_lines: List[str] = []
            top_level_names = sorted(list(set(e.name.split("/")[0] for e in aliases)))

            for name in top_level_names:
                top_level_entry = next((e for e in aliases if e.name == name), None)

                # Get all children for this top-level name
                children = [
                    e
                    for e in aliases
                    if e.name.startswith(name + "/") and e.name != name
                ]

                if top_level_entry:
                    line = f"`.{name}`: {format_preview(top_level_entry.content)}"
                    if grey_text:
                        line = f"-# {line}"
                    alias_lines.append(line)
                else:
                    line = f"`.{name}/`"
                    if grey_text:
                        line = f"-# {line}"
                    alias_lines.append(line)

                if children:
                    children_line = "-# " + ", ".join(
                        f".{child.name}" for child in children
                    )
                    alias_lines.append(children_line)
                alias_lines.append("")

            if alias_lines:
                alias_lines.pop()  # Remove last empty line

            return "\n".join(alias_lines)

        # Format promoted aliases normally
        promoted_str = format_aliases_section(promoted_aliases)

        # Format demoted aliases as grey text
        demoted_str = format_aliases_section(demoted_aliases, grey_text=True)

        # Builtins section
        builtins = [
            f"-# {cmd.help}"
            for cmd in sorted(self.bot.commands, key=lambda c: c.name)
            if cmd.name != "help"
        ]
        builtins_str = "\n".join(builtins)

        # Build the final message
        message_parts = ["__What Emily knows__"]

        if promoted_str:
            message_parts.append(promoted_str)

        if demoted_str:
            if promoted_str:
                message_parts.append("")  # Add spacing
            message_parts.append(demoted_str)

        message_parts.extend(["", f"-# __Teach Emily stuff__", builtins_str])

        await ctx.send(
            "\n\n".join(filter(None, message_parts)),
            suppress_embeds=True,
        )
