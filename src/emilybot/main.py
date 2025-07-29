import asyncio
import logging
import os
import discord
import re
import sys
from pathlib import Path
from typing import Any, Optional
from discord.ext import commands
from watchfiles import awatch  # type: ignore

from emilybot.discord import EmilyBot
from emilybot.validation import AliasValidator, ValidationError
from emilybot.commands.save import cmd_add
from emilybot.commands.show import cmd_list, cmd_random, cmd_show
from emilybot.commands.edit import cmd_edit
from emilybot.commands.delete import cmd_rm
from emilybot.commands.help import cmd_help
from emilybot.commands.promote import cmd_promote, cmd_demote, cmd_demote_all


async def init_bot(dev: bool) -> EmilyBot:
    intents = discord.Intents.default()
    intents.message_content = True

    if dev:
        logging.info("Running in development mode. Using `.dev.` as command prefix.")
        command_prefix = ".dev."
    else:
        logging.info("Running in production mode. Using `.` as command prefix.")
        command_prefix = "."

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

    @bot.listen()
    async def on_ready() -> None:  # pyright: ignore[reportUnusedFunction]
        logging.info(f"We have logged in as {bot.user}")

    @bot.listen()
    async def on_command_error(  # pyright: ignore[reportUnusedFunction]
        ctx: commands.Context[EmilyBot],
        error: commands.CommandError,
    ) -> None:
        """Handle command errors gracefully"""
        logging.info(
            f"on_command_error called with error: {error}, message: {ctx.message.content}"
        )
        if isinstance(error, commands.CommandNotFound):
            # skip .dev. because it's meant for the dev bot
            if not dev and ctx.message.content.startswith(".dev."):
                logging.info("Ignoring command meant for the dev bot.")
                return

            # Bot should refuse to handle anything that can annoy people.
            # Allowed things are: .ab<anything>
            msg_without_prefix = ctx.message.content[len(command_prefix) :]
            if not re.match(r"^[a-zA-Z][a-zA-Z0-9_/]", msg_without_prefix):
                logging.info(f"Not treating {msg_without_prefix} as a command.")
                return

            # Extract the command part (everything after prefix, before first space)
            potential_alias = msg_without_prefix.split(" ")[0].strip()

            try:
                # If it can be an alias, try looking it up
                AliasValidator.validate_alias(potential_alias, "lookup")
                await cmd_show(ctx, potential_alias)
                return
            except ValidationError:
                pass

            # ok it's not an alias so it's an unknown command then
            await ctx.send(
                f"❓ Unknown command. Use `{command_prefix}help` to see available commands.",
            )

        elif isinstance(error, commands.MissingRequiredArgument):
            param_name = getattr(error, "param", None)
            if param_name:
                await ctx.send(f"❌ Missing required argument: {param_name.name}")
            else:
                await ctx.send("❌ Missing required argument")
        else:
            await ctx.send(f"❌ An error occurred: {str(error)}")
            logging.error("An error occurred", exc_info=error)

    return bot


async def run_bot_with_autoreload() -> None:
    """Run the bot with autoreload in development mode."""

    TOKEN = os.environ.get("TOKEN")
    if TOKEN is None:
        print("❌ TOKEN is not set")
        sys.exit(1)

    bot_task: Optional[asyncio.Task[Any]] = None
    watch_paths = [Path("src/emilybot")]

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
        )

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
                await stop_bot()
                await asyncio.sleep(0.5)  # Brief pause before restart
                await start_bot()

    except KeyboardInterrupt:
        logging.info("🔄 Bot stopped by user")
    except Exception:
        logging.exception("💥 Unexpected error in development server")
    finally:
        await stop_bot()


async def main_async() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )
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
