from datetime import datetime
import re
from typing import Literal, Optional, overload
from dataclasses import dataclass
from discord.ext import commands
from discord.ext.commands import Context, Bot  # pyright: ignore[reportMissingTypeStubs]
from typed_json_db import JsonDB
from pathlib import Path
import uuid
import inflect

from emilybot.validation import AliasValidator, ContentValidator, ValidationError


def first[T](iterable: list[T]) -> T | None:
    """Return the first element of a list or None if empty."""
    return iterable[0] if iterable else None


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

    @overload
    def find_alias(
        self,
        alias: str | re.Pattern[str],
        *,
        server_id: int,
        user_id: int | None = None,
    ) -> list[RememberEntry]: ...

    @overload
    def find_alias(
        self,
        alias: str | re.Pattern[str],
        *,
        user_id: int,
        server_id: int | None = None,
    ) -> list[RememberEntry]: ...

    def find_alias(
        self,
        alias: str | re.Pattern[str],
        *,
        server_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> list[RememberEntry]:
        """Find an alias in the database."""
        if server_id is not None:
            if isinstance(alias, str):
                results = self.remember.find(  # type: ignore
                    server_id=server_id, name=alias.lower()
                )
            else:
                results = self.remember.find(  # type: ignore
                    server_id=server_id
                )
                results = [entry for entry in results if alias.match(entry.name)]

        elif user_id is not None:
            if isinstance(alias, str):
                results = self.remember.find(  # type: ignore
                    user_id=user_id, server_id=None, name=alias.lower()
                )
            else:
                results = self.remember.find(  # type: ignore
                    user_id=user_id, server_id=None
                )
                results = [entry for entry in results if alias.match(entry.name)]
        else:
            raise ValueError("Either server_id or user_id must be provided")

        return results


class RememberCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db = DB()
        self.inflect = inflect.engine()

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
                existing = self.db.find_alias(alias, server_id=server_id)
            else:
                existing = self.db.find_alias(alias, user_id=ctx.author.id)
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
                existing = first(self.db.find_alias(alias, server_id=server_id))
            else:
                existing = first(self.db.find_alias(alias, user_id=ctx.author.id))

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

    async def _find_implementation(self, ctx: Context[Bot], alias: str | None) -> None:
        """Shared implementation for finding an alias."""

        server_id = ctx.guild.id if ctx.guild else None

        # `.show all` - list all aliases
        if alias == "all" or alias == "/" or alias == "" or alias is None:
            results = self.db.find_alias(
                re.compile(".*"), server_id=server_id, user_id=ctx.author.id
            )
            plural = self.inflect.plural_noun("entry", len(results))  # type: ignore
            if not results:
                await ctx.send("❓ No aliases found.")
            else:
                await ctx.send(
                    f"📜 Found {len(results)} {plural}':\n"
                    + ", ".join(entry.name for entry in results)
                )

        # `.show foo/` - list all aliases starting with "foo/"
        elif alias.endswith("/"):
            # list by prefix
            results = self.db.find_alias(
                re.compile("^" + re.escape(alias), re.IGNORECASE),
                server_id=server_id,
                user_id=ctx.author.id,
            )
            plural = self.inflect.plural_noun("entry", len(results))  # type: ignore
            if not results:
                await ctx.send(f"❓ No entries found for prefix '{alias}'.")
            else:
                await ctx.send(
                    f"📜 Found {len(results)} {plural} for '{alias}':\n"
                    + "\n".join(f"- {entry.name}" for entry in results)
                )

        else:
            existing = first(
                self.db.find_alias(alias, server_id=server_id, user_id=ctx.author.id)
            )
            if existing:
                await ctx.send(self.format_retrieved_content(alias, existing.content))
            else:
                await ctx.send(self.format_not_found_message(alias))

    @commands.command()
    async def save(self, ctx: Context[Bot], alias: str, *, content: str) -> None:
        """Remember content with an alias. Usage: .save <alias> <content>"""
        await self._remember_implementation(ctx, alias, content)

    @commands.command()
    async def show(self, ctx: Context[Bot], alias: str | None) -> None:
        """Find a remembered entry by alias. Usage: .show <alias> or just .show to list all"""
        await self._find_implementation(ctx, alias)

    @commands.command()
    async def edit(self, ctx: Context[Bot], alias: str, *, new_content: str) -> None:
        """Edit an existing remembered entry. Usage: .edit <alias> <new_content>"""
        await self._edit_implementation(ctx, alias, new_content)


async def setup(bot: Bot) -> None:
    await bot.add_cog(RememberCog(bot))
