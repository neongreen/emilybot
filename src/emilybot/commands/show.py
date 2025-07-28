import re
import random
from discord.ext.commands import Context, Bot  # pyright: ignore[reportMissingTypeStubs]

import emilybot.db as db
from emilybot.utils.list import first
from emilybot.validation import AliasValidator, ValidationError
from emilybot.utils.inflect import inflect


class ShowCommands:
    """Commands for displaying and retrieving alias content."""

    def __init__(self, bot: Bot, db: db.DB, command_prefix: str) -> None:
        self.bot = bot
        self.db = db
        self.command_prefix = command_prefix

    def format_not_found_message(self, alias: str) -> str:
        """Format a helpful error message when an alias is not found."""
        return (
            f"❓ Alias '{alias}' not found.\n"
            f"💡 Use `{self.command_prefix}save {alias} <text>` to create this alias."
        )

    def format_validation_error(self, error_message: str) -> str:
        """Format validation error messages for user-friendly display."""
        return f"❌ {error_message}"

    def format_success_message(self, alias: str, action: str = "stored") -> str:
        """Format success message for remember operations."""
        return f"✅ Alias '{alias}' {action} successfully."

    def format_show_content(self, content: str) -> str:
        # trim if >1000char, *then* trim if >100 lines
        if len(content) > 1000:
            content = content[:1000] + "..."
        if content.count("\n") > 100:
            content = "\n".join(content.split("\n")[:100]) + "..."
        return content

    async def _show_implementation(self, ctx: Context[Bot], alias: str) -> None:
        """Shared implementation for finding an alias."""

        server_id = ctx.guild.id if ctx.guild else None

        # `.show all` - list all aliases
        if alias == "all" or alias == "/":
            results = self.db.find_alias(
                re.compile(".*"), server_id=server_id, user_id=ctx.author.id
            )
            if not results:
                await ctx.send("❓ No aliases found.", suppress_embeds=True)
            else:
                await ctx.send(
                    inflect(f"📜 Found no('entry', {len(results)}):\n")
                    + ", ".join(entry.name for entry in results),
                    suppress_embeds=True,
                )

        # `.show foo/` - list all aliases starting with "foo/"
        elif alias.endswith("/"):
            # list by prefix
            results = self.db.find_alias(
                re.compile("^" + re.escape(alias), re.IGNORECASE),
                server_id=server_id,
                user_id=ctx.author.id,
            )
            if not results:
                await ctx.send(
                    f"❓ No entries found for prefix '{alias}'.",
                    suppress_embeds=True,
                )
            else:
                await ctx.send(
                    inflect(f"📜 Found no('entry', {len(results)})")
                    + f" for '{alias}':\n"
                    + "\n".join(f"- {entry.name}" for entry in results),
                    suppress_embeds=True,
                )

        else:
            entry = first(
                self.db.find_alias(alias, server_id=server_id, user_id=ctx.author.id)
            )
            if entry:
                await ctx.send(
                    self.format_show_content(entry.content), suppress_embeds=True
                )
            else:
                await ctx.send(
                    self.format_not_found_message(alias), suppress_embeds=True
                )

    async def _random_implementation(self, ctx: Context[Bot], alias: str) -> None:
        """Shared implementation for getting a random non-blank line from an entry."""
        try:
            # Validate alias
            AliasValidator.validate_alias(alias, "lookup_no_endslash")

            server_id = ctx.guild.id if ctx.guild else None

            # Find existing entry
            entry = first(
                self.db.find_alias(alias, server_id=server_id, user_id=ctx.author.id)
            )

            if not entry:
                await ctx.send(
                    self.format_not_found_message(alias), suppress_embeds=True
                )
                return

            # Split content into lines and filter out blank lines
            lines = [line.strip() for line in entry.content.split("\n")]
            non_blank_lines = [line for line in lines if line]

            if not non_blank_lines:
                await ctx.send(
                    f"❓ Alias '{alias}' has no non-blank lines.",
                    suppress_embeds=True,
                )
                return

            # Select a random non-blank line
            random_line = random.choice(non_blank_lines)
            await ctx.send(random_line, suppress_embeds=True)

        except ValidationError as e:
            await ctx.send(self.format_validation_error(str(e)), suppress_embeds=True)

    async def show(self, ctx: Context[Bot], alias: str) -> None:
        """Find a remembered entry by alias. Usage: .show <alias>, or list with .show dir/"""
        await self._show_implementation(ctx, alias)

    async def all(self, ctx: Context[Bot]) -> None:
        """List all remembered entries."""
        await self._show_implementation(ctx, "all")

    async def random(self, ctx: Context[Bot], alias: str) -> None:
        """Get a random non-blank line from an entry. Usage: .random <alias>"""
        await self._random_implementation(ctx, alias)
