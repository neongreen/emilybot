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

        def format_preview(content: str) -> str:
            lines = content.split("\n")
            first_line = lines[0]

            if len(first_line) > 100:
                return first_line[:100] + " [...]"

            if len(lines) > 1:
                return first_line + " [...]"

            return first_line

        alias_lines: List[str] = []
        top_level_names = sorted(list(set(e.name.split("/")[0] for e in all_aliases)))

        for name in top_level_names:
            top_level_entry = next((e for e in all_aliases if e.name == name), None)

            if top_level_entry:
                alias_lines.append(
                    f"**.{name}:** {format_preview(top_level_entry.content)}"
                )
            else:
                alias_lines.append(f"**.{name}/**")

            children = [
                e
                for e in all_aliases
                if e.name.startswith(name + "/") and e.name != name
            ]
            if children:
                alias_lines.append(
                    "-# · · · Also: "
                    + ", ".join(f".{child.name}" for child in children)
                )

        if alias_lines:
            alias_lines.pop()

        aliases_str = "\n".join(alias_lines)

        # Builtins section
        builtins = [
            f"-# `{self.command_prefix}{cmd.name}`: {cmd.help}"
            for cmd in sorted(self.bot.commands, key=lambda c: c.name)
            if cmd.name != "help"
        ]
        builtins_str = "\n".join(builtins)

        await ctx.send(
            f"__What Emily knows__\n\n{aliases_str}\n\n"
            f"-# __Teach Emily stuff__\n{builtins_str}",
            suppress_embeds=True,
        )
