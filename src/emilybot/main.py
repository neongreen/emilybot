import asyncio
import logging
import os
import discord
import re
from discord.ext import commands
from discord.ext.commands import Context, Bot  # pyright: ignore[reportMissingTypeStubs]

import emilybot.db as db
from emilybot.validation import AliasValidator, ValidationError
from emilybot.commands.save import SaveCommands
from emilybot.commands.show import ShowCommands
from emilybot.commands.edit import EditCommands
from emilybot.commands.delete import DeleteCommands
from emilybot.commands.help import HelpCommands


async def init_bot(dev: bool) -> Bot:
    intents = discord.Intents.default()
    intents.message_content = True

    if dev:
        logging.info("Running in development mode. Using `.dev.` as command prefix.")
        command_prefix = ".dev."
    else:
        logging.info("Running in production mode. Using `.` as command prefix.")
        command_prefix = "."

    bot = Bot(
        command_prefix=command_prefix,
        intents=intents,
        allowed_mentions=discord.AllowedMentions.none(),
    )
    bot.remove_command("help")

    database = db.DB()

    save_commands = SaveCommands(bot, database, command_prefix)
    show_commands = ShowCommands(bot, database, command_prefix)
    edit_commands = EditCommands(bot, database, command_prefix)
    delete_commands = DeleteCommands(bot, database, command_prefix)
    help_commands = HelpCommands(bot, database, command_prefix)

    @bot.listen()
    async def on_ready() -> None:  # pyright: ignore[reportUnusedFunction]
        logging.info(f"We have logged in as {bot.user}")

    @bot.listen()
    async def on_command_error(  # pyright: ignore[reportUnusedFunction]
        ctx: Context[commands.Bot],
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
                await show_commands.show(ctx, potential_alias)
                return
            except ValidationError:
                pass

            # ok it's not an alias so it's an unknown command then
            await ctx.send(
                f"❓ Unknown command. Use `{command_prefix}help` to see available commands."
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

    @bot.command()
    async def add(ctx: Context[Bot], alias: str, *, content: str) -> None:  # pyright: ignore[reportUnusedFunction]
        """Add content to an existing entry or create a new one. Usage: .add <alias> <content>"""
        await save_commands.add(ctx, alias, content=content)

    @bot.command()
    async def random(ctx: Context[Bot], alias: str) -> None:  # pyright: ignore[reportUnusedFunction]
        """Get a random non-blank line from an entry. Usage: .random <alias>"""
        await show_commands.random(ctx, alias)

    @bot.command()
    async def edit(ctx: Context[Bot], alias: str, *, new_content: str) -> None:  # pyright: ignore[reportUnusedFunction]
        """Edit an existing remembered entry. Usage: .edit <alias> <new_content>"""
        await edit_commands.edit(ctx, alias, new_content=new_content)

    @bot.command()
    async def rm(ctx: Context[Bot], alias: str) -> None:  # pyright: ignore[reportUnusedFunction]
        """Delete an alias. Usage: .rm <alias>. 'Children' (foo/bar, etc) will not be deleted."""
        await delete_commands.rm(ctx, alias)

    @bot.command(name="help")
    async def help_command(ctx: Context[Bot]) -> None:  # pyright: ignore[reportUnusedFunction]
        """Shows this help message."""
        await help_commands.help(ctx)

    return bot


async def main_async() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )
    TOKEN = os.environ.get("TOKEN")
    if TOKEN is None:
        print("TOKEN is not set")
        exit(1)
    dev_mode = os.environ.get("DEV_MODE", "false").lower() == "true"
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
