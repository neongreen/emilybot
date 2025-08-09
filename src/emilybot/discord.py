from discord.message import Message


from discord.ext import commands
from typing import Any

from emilybot.database import DB


class EmilyContext(commands.Context["EmilyBot"]):
    """A custom context class that inherits from commands.Context"""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

    async def send(
        self,
        content: str | None = None,
        *args: Any,
        suppress_embeds: bool = True,
        **kwargs: Any,
    ) -> Message:
        """Like the normal send, but suppresses embeds by default and truncates the message to 2000 characters"""
        if content and len(content) > 2000:
            content = content[: 2000 - 3] + "..."

        return await super().send(
            content, *args, suppress_embeds=suppress_embeds, **kwargs
        )


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
