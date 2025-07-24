import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=".", intents=intents)


@bot.event
async def on_ready() -> None:
    print(f"We have logged in as {bot.user}")


@bot.command()
async def remember(ctx: commands.Context[commands.Bot]) -> None:
    await ctx.send("hi i'm remember")


@bot.command()
async def where(ctx: commands.Context[commands.Bot]) -> None:
    await ctx.send("hi i'm where")


def main() -> None:
    TOKEN = os.environ.get("TOKEN")
    if TOKEN is None:
        print("TOKEN is not set")
        exit(1)
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
