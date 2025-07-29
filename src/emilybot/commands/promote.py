from datetime import datetime
from discord.ext.commands import Context, Bot  # pyright: ignore[reportMissingTypeStubs]

import emilybot.db as db
from emilybot.utils.list import first
from emilybot.validation import AliasValidator, ValidationError


class PromoteCommands:
    """Commands for promoting and demoting alias visibility in help."""

    def __init__(self, bot: Bot, db: db.DB, command_prefix: str) -> None:
        self.bot = bot
        self.db = db
        self.command_prefix = command_prefix

    def format_not_found_message(self, alias: str) -> str:
        return f"❓ Alias '{alias}' not found."

    def format_validation_error(self, error_message: str) -> str:
        return f"❌ {error_message}"

    def format_promoted_message(self, alias: str) -> str:
        return f"✅ Alias '{alias}' promoted - will show prominently in help."

    def format_demoted_message(self, alias: str) -> str:
        return f"✅ Alias '{alias}' demoted - will show as grey text at bottom of help."

    def format_already_promoted_message(self, alias: str) -> str:
        return f"ℹ️ Alias '{alias}' is already promoted."

    def format_already_demoted_message(self, alias: str) -> str:
        return f"ℹ️ Alias '{alias}' is already demoted."

    async def _promote_demote_implementation(
        self, ctx: Context[Bot], alias: str, promote: bool
    ) -> None:
        """Shared implementation for promoting/demoting an alias."""
        try:
            AliasValidator.validate_alias(alias, "lookup")

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

            # Check if already in desired state
            if promote and entry.promoted:
                await ctx.send(
                    self.format_already_promoted_message(alias), suppress_embeds=True
                )
                return
            elif not promote and not entry.promoted:
                await ctx.send(
                    self.format_already_demoted_message(alias), suppress_embeds=True
                )
                return

            # Update entry
            entry.promoted = promote
            self.db.remember.update(entry)

            # Log the action
            action = db.Action(
                user_id=user_id,
                timestamp=datetime.now(),
                action=db.ActionPromote(
                    kind="promote",
                    entry_id=entry.id,
                    promoted=promote,
                ),
            )
            self.db.log.add(action)

            # Send appropriate message
            if promote:
                await ctx.send(
                    self.format_promoted_message(alias), suppress_embeds=True
                )
            else:
                await ctx.send(self.format_demoted_message(alias), suppress_embeds=True)

        except ValidationError as e:
            await ctx.send(self.format_validation_error(str(e)), suppress_embeds=True)

    async def promote(self, ctx: Context[Bot], alias: str) -> None:
        """Promote an alias to show prominently in help. Usage: .promote <alias>"""
        await self._promote_demote_implementation(ctx, alias, True)

    async def demote(self, ctx: Context[Bot], alias: str) -> None:
        """Demote an alias to show as grey text at bottom of help. Usage: .demote <alias>"""
        await self._promote_demote_implementation(ctx, alias, False)
