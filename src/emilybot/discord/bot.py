"""EmilyBot Discord bot class."""

from discord.ext import commands
from typing import Any

from emilybot.database import DB
from emilybot.discord.bot_context import EmilyContext


class EmilyBot(commands.Bot):
    def __init__(self, command_prefix: str | list[str], *args: Any, **kwargs: Any):
        super().__init__(command_prefix, *args, **kwargs)
        self.db = DB()
        # Use the first prefix as the primary one for display purposes
        if isinstance(command_prefix, list):
            self.just_command_prefix = command_prefix[0]
        else:
            self.just_command_prefix = command_prefix

    async def get_context(self, *args: Any, **kwargs: Any) -> EmilyContext:
        return await super().get_context(*args, **kwargs, cls=EmilyContext)
