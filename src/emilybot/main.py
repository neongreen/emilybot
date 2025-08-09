import asyncio
import logging
import os
import discord
import sys
from pathlib import Path
from typing import Any, Optional, assert_never
from discord.ext import commands
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

    logging.debug(f"⚡ execute_js: code='{code}'")

    success, output, value = await run_code(ctx, code=code)
    logging.debug(
        f"📊 JavaScript execution result: success={success}, output='{output}', value='{value}'"
    )

    if success:
        logging.debug("✅ JavaScript executed successfully")
        await ctx.send(format_show_content(output, value))
    else:
        logging.debug(f"❌ JavaScript execution failed: {output}")
        await ctx.send(f"❌ JavaScript error: {output}")


async def handle_message(message: discord.Message, bot: EmilyBot, dev: bool) -> None:
    """Handle messages using our own parsing logic.
    This is used for most of the commands, except the ones defined via @command.
    (TODO: get rid of @command entirely.)
    """

    # Create a context for the message
    ctx = await bot.get_context(message)

    message_content = message.content
    logging.debug(f"🔧 Parsing command: '{message_content}'")

    try:
        # In dev mode we use #$ instead of $ for JS
        if dev and message_content.startswith("#$"):
            message_content = message_content[1:]

        parsed = parse_message(message_content)
        logging.debug(f"📝 Parsed result: {type(parsed).__name__} = {parsed}")

        # Note: ctx.args doesn't give us args :(
        match parsed:
            case Command(cmd=cmd, args=args):
                logging.debug(f"🚀 Executing command: '{cmd}' with args: {args}")
                await cmd_cmd(ctx, cmd, args=args)
            case JS(code=code):
                logging.debug(f"⚡ Executing JavaScript: '{code}'")
                await execute_js(ctx, code)
            case ListChildren(parent=parent):
                logging.debug(f"📜 Listing children of: '{parent}'")
                await cmd_show(ctx, f"{parent}/")
            case None:
                logging.debug("🔍 No action found")
                return
            case _:
                assert_never(parsed)
    except Exception as e:
        logging.debug(f"💥 Exception during parsing: {type(e).__name__}: {e}")
        logging.error("Error parsing command", exc_info=True)
        await ctx.send(f"❌ Error parsing command: {str(e)}")


async def init_bot(dev: bool) -> EmilyBot:
    intents = discord.Intents.default()
    intents.message_content = True

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

    @bot.listen()
    async def on_message(message: discord.Message) -> None:  # pyright: ignore[reportUnusedFunction]
        if message.author.bot:
            logging.debug("🤖 Skipping bot message")
            return

        # This is only used when the command is not defined via @command.
        await handle_message(message, bot, dev)

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

            # Try to handle . prefix commands using parse_command
            if not dev and ctx.message.content.startswith("."):
                logging.debug("🔍 Checking . prefix with parse_command")
                try:
                    parsed = parse_message(ctx.message.content, extra_prefixes=["."])
                    match parsed:
                        case Command(cmd=cmd, args=args):
                            logging.debug(
                                f"🚀 Executing . command: '{cmd}' with args: {args}"
                            )
                            await cmd_cmd(ctx, cmd, args=args)
                            return
                        case ListChildren(parent=parent):
                            logging.debug(f"📜 Listing children of: '{parent}'")
                            await cmd_show(ctx, f"{parent}/")
                            return
                        case JS():
                            # This shouldn't happen for . prefix, but handle it gracefully
                            logging.debug(
                                "❌ Unexpected JS result for . prefix command"
                            )
                            await ctx.send(
                                f"❓ Unknown command. Use `{ctx.bot.just_command_prefix}help` to see available commands.",
                            )
                            return
                        case None:
                            logging.debug("🔍 No action found")
                            return
                        case _:
                            assert_never(parsed)
                except Exception as e:
                    logging.debug(
                        f"❌ Error parsing . command: {type(e).__name__}: {e}"
                    )
                    await ctx.send(
                        f"❓ Unknown command. Use `{ctx.bot.just_command_prefix}help` to see available commands.",
                    )
                    return

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
