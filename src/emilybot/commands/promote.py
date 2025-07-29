from datetime import datetime
from discord.ext import commands
from emilybot.discord import EmilyContext

from emilybot.database import Action, ActionPromote
from emilybot.utils.list import first
from emilybot.validation import AliasValidator, ValidationError


def format_not_found_message(alias: str) -> str:
    return f"❓ Alias '{alias}' not found."


def format_validation_error(error_message: str) -> str:
    return f"❌ {error_message}"


def format_promoted_message(alias: str) -> str:
    return f"✅ Alias '{alias}' promoted - will show prominently in help."


def format_demoted_message(alias: str) -> str:
    return f"✅ Alias '{alias}' demoted - will show as grey text at bottom of help."


def format_already_promoted_message(alias: str) -> str:
    return f"ℹ️ Alias '{alias}' is already promoted."


def format_already_demoted_message(alias: str) -> str:
    return f"ℹ️ Alias '{alias}' is already demoted."


async def _promote_demote_implementation(
    ctx: EmilyContext, alias: str, promote: bool
) -> None:
    """Shared implementation for promoting/demoting an alias."""

    db = ctx.bot.db

    try:
        AliasValidator.validate_alias(alias, "lookup")

        server_id = ctx.guild.id if ctx.guild else None
        user_id = ctx.author.id

        # Find existing entry
        entry = first(db.find_alias(alias, server_id=server_id, user_id=user_id))

        if not entry:
            await ctx.send(format_not_found_message(alias))
            return

        # Check if this is a top-level LAS (no "/" in name)
        if "/" in entry.name:
            await ctx.send(
                format_validation_error(
                    "Only top-level aliases can be promoted or demoted."
                )
            )
            return

        # Check if already in desired state
        if promote and entry.promoted:
            await ctx.send(format_already_promoted_message(alias))
            return
        elif not promote and not entry.promoted:
            await ctx.send(format_already_demoted_message(alias))
            return

        # Update entry
        entry.promoted = promote
        db.remember.update(entry)

        # Log the action
        action = Action(
            user_id=user_id,
            timestamp=datetime.now(),
            action=ActionPromote(
                kind="promote",
                entry_id=entry.id,
                promoted=promote,
            ),
        )
        db.log.add(action)

        # Send appropriate message
        if promote:
            await ctx.send(format_promoted_message(alias))
        else:
            await ctx.send(format_demoted_message(alias))

    except ValidationError as e:
        await ctx.send(format_validation_error(str(e)))


@commands.command(name="promote")
async def cmd_promote(ctx: EmilyContext, alias: str) -> None:
    """`.promote [alias]`: Promote an alias to show prominently in help."""
    await _promote_demote_implementation(ctx, alias, True)


@commands.command(name="demote")
async def cmd_demote(ctx: EmilyContext, alias: str) -> None:
    """`.demote [alias]`: Demote an alias to show as grey text at bottom of help."""
    await _promote_demote_implementation(ctx, alias, False)


@commands.command(name="demote_all")
async def cmd_demote_all(ctx: EmilyContext) -> None:
    """`.demote_all`: Demote all promoted aliases to show as grey text at bottom of help."""
    db = ctx.bot.db
    server_id = ctx.guild.id if ctx.guild else None
    user_id = ctx.author.id

    # Find all promoted top-level aliases for this user/server
    if server_id:
        all_entries = db.remember.find(server_id=server_id)
    else:
        all_entries = db.remember.find(user_id=user_id, server_id=None)

    # Filter for promoted top-level aliases (no "/" in name)
    promoted_entries = [
        entry for entry in all_entries if entry.promoted and "/" not in entry.name
    ]

    if not promoted_entries:
        await ctx.send("ℹ️ No promoted aliases found to demote.")
        return

    # Demote all found entries
    demoted_count = 0
    for entry in promoted_entries:
        entry.promoted = False
        db.remember.update(entry)

        # Log the action
        action = Action(
            user_id=user_id,
            timestamp=datetime.now(),
            action=ActionPromote(
                kind="promote",
                entry_id=entry.id,
                promoted=False,
            ),
        )
        db.log.add(action)
        demoted_count += 1

    if demoted_count == 1:
        await ctx.send("✅ Demoted 1 alias - will show as grey text at bottom of help.")
    else:
        await ctx.send(
            f"✅ Demoted {demoted_count} aliases - will show as grey text at bottom of help."
        )
