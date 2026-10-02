"""Replies for mistakes in how a built-in command was typed."""

import logging
from discord.ext import commands

from emilybot.commands.help import command_usage
from emilybot.discord import EmilyContext


def format_input_error(ctx: EmilyContext, error: commands.UserInputError) -> str:
    command = ctx.command
    assert command is not None
    if isinstance(error, commands.MissingRequiredArgument):
        reason = f"Missing `[{error.param.name}]`."
    else:
        reason = str(error)
    return (
        f"❌ {reason}\n"
        f"Usage: {command_usage(command)}\n"
        f"-# More: `{ctx.bot.just_command_prefix}help {command.name}`"
    )


async def on_command_error(ctx: EmilyContext, error: commands.CommandError) -> None:
    """Reply with usage when a built-in was typed wrong.

    Only argument errors (missing, unparsable or extra arguments) are the
    user's mistake. Everything else, such as an exception raised inside a
    command, is logged and gets no reply, so a bug is not reported to the
    user as bad input.
    """
    if isinstance(error, commands.UserInputError) and ctx.command is not None:
        await ctx.send(format_input_error(ctx, error))
        return
    logging.error(
        f"Error in command {ctx.command}", exc_info=(type(error), error, error.__traceback__)
    )
