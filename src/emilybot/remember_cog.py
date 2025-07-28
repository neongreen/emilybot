from datetime import datetime
from typing import Literal, Optional
from dataclasses import dataclass
from discord.ext import commands
from discord.ext.commands import Context, Bot  # pyright: ignore[reportMissingTypeStubs]
from typed_json_db import JsonDB
from pathlib import Path
import uuid

from emilybot.validation import AliasValidator, ContentValidator, ValidationError


@dataclass
class RememberEditAction:
    """Represents an edit action on a remember entry."""

    kind: Literal["edit"]
    entry_id: uuid.UUID
    old_content: str
    new_content: str


@dataclass
class RememberCreateAction:
    """Represents a create action on a remember entry."""

    kind: Literal["create"]
    server_id: Optional[int]
    name: str
    content: str
    entry_id: uuid.UUID


@dataclass
class RememberAction:
    timestamp: datetime
    user_id: int
    action: RememberCreateAction | RememberEditAction


@dataclass
class RememberEntry:
    """Rows in the `remember` table"""

    id: uuid.UUID
    """Unique ID"""

    server_id: Optional[int]
    """In which server was this entry added. `None` means it was in DMs with the bot"""

    user_id: int
    """Which user added this entry"""

    created_at: str  # ISO format datetime string
    """When"""

    name: str
    """E.g. "manual", will be normalized to lowercase"""

    content: str
    """E.g. link to that manual"""


class DB:
    def __init__(self) -> None:
        # Ensure data directory exists with proper permissions
        data_dir = Path("data")
        data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize JsonDB with type annotation
        self.remember = JsonDB[RememberEntry](
            RememberEntry, data_dir / "remember.json", primary_key="id"
        )
        self.log = JsonDB[RememberAction](
            RememberAction, data_dir / "remember_log.json"
        )

    def find_alias_server(self, server_id: int, alias: str) -> Optional[RememberEntry]:
        """Find an alias (server scope) in the database."""
        results = self.remember.find(server_id=server_id, name=alias.lower())  # type: ignore
        if results:
            return results[0]
        return None

    def find_alias_personal(self, user_id: int, alias: str) -> Optional[RememberEntry]:
        """Find an alias (personal scope) in the database."""
        results = self.remember.find(  # type: ignore
            user_id=user_id, server_id=None, name=alias.lower()
        )
        if results:
            return results[0]
        return None


class RememberCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db = DB()

    def format_not_found_message(self, alias: str) -> str:
        """Format a helpful error message when an alias is not found."""
        return (
            f"❓ Alias '{alias}' not found.\n"
            f"💡 Use `.save {alias} <text>` to create this alias."
        )

    def format_validation_error(self, error_message: str) -> str:
        """Format validation error messages for user-friendly display."""
        return f"❌ {error_message}"

    def format_success_message(self, alias: str, action: str = "stored") -> str:
        """Format success message for remember operations."""
        return f"✅ Alias '{alias}' {action} successfully."

    def format_retrieved_content(self, alias: str, content: str) -> str:
        """Format retrieved content."""
        return f"📝 **{alias}**:\n{content}"

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if self.bot.user:
            print(f"RememberCog loaded in {self.bot.user.name}")
        else:
            print("RememberCog loaded, but bot user is not available yet.")

    async def _remember_implementation(
        self, ctx: Context[Bot], alias: str, content: str
    ) -> None:
        """Shared implementation for remember and learn commands."""
        try:
            # Validate alias and content
            AliasValidator.validate_alias(alias)
            ContentValidator.validate_content(content)

            guild = ctx.guild
            server_id = guild.id if guild else None

            # Check if entry already exists
            if server_id:
                existing = self.db.find_alias_server(server_id, alias)
            else:
                existing = self.db.find_alias_personal(ctx.author.id, alias)
            if existing:
                await ctx.send(f"❌ Alias '{alias}' already exists")
                return

            # Add new entry
            doc = RememberEntry(
                id=uuid.uuid4(),
                server_id=server_id,
                user_id=ctx.author.id,
                created_at=datetime.now().isoformat(),
                name=alias.lower(),
                content=content,
            )
            self.db.remember.add(doc)

            action = RememberAction(
                user_id=ctx.author.id,
                timestamp=datetime.now(),
                action=RememberCreateAction(
                    kind="create",
                    entry_id=doc.id,
                    server_id=server_id,
                    name=alias.lower(),
                    content=content,
                ),
            )
            self.db.log.add(action)

            await ctx.send(self.format_success_message(alias))

        except ValidationError as e:
            await ctx.send(self.format_validation_error(str(e)))

    async def _edit_implementation(
        self, ctx: Context[Bot], alias: str, new_content: str
    ) -> None:
        """Shared implementation for editing an existing alias."""
        try:
            # Validate alias and content
            AliasValidator.validate_alias(alias)
            ContentValidator.validate_content(new_content)

            guild = ctx.guild
            server_id = guild.id if guild else None

            # Find existing entry
            if server_id:
                existing = self.db.find_alias_server(server_id, alias)
            else:
                existing = self.db.find_alias_personal(ctx.author.id, alias)

            if not existing:
                await ctx.send(self.format_not_found_message(alias))
                return

            # Update entry
            old_content = existing.content
            existing.content = new_content
            self.db.remember.update(existing)

            action = RememberAction(
                user_id=ctx.author.id,
                timestamp=datetime.now(),
                action=RememberEditAction(
                    kind="edit",
                    entry_id=existing.id,
                    old_content=old_content,
                    new_content=new_content,
                ),
            )
            self.db.log.add(action)

            await ctx.send(self.format_success_message(alias, "updated"))

        except ValidationError as e:
            await ctx.send(self.format_validation_error(str(e)))

    async def _find_implementation(self, ctx: Context[Bot], key: str) -> None:
        """Shared implementation for finding an alias."""

        guild = ctx.guild
        server_id = guild.id if guild else None

        if server_id:
            result = self.db.find_alias_server(server_id, key)
        else:
            result = self.db.find_alias_personal(ctx.author.id, key)

        if result:
            await ctx.send(self.format_retrieved_content(key, result.content))
        else:
            await ctx.send(self.format_not_found_message(key))

    @commands.command()
    async def save(self, ctx: Context[Bot], alias: str, *, content: str) -> None:
        """Remember content with an alias. Usage: .save <alias> <content>"""
        await self._remember_implementation(ctx, alias, content)

    @commands.command()
    async def show(self, ctx: Context[Bot], key: str) -> None:
        """Find a remembered entry by key. Usage: .show <key>"""
        await self._find_implementation(ctx, key)

    @commands.command()
    async def edit(self, ctx: Context[Bot], alias: str, *, new_content: str) -> None:
        """Edit an existing remembered entry. Usage: .edit <alias> <new_content>"""
        await self._edit_implementation(ctx, alias, new_content)


async def setup(bot: Bot) -> None:
    await bot.add_cog(RememberCog(bot))
