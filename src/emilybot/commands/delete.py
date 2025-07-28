from datetime import datetime
from discord.ext.commands import Context, Bot  # pyright: ignore[reportMissingTypeStubs]

import emilybot.db as db
from emilybot.utils.list import first
from emilybot.validation import AliasValidator, ValidationError


class DeleteCommands:
    """Commands for deleting existing aliases."""

    def __init__(self, bot: Bot, db: db.DB, command_prefix: str) -> None:
        self.bot = bot
        self.db = db
        self.command_prefix = command_prefix

    def format_not_found_message(self, alias: str) -> str:
        return f"❓ Alias '{alias}' not found."

    def format_validation_error(self, error_message: str) -> str:
        return f"❌ {error_message}"

    def format_deleted_message(self, alias: str) -> str:
        return f"✅ Fine. '{alias}' was deleted."

    async def rm(self, ctx: Context[Bot], alias: str) -> None:
        """Delete an existing remembered entry. Usage: .rm <alias>"""

        try:
            AliasValidator.validate_alias(alias, "delete")

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

            # Delete entry
            self.db.remember.remove(entry.id)

            action = db.Action(
                user_id=user_id,
                timestamp=datetime.now(),
                action=db.ActionDelete(
                    kind="delete",
                    entry_id=entry.id,
                    entry=entry,
                ),
            )
            self.db.log.add(action)

            await ctx.send(self.format_deleted_message(alias), suppress_embeds=True)

        except ValidationError as e:
            await ctx.send(self.format_validation_error(str(e)), suppress_embeds=True)
