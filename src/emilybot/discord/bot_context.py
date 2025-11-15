"""Custom Discord context for EmilyBot."""

from discord.ext import commands
from discord.message import Message
from typing import Any, TYPE_CHECKING
import tomllib
from pathlib import Path

from emilybot.discord.views import PaginatedView
from emilybot.discord.message_formatting import split_into_pages

if TYPE_CHECKING:
    from emilybot.discord.bot import EmilyBot


class EmilyContext(commands.Context["EmilyBot"]):
    """A custom context class that inherits from commands.Context"""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

    def _get_config(self) -> dict[str, Any]:
        """Load configuration from config.toml file."""
        config_path = Path("config.toml")
        if config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    return tomllib.load(f)
            except Exception:
                pass
        # Default fallback config
        return {"reactions": {"success": "✔️", "error": "❌"}}

    async def send(
        self,
        content: str | None = None,
        *args: Any,
        suppress_embeds: bool = True,
        **kwargs: Any,
    ) -> Message:
        """Like the normal send, but suppresses embeds by default and supports pagination for long messages.

        Args:
            content: The message content
            suppress_embeds: Whether to suppress link embeds (default: True)
            **kwargs: Additional arguments to pass to discord.py's send
        """
        # If content is short enough, send normally
        if not content or len(content) <= 2000:
            return await super().send(
                content, *args, suppress_embeds=suppress_embeds, **kwargs
            )

        # Split into pages
        pages = split_into_pages(content)

        # If it fits in one page after splitting, send normally
        if len(pages) == 1:
            return await super().send(
                pages[0], *args, suppress_embeds=suppress_embeds, **kwargs
            )

        # Send with pagination
        view = PaginatedView(pages, author_id=self.author.id)
        message = await super().send(
            pages[0], *args, suppress_embeds=suppress_embeds, view=view, **kwargs
        )
        view.message = message
        return message

    async def react_success(self) -> None:
        """Add a checkmark reaction to the current message to indicate success."""
        config = self._get_config()
        success_symbol = config.get("reactions", {}).get("success", "✔️")
        await self.message.add_reaction(success_symbol)
