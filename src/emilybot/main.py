import asyncio
import logging
import os
import discord
import sys
import subprocess
from pathlib import Path
from typing import Any, Optional, assert_never
from watchfiles import awatch  # type: ignore

from emilybot.discord import EmilyBot, EmilyContext
from emilybot.commands.save import cmd_add
from emilybot.commands.show import cmd_list, cmd_random, cmd_show
from emilybot.commands.edit import cmd_edit
from emilybot.commands.delete import cmd_rm
from emilybot.commands.help import cmd_help
from emilybot.commands.promote import cmd_promote, cmd_demote, cmd_demote_all
from emilybot.commands.set import cmd_set
from emilybot.commands.run import cmd_cmd, cmd_run
from emilybot.execute.run_code import run_code
from emilybot.format import format_show_content
from emilybot.parser import parse_message, Command, JS, ListChildren


async def execute_js(ctx: EmilyContext, code: str) -> None:
    """Execute JavaScript. All wrapping like '$ ', '```js`, etc should be handled by the parser."""

    success, output, value = await run_code(ctx, code=code)

    if success:
        await ctx.send(format_show_content(output, value))
    else:
        await ctx.send(output)  # Error message is already formatted


async def init_bot(dev: bool) -> EmilyBot:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.reactions = True  # Required for on_reaction_add

    if dev:
        logging.info("Running in development mode. Using `#$` as command prefix.")
        command_prefix = ["#$"]
    else:
        logging.info(
            "Running in production mode. Using `.` and `$` as command prefixes."
        )
        command_prefix = [".", "$"]

    bot = EmilyBot(
        command_prefix=command_prefix,
        intents=intents,
        allowed_mentions=discord.AllowedMentions.none(),
    )
    bot.remove_command("help")

    bot.add_command(cmd_add)
    bot.add_command(cmd_show)
    bot.add_command(cmd_random)
    bot.add_command(cmd_edit)
    bot.add_command(cmd_rm)
    bot.add_command(cmd_help)
    bot.add_command(cmd_promote)
    bot.add_command(cmd_demote)
    bot.add_command(cmd_demote_all)
    bot.add_command(cmd_list)
    bot.add_command(cmd_set)
    bot.add_command(cmd_run)
    bot.add_command(cmd_cmd)

    @bot.listen()
    async def on_ready() -> None:  # pyright: ignore[reportUnusedFunction]
        logging.info(f"We have logged in as {bot.user}")

        # Send startup notification to availablegreen
        try:
            # Get git commit info (skip if not in a git repo)
            try:
                commit_hash = subprocess.check_output(
                    ["git", "rev-parse", "--short", "HEAD"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
                commit_msg = subprocess.check_output(
                    ["git", "log", "-1", "--pretty=%B"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
                commit_info = f"**Commit:** `{commit_hash}`\n**Message:** {commit_msg}"
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Not in a git repo or git not available
                commit_info = "*No git info available*"

            # Send DM to Ema
            try:
                user = await bot.fetch_user(328950281570353153)  # Ema
                await user.send(f"🚀 **Bot started!**\n\n{commit_info}")
                logging.info(f"Sent startup notification to {user.name}")
            except discord.NotFound:
                logging.warning("Could not find Ema (ID: 328950281570353153)")
            except discord.Forbidden:
                logging.warning("Cannot DM Ema (privacy settings)")
        except Exception as e:
            logging.error(f"Failed to send startup notification: {e}")

    @bot.listen()
    async def on_raw_reaction_add(  # pyright: ignore[reportUnusedFunction]
        payload: discord.RawReactionActionEvent,
    ) -> None:
        """Delete bot messages when specific reactions are added.

        Uses raw events to work with both cached and uncached messages.
        """
        # Ignore bot reactions
        if payload.user_id == bot.user.id:  # type: ignore
            return

        # Define deletion emojis
        # - Custom emoji: <:miss:1363721012801179779>
        # - Unicode: 🗑️ (wastebasket) and ❌ (x)
        deletion_emojis = {
            "1363721012801179779",  # Custom emoji ID (just the ID number)
            "🗑️",  # Wastebasket
            "❌",  # X mark
        }

        # Check if the reaction emoji matches any deletion emoji
        emoji_str = str(payload.emoji)
        # For custom emojis, use the ID
        if payload.emoji.id:
            emoji_str = str(payload.emoji.id)

        if emoji_str not in deletion_emojis:
            return

        # Fetch the message to check if it's from the bot
        try:
            channel = bot.get_channel(payload.channel_id)
            if channel is None:
                channel = await bot.fetch_channel(payload.channel_id)

            if not isinstance(channel, discord.abc.Messageable):
                return

            message = await channel.fetch_message(payload.message_id)

            # Only delete if it's the bot's own message
            if message.author != bot.user:
                return

            await message.delete()
            logging.info(
                f"Deleted message {message.id} after {emoji_str} reaction from user {payload.user_id}"
            )
        except discord.NotFound:
            # Message was already deleted
            pass
        except discord.Forbidden:
            logging.warning(
                f"Cannot delete message {payload.message_id} - missing permissions"
            )
        except Exception as e:
            logging.error(f"Error deleting message: {e}", exc_info=True)

    async def on_message(message: discord.Message) -> None:
        """
        Override the default on_message handler to handle our own commands.
        """

        if message.author.bot:
            return

        ctx = await bot.get_context(message)
        if ctx.command:
            await bot.invoke(ctx)
            return

        # If we get here, it's not a built-in command (registered via @command).
        # We use our own parsing logic then.

        message_content = message.content

        try:
            # In dev mode we use #$ instead of $ for JS
            if dev and message_content.startswith("#$"):
                message_content = message_content[1:]

            parsed = parse_message(message_content, extra_prefixes=[] if dev else ["."])

            # Note: ctx.args doesn't give us args :(
            match parsed:
                case Command(cmd=cmd, args=args):
                    await cmd_cmd(ctx, cmd, args=args)
                case JS(code=code):
                    await execute_js(ctx, code)
                case ListChildren(parent=parent):
                    await cmd_show(ctx, f"{parent}/")
                case None:
                    return
                case _:
                    assert_never(parsed)

        except Exception as e:
            logging.error("Error parsing command", exc_info=True)
            await ctx.send(f"❌ Error parsing command: {str(e)}")

    bot.on_message = on_message

    return bot


async def run_bot_with_autoreload() -> None:
    """Run the bot with autoreload in development mode."""

    TOKEN = os.environ.get("TOKEN")
    if TOKEN is None:
        print("❌ TOKEN is not set")
        sys.exit(1)

    bot_task: Optional[asyncio.Task[Any]] = None
    watch_paths = [Path("src/emilybot"), Path(".")]

    async def start_bot():
        nonlocal bot_task
        if bot_task and not bot_task.done():
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass

        logging.info("🚀 Starting bot...")
        dev_mode = os.environ.get("DEV_MODE", "false").lower() == "true"
        bot = await init_bot(dev_mode)
        bot_task = asyncio.create_task(bot.start(TOKEN))

    async def stop_bot():
        nonlocal bot_task
        if bot_task and not bot_task.done():
            logging.info("🛑 Stopping bot...")
            bot_task.cancel()
            try:
                await bot_task
            except asyncio.CancelledError:
                pass

    def is_relevant_file(file_path: str) -> bool:
        """Check if a file change should trigger a restart."""
        path = Path(file_path)
        return (
            path.suffix == ".py"
            and "__pycache__" not in path.parts
            and not path.name.startswith(".")
        ) or path.name == "config.toml"

    try:
        # Start the bot initially
        await start_bot()

        # Watch for changes
        logging.info(
            f"👀 Watching for changes in: {', '.join(str(p) for p in watch_paths)}"
        )
        async for changes in awatch(*watch_paths, recursive=True):
            relevant_changes = [
                change for change in changes if is_relevant_file(change[1])
            ]

            if relevant_changes:
                logging.info(
                    f"📝 Detected changes: {[Path(change[1]).name for change in relevant_changes]}"
                )
                logging.info("🔄 Restarting process...")
                # Restart the process
                os.execv(sys.executable, [sys.executable] + sys.argv)

    except KeyboardInterrupt:
        logging.info("🔄 Bot stopped by user")
    except Exception:
        logging.exception("💥 Unexpected error in development server")
    finally:
        await stop_bot()


async def main_async() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )

    # Silence discord.py's verbose logging
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)

    TOKEN = os.environ.get("TOKEN")
    if TOKEN is None:
        print("❌ TOKEN is not set")
        sys.exit(1)
    dev_mode = os.environ.get("DEV_MODE", "false").lower() == "true"

    if dev_mode:
        logging.info("🔧 Starting in development mode with autoreload...")
        await run_bot_with_autoreload()
    else:
        logging.info("🚀 Starting in production mode...")
        bot = await init_bot(dev_mode)
        await bot.start(TOKEN)


def main() -> None:
    """Run the bot."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception:
        logging.exception("An unexpected error occurred")
