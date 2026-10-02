"""Download, review and confirm a frozen set of alias definitions."""

import asyncio
import io
import logging
import time
from typing import Any
import weakref

import discord
from discord.ext import commands

from emilybot.atomic_json_db import DBSaveError
from emilybot.commands.install_plan import (
    InstallPlan,
    apply_plan,
    compile_plan,
    review_text,
)
from emilybot.commands.install_source import InstallError, MAX_BYTES, fetch_source
from emilybot.discord import EmilyContext

MAX_PENDING = 32
MAX_WORK = 4


class InstallState:
    def __init__(self) -> None:
        self.pending: dict[int, InstallView] = {}
        self.working: set[int] = set()


_states: weakref.WeakKeyDictionary[Any, InstallState] = weakref.WeakKeyDictionary()


def install_state(bot: Any) -> InstallState:
    state = _states.get(bot)
    if state is None:
        state = InstallState()
        _states[bot] = state
    return state


class InstallView(discord.ui.View):
    def __init__(
        self, ctx: EmilyContext, plan: InstallPlan, state: InstallState
    ) -> None:
        super().__init__(timeout=300)
        self.ctx = ctx
        self.plan = plan
        self.state = state
        self.deadline = time.monotonic() + 300
        self.finished = False
        self.message: discord.Message | None = None

    def finish(self) -> None:
        self.finished = True
        if self.state.pending.get(self.plan.user_id) is self:
            self.state.pending.pop(self.plan.user_id)
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction[Any]) -> bool:
        if (
            interaction.user.id != self.plan.user_id
            or interaction.guild_id != self.plan.server_id
        ):
            await interaction.response.send_message(
                "Only the invoker can use this preview here.", ephemeral=True
            )
            return False
        if (
            self.finished
            or time.monotonic() >= self.deadline
            or self.state.pending.get(self.plan.user_id) is not self
        ):
            await interaction.response.send_message(
                "This preview is no longer active. Run .install again.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Install", style=discord.ButtonStyle.success)
    async def install(
        self, interaction: discord.Interaction[Any], button: discord.ui.Button[Any]
    ) -> None:
        # Guard again inside the callback before its first await. Concurrent clicks cannot apply twice.
        if not await self.interaction_check(interaction):
            return
        self.finish()
        try:
            apply_plan(self.ctx.bot.db, self.plan)
            result = "Installed the definitions. No code or examples were run."
        except InstallError as e:
            result = str(e)
        except DBSaveError as e:
            logging.exception("Install save failed")
            if e.path == self.ctx.bot.db.log.file_path:
                result = "Definitions were saved, but saving their history failed."
                if e.file_state == "new":
                    result = "Definitions and history were written, but the disk did not confirm history was stored."
                elif e.file_state == "unknown":
                    result = "Definitions were saved, but history saving failed partway. Stored history contents are unknown."
            elif e.file_state == "new":
                result = "Definitions were written, but the disk did not confirm storage. History was not saved."
            elif e.file_state == "unknown":
                result = "Saving definitions failed partway. Stored file contents are unknown; memory kept the previous definitions. History was not saved."
            else:
                result = "Saving definitions failed. Nothing was changed."
        await interaction.response.edit_message(
            content=result, view=self, allowed_mentions=discord.AllowedMentions.none()
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(
        self, interaction: discord.Interaction[Any], button: discord.ui.Button[Any]
    ) -> None:
        if not await self.interaction_check(interaction):
            return
        self.finish()
        await interaction.response.edit_message(
            content="Installation cancelled.", view=self
        )

    async def on_timeout(self) -> None:
        self.finish()
        if self.message:
            try:
                await self.message.edit(
                    content="Installation preview expired. Run .install again.",
                    view=self,
                )
            except discord.HTTPException:
                pass


@commands.command(name="install")
async def cmd_install(ctx: EmilyContext, *, source: str = "") -> None:
    """`.install [HTTPS file link]`: Review and install fenced definitions, or attach one .md/.txt file."""
    state = install_state(ctx.bot)
    user_id = ctx.author.id
    if user_id in state.working or len(state.working) >= MAX_WORK:
        await ctx.send("An installer is busy. Try again shortly.")
        return
    attachments = ctx.message.attachments
    source = source.strip()
    if (
        (bool(source) + bool(attachments)) != 1
        or len(attachments) > 1
        or (source and len(source.split()) != 1)
    ):
        await ctx.send("Use one HTTPS file link or one attached .md/.txt file.")
        return
    if attachments:
        attachment = attachments[0]
        if not attachment.filename.lower().endswith((".md", ".txt")):
            await ctx.send("Attach one .md or .txt file.")
            return
        if attachment.size > MAX_BYTES:
            await ctx.send("The file exceeds 256 KiB.")
            return
        source = attachment.url
    previous = state.pending.get(user_id)
    if previous:
        previous.finish()
    if len(state.pending) + len(state.working) >= MAX_PENDING:
        await ctx.send("Too many pending installation previews. Try again shortly.")
        return
    state.working.add(user_id)
    try:
        body = await fetch_source(source)
        async with asyncio.timeout(60):
            plan = await compile_plan(
                ctx.bot.db, body, ctx.guild.id if ctx.guild else None, user_id
            )
        if not plan.changed:
            await ctx.send(
                "Already installed. No definitions, history or stores changed."
            )
            return
        review = review_text(plan)
        # Complete old/new values are kept in a text attachment, never truncated.
        file = discord.File(
            io.BytesIO(review.encode("utf-8")), filename="install-review.txt"
        )
        view = InstallView(ctx, plan, state)
        state.pending[user_id] = view
        try:
            view.message = await ctx.send(
                "Review install-review.txt for every alias and the complete old/new content and code.\n"
                "Definitions are processed in order without running code. .add creates or replaces content.\n"
                f"{len(plan.changed)} aliases change; {len(plan.skipped)} example blocks are skipped.\n"
                "Install or Cancel within five minutes.",
                file=file,
                view=view,
                allowed_mentions=discord.AllowedMentions.none(),
                suppress_embeds=True,
            )
        except BaseException:
            view.finish()
            raise
    except (InstallError, TimeoutError) as e:
        await ctx.send(
            str(e) or "Checking the definitions timed out. Nothing was changed.",
            allowed_mentions=discord.AllowedMentions.none(),
            suppress_embeds=True,
        )
    finally:
        state.working.remove(user_id)
