from discord.ext import commands
from discord.ext.commands import Context, Bot  # pyright: ignore[reportMissingTypeStubs]

import emilybot.remember.db as db
from emilybot.validation import AliasValidator, ValidationError
from emilybot.remember.save_commands import SaveCommands
from emilybot.remember.show_commands import ShowCommands
from emilybot.remember.edit_commands import EditCommands


class RememberCog(commands.Cog):
    def __init__(self, bot: commands.Bot, command_prefix: str) -> None:
        self.bot = bot
        self.db = db.DB()
        self.command_prefix = command_prefix

        self.save_commands = SaveCommands(self.bot, self.db, self.command_prefix)
        self.show_commands = ShowCommands(self.bot, self.db, self.command_prefix)
        self.edit_commands = EditCommands(self.bot, self.db, self.command_prefix)

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

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self.bot.user:
            print(f"RememberCog loaded in {self.bot.user.name}")
        else:
            print("RememberCog loaded, but bot user is not available yet.")

    def can_handle(self, content: str) -> bool:
        """An extra check to see if the message can be handled by this cog. This will grab messages like `.foo?`."""
        if (
            content.startswith(self.command_prefix)
            and len(content) > len(self.command_prefix)
            and content[-1] == "?"
        ):
            try:
                AliasValidator.validate_alias(
                    content[len(self.command_prefix) : -1].strip()
                )
            except ValidationError:
                return False
            return True
        return False

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context[commands.Bot], error: commands.CommandError
    ) -> None:
        # Only process if message is not from a bot
        if ctx.message.author.bot:
            return

        content = ctx.message.content

        # Check if message starts with command prefix, ends with '?', and is not just '?'
        if self.can_handle(content):
            # Call show method through the show_commands component
            alias = content[len(self.command_prefix) : -1].strip()
            await self.show_commands.show(ctx, alias)

    @commands.command()
    async def save(self, ctx: Context[Bot], alias: str, *, content: str) -> None:
        """Remember content with an alias. Usage: .save <alias> <content>"""
        await self.save_commands.save(ctx, alias, content=content)

    @commands.command()
    async def add(self, ctx: Context[Bot], alias: str, *, content: str) -> None:
        """Add content to an existing entry or create a new one. Usage: .add <alias> <content>"""
        await self.save_commands.add(ctx, alias, content=content)

    @commands.command()
    async def show(self, ctx: Context[Bot], alias: str) -> None:
        """Find a remembered entry by alias. Usage: .show <alias>, or list with .show dir/"""
        await self.show_commands.show(ctx, alias)

    @commands.command()
    async def all(self, ctx: Context[Bot]) -> None:
        """List all remembered entries."""
        await self.show_commands.all(ctx)

    @commands.command()
    async def random(self, ctx: Context[Bot], alias: str) -> None:
        """Get a random non-blank line from an entry. Usage: .random <alias>"""
        await self.show_commands.random(ctx, alias)

    @commands.command()
    async def edit(self, ctx: Context[Bot], alias: str, *, new_content: str) -> None:
        """Edit an existing remembered entry. Usage: .edit <alias> <new_content>"""
        await self.edit_commands.edit(ctx, alias, new_content=new_content)
