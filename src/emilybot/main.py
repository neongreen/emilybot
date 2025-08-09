import asyncio
import logging
import os
import discord
import re
import sys
from pathlib import Path
from typing import Any, Optional, assert_never
from discord.ext import commands
from watchfiles import awatch  # type: ignore

from emilybot.discord import EmilyBot, EmilyContext
from emilybot.validation import AliasValidator, ValidationError
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
from emilybot.parser import parse_command, Command, JS


async def execute_dollar_javascript(ctx: EmilyContext, message: str) -> None:
    """Execute a message starting with $ as JavaScript"""
    logging.debug(f"⚡ execute_dollar_javascript: message='{message}'")

    success, output, value = await run_code(ctx, code=message)
    logging.debug(
        f"📊 JavaScript execution result: success={success}, output='{output}', value='{value}'"
    )

    if success:
        logging.debug("✅ JavaScript executed successfully")
        await ctx.send(format_show_content(output, value))
    else:
        logging.debug(f"❌ JavaScript execution failed: {output}")
        await ctx.send(f"❌ JavaScript error: {output}")


async def handle_dollar_command(message: discord.Message, bot: EmilyBot) -> None:
    """Handle messages starting with $ prefix"""

    # Create a context for the message
    ctx = await bot.get_context(message)

    message_content = message.content
    logging.debug(f"🔧 Parsing command: '{message_content}'")

    try:
        parsed = parse_command(message_content)
        logging.debug(f"📝 Parsed result: {type(parsed).__name__} = {parsed}")

        match parsed:
            case Command(cmd=cmd):
                logging.debug(f"🚀 Executing command: '{cmd}'")
                await cmd_cmd(ctx, cmd)
            case JS(code=code):
                logging.debug(f"⚡ Executing JavaScript: '{code}'")
                await execute_dollar_javascript(ctx, code)
            case _:
                logging.debug(f"❌ Unexpected parsed type: {type(parsed)}")
                assert_never(parsed)
    except Exception as e:
        logging.debug(f"💥 Exception during parsing: {type(e).__name__}: {e}")
        logging.error("Error parsing command", exc_info=True)
        await ctx.send(f"❌ Error parsing command: {str(e)}")


async def init_bot(dev: bool) -> EmilyBot:
    intents = discord.Intents.default()
    intents.message_content = True

    if dev:
        logging.info("Running in development mode. Using `##` as command prefix.")
        command_prefix = ["$", "##"]
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

    @bot.listen()
    async def on_message(message: discord.Message) -> None:  # pyright: ignore[reportUnusedFunction]
        logging.debug(
            f"🔍 on_message: content='{message.content}', author={message.author.display_name}"
        )

        if message.author.bot:
            logging.debug("🤖 Skipping bot message")
            return

        # TODO this doesn't actually seem to do anything
        if dev and message.content.startswith("$"):
            logging.debug("🚫 Dev mode: skipping $ message (meant for prod bot)")
            return  # meant for the prod bot

        # Handle $ prefix commands directly
        if message.content.startswith("$ "):
            logging.debug("🔍 Handling $ prefix command")
            await handle_dollar_command(message, bot)
            return

        if dev and message.content.startswith("#"):
            logging.debug(f"🔧 Dev mode: converting #{message.content[1:]} to command")
            message.content = message.content[1:]
            await bot.process_commands(message)

    @bot.listen()
    async def on_command_error(  # pyright: ignore[reportUnusedFunction]
        ctx: EmilyContext,
        error: commands.CommandError,
    ) -> None:
        """Handle command errors gracefully"""
        logging.info(
            f"on_command_error called with error: {error}, message: {ctx.message.content}"
        )
        if isinstance(error, commands.CommandNotFound):
            logging.debug("🔍 CommandNotFound - checking for custom prefixes")

            # skip the dev prefix because it's meant for the dev bot
            if not dev and ctx.message.content.startswith("##"):
                logging.info("Ignoring command meant for the dev bot.")
                return

            # Check if the message starts with any of our prefixes
            message_content = ctx.message.content
            potential_alias = None

            # Check for . prefix first
            if message_content.startswith("."):
                logging.debug("🔍 Checking . prefix")
                potential_alias = message_content[1:].split(" ")[0].strip()
                logging.debug(f"📝 Extracted potential alias: '{potential_alias}'")

                if not potential_alias:
                    logging.debug("❌ No alias found after . prefix")
                    return

                # Bot should refuse to handle anything that can annoy people.
                # Allowed things are: .ab<anything> or $ab<anything>
                if (
                    re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_/]", potential_alias)
                    is None  # avoid .[punctuation] or $[punctuation]
                    or potential_alias.isdecimal()  # avoid .0123 or $0123
                ):
                    logging.info(f"Not treating {potential_alias} as a command.")
                    return

                try:
                    # If it can be an alias, try looking it up
                    logging.debug(f"✅ Validating alias: '{potential_alias}'")
                    AliasValidator.validate_alias(potential_alias, "lookup")
                    logging.debug(f"🚀 Executing command: '{potential_alias}'")
                    await cmd_cmd(ctx, potential_alias)
                    return
                except ValidationError as e:
                    logging.debug(
                        f"❌ Alias validation failed: '{potential_alias}' - {e}"
                    )

                logging.debug(f"❓ Unknown . command: '{potential_alias}'")
                await ctx.send(
                    f"❓ Unknown command. Use `{ctx.bot.just_command_prefix}help` to see available commands.",
                )

        elif isinstance(error, commands.MissingRequiredArgument):
            logging.debug(f"❌ MissingRequiredArgument: {error}")
            param_name = getattr(error, "param", None)
            if param_name:
                await ctx.send(f"❌ Missing required argument: {param_name.name}")
            else:
                await ctx.send("❌ Missing required argument")
        else:
            logging.debug(f"❌ Other command error: {type(error).__name__}: {error}")
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
