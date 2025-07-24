import asyncio
import logging
import os
import discord
from discord.ext import commands
from discord.ext.commands import Bot  # pyright: ignore[reportMissingTypeStubs]

from emilybot.remember_cog import RememberCog


async def init_bot() -> Bot:
    intents = discord.Intents.default()
    intents.message_content = True

    bot = Bot(
        command_prefix=".",
        intents=intents,
        allowed_mentions=discord.AllowedMentions.none(),
    )

    async def on_ready() -> None:
        print(f"We have logged in as {bot.user}")

    bot.add_listener(on_ready)

    async def on_command_error(
        ctx: commands.Context[commands.Bot], error: commands.CommandError
    ) -> None:
        """Handle command errors gracefully"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.send("❓ Unknown command. Use `.help` to see available commands.")
        elif isinstance(error, commands.MissingRequiredArgument):
            param_name = getattr(error, "param", None)
            if param_name:
                await ctx.send(f"❌ Missing required argument: {param_name.name}")
            else:
                await ctx.send("❌ Missing required argument")
        else:
            await ctx.send(f"❌ An error occurred: {str(error)}")
            logging.error("An error occurred", exc_info=error)

    bot.add_listener(on_command_error)

    await bot.add_cog(RememberCog(bot))

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
    bot = await init_bot()
    await bot.start(TOKEN)


def main() -> None:
    """Run the bot."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception:
        logging.exception("An unexpected error occurred")
