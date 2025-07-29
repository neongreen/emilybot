from datetime import datetime
from discord.ext.commands import Context, Bot  # pyright: ignore[reportMissingTypeStubs]
import uuid

import emilybot.db as db
from emilybot.utils.list import first
from emilybot.validation import AliasValidator, ValidationError


class SaveCommands:
    """Commands for saving and adding content to aliases."""

    def __init__(self, bot: Bot, db: db.DB, command_prefix: str) -> None:
        self.bot = bot
        self.db = db
        self.command_prefix = command_prefix

    def format_not_found_message(self, alias: str) -> str:
        """Format a helpful error message when an alias is not found."""
        return (
            f"❓ Alias '{alias}' not found.\n"
            f"💡 Use `{self.command_prefix}add {alias} <text>` to create this alias."
        )

    def format_validation_error(self, error_message: str) -> str:
        """Format validation error messages for user-friendly display."""
        return f"❌ {error_message}"

    def format_success_message(self, alias: str, action: str = "stored") -> str:
        """Format success message for remember operations."""
        return f"✅ Alias '{alias}' {action} successfully."

    async def add(self, ctx: Context[Bot], alias: str, content: str) -> None:
        """Add content to an existing entry or create a new one. Usage: .add <alias> <content>"""
        try:
            # Validate alias and content
            AliasValidator.validate_alias(alias, "create")
            if not content.strip():
                raise ValidationError("Text to add cannot be empty.")

            server_id = ctx.guild.id if ctx.guild else None

            # Find existing entry
            entry = first(
                self.db.find_alias(alias, server_id=server_id, user_id=ctx.author.id)
            )

            if entry:
                # Entry exists - append content with blank line
                old_content = entry.content
                entry.content = f"{old_content}\n\n{content}"
                self.db.remember.update(entry)

                action = db.Action(
                    user_id=ctx.author.id,
                    timestamp=datetime.now(),
                    action=db.ActionEdit(
                        kind="edit",
                        entry_id=entry.id,
                        old_content=old_content,
                        new_content=entry.content,
                    ),
                )
                self.db.log.add(action)

                await ctx.send(
                    self.format_success_message(alias, "updated"), suppress_embeds=True
                )
            else:
                # Entry doesn't exist - create new one
                doc = db.Entry(
                    id=uuid.uuid4(),
                    server_id=server_id,
                    user_id=ctx.author.id,
                    created_at=datetime.now().isoformat(),
                    name=alias.lower(),
                    content=content,
                )
                self.db.remember.add(doc)

                action = db.Action(
                    user_id=ctx.author.id,
                    timestamp=datetime.now(),
                    action=db.ActionCreate(
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
