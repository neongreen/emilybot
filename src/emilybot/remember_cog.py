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
    def __init__(self, bot: commands.Bot, command_prefix: str) -> None:
        self.bot = bot
        self.db = DB()
        self.inflect = inflect.engine()
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

    # Listen for messages to handle implicit commands like `.foo?` which should trigger `.show foo`
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
            # Call show
            alias = content[len(self.command_prefix) : -1].strip()
            await self.show.callback(self, ctx, alias)  # type: ignore

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
                entry = self.db.find_alias(alias, server_id=server_id)
            else:
                entry = self.db.find_alias(alias, user_id=ctx.author.id)
            if entry:
                await ctx.send(
                    f"❌ Alias '{alias}' already exists", suppress_embeds=True
                )
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

            await ctx.send(self.format_success_message(alias), suppress_embeds=True)

        except ValidationError as e:
            await ctx.send(self.format_validation_error(str(e)), suppress_embeds=True)

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
                entry = first(self.db.find_alias(alias, server_id=server_id))
            else:
                entry = first(self.db.find_alias(alias, user_id=ctx.author.id))

            if not entry:
                await ctx.send(
                    self.format_not_found_message(alias), suppress_embeds=True
                )
                return

            # Update entry
            old_content = entry.content
            entry.content = new_content
            self.db.remember.update(entry)

            action = RememberAction(
                user_id=ctx.author.id,
                timestamp=datetime.now(),
                action=RememberEditAction(
                    kind="edit",
                    entry_id=entry.id,
                    old_content=old_content,
                    new_content=new_content,
                ),
            )
            self.db.log.add(action)

            await ctx.send(
                self.format_success_message(alias, "updated"), suppress_embeds=True
            )

        except ValidationError as e:
            await ctx.send(self.format_validation_error(str(e)), suppress_embeds=True)

    async def _show_implementation(self, ctx: Context[Bot], alias: str) -> None:
        """Shared implementation for finding an alias."""

        server_id = ctx.guild.id if ctx.guild else None

        # `.show all` - list all aliases
        if alias == "all" or alias == "/":
            results = self.db.find_alias(
                re.compile(".*"), server_id=server_id, user_id=ctx.author.id
            )
            plural = self.inflect.plural_noun("entry", len(results))  # type: ignore
            if not results:
                await ctx.send("❓ No aliases found.", suppress_embeds=True)
            else:
                await ctx.send(
                    f"📜 Found {len(results)} {plural}:\n"
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
            plural = self.inflect.plural_noun("entry", len(results))  # type: ignore
            if not results:
                await ctx.send(
                    f"❓ No entries found for prefix '{alias}'.",
                    suppress_embeds=True,
                )
            else:
                await ctx.send(
                    f"📜 Found {len(results)} {plural} for '{alias}':\n"
                    + "\n".join(f"- {entry.name}" for entry in results),
                    suppress_embeds=True,
                )

        else:
            entry = first(
                self.db.find_alias(alias, server_id=server_id, user_id=ctx.author.id)
            )
            if entry:
                await ctx.send(entry.content, suppress_embeds=True)
            else:
                await ctx.send(
                    self.format_not_found_message(alias), suppress_embeds=True
                )

    @commands.command()
    async def save(self, ctx: Context[Bot], alias: str, *, content: str) -> None:
        """Remember content with an alias. Usage: .save <alias> <content>"""
        await self._remember_implementation(ctx, alias, content)

    @commands.command()
    async def show(self, ctx: Context[Bot], alias: str) -> None:
        """Find a remembered entry by alias. Usage: .show <alias>, or list with .show dir/"""
        await self._show_implementation(ctx, alias)

    @commands.command()
    async def all(self, ctx: Context[Bot]) -> None:
        """List all remembered entries."""
        await self._show_implementation(ctx, "all")

    @commands.command()
    async def edit(self, ctx: Context[Bot], alias: str, *, new_content: str) -> None:
        """Edit an existing remembered entry. Usage: .edit <alias> <new_content>"""
        await self._edit_implementation(ctx, alias, new_content)
