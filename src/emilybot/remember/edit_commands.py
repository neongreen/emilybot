from datetime import datetime
from discord.ext.commands import Context, Bot  # pyright: ignore[reportMissingTypeStubs]

import emilybot.remember.db as db
from emilybot.utils.list import first
from emilybot.validation import AliasValidator, ContentValidator, ValidationError


class EditCommands:
    """Commands for editing existing aliases."""

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

    async def _edit_implementation(
        self, ctx: Context[Bot], alias: str, new_content: str
    ) -> None:
        """Shared implementation for editing an existing alias."""
        try:
            # Validate alias and content
            AliasValidator.validate_alias(alias)
            ContentValidator.validate_content(new_content)

            server_id = ctx.guild.id if ctx.guild else None
            user_id = ctx.author.id

            # Find existing entry
            entry = first(
                self.db.find_alias(alias, server_id=server_id, user_id=user_id)
            )

            if not entry:
                await ctx.send(
                    self.format_not_found_message(alias), suppress_embeds=True
                )
                return

            # Update entry
            old_content = entry.content
            entry.content = new_content
            self.db.remember.update(entry)

            action = db.Action(
                user_id=user_id,
                timestamp=datetime.now(),
                action=db.ActionEdit(
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

    async def edit(self, ctx: Context[Bot], alias: str, *, new_content: str) -> None:
        """Edit an existing remembered entry. Usage: .edit <alias> <new_content>"""
        await self._edit_implementation(ctx, alias, new_content)
