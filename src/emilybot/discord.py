from discord.message import Message


from discord.ext import commands
from typing import Any
import tomllib
from pathlib import Path
import discord

from emilybot.database import DB


class PaginatedView(discord.ui.View):
    """A view with Previous/Next buttons for paginating long messages."""

    def __init__(self, pages: list[str], *, author_id: int, timeout: float = 180.0):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0
        self.message: Message | None = None
        self.author_id = author_id
        self._update_buttons()

    def _update_buttons(self) -> None:
        """Update button states based on current page."""
        # Get the buttons from the children list
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.label == "◀ Previous":
                    item.disabled = self.current_page == 0
                elif item.label == "Next ▶":
                    item.disabled = self.current_page >= len(self.pages) - 1

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        """Go to the previous page."""
        # Only allow the original author to navigate
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the command author can navigate pages.", ephemeral=True
            )
            return

        if self.current_page > 0:
            self.current_page -= 1
            self._update_buttons()
            try:
                await interaction.response.edit_message(
                    content=self.pages[self.current_page], view=self
                )
            except discord.HTTPException:
                # Message was deleted or bot lost permissions
                pass

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        """Go to the next page."""
        # Only allow the original author to navigate
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the command author can navigate pages.", ephemeral=True
            )
            return

        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self._update_buttons()
            try:
                await interaction.response.edit_message(
                    content=self.pages[self.current_page], view=self
                )
            except discord.HTTPException:
                # Message was deleted or bot lost permissions
                pass

    @discord.ui.button(label="✕", style=discord.ButtonStyle.danger)
    async def close_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        """Close the pagination and remove buttons."""
        # Only allow the original author to close
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the command author can close pagination.", ephemeral=True
            )
            return

        if self.message:
            try:
                await interaction.response.edit_message(view=None)
            except discord.HTTPException:
                # Message was deleted or bot lost permissions
                pass
        self.stop()

    async def on_timeout(self) -> None:
        """Remove buttons when the view times out."""
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                pass


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

    def _split_into_pages(self, content: str, max_length: int = 1900) -> list[str]:
        """Split content into pages that fit within Discord's message limit.

        Uses max_length of 1900 to leave room for page indicators.
        """
        if len(content) <= max_length:
            return [content]

        pages: list[str] = []
        lines = content.split("\n")
        current_page = ""

        for line in lines:
            # If adding this line would exceed the limit, start a new page
            if len(current_page) + len(line) + 1 > max_length:
                if current_page:
                    pages.append(current_page)
                    current_page = ""

                # If a single line is too long, split it by character
                if len(line) > max_length:
                    while line:
                        chunk = line[:max_length]
                        pages.append(chunk)
                        line = line[max_length:]
                else:
                    current_page = line + "\n"
            else:
                current_page += line + "\n"

        # Add the last page if there's content
        if current_page:
            pages.append(current_page)

        # Add page indicators
        if len(pages) > 1:
            pages = [
                f"{page.rstrip()}\n\n*Page {i + 1}/{len(pages)}*"
                for i, page in enumerate(pages)
            ]

        return pages

    async def send(
        self,
        content: str | None = None,
        *args: Any,
        suppress_embeds: bool = True,
        paginate: bool = True,
        **kwargs: Any,
    ) -> Message:
        """Like the normal send, but suppresses embeds by default and supports pagination for long messages.

        Args:
            content: The message content
            suppress_embeds: Whether to suppress link embeds (default: True)
            paginate: Whether to use pagination for long messages (default: True)
            **kwargs: Additional arguments to pass to discord.py's send
        """
        # If content is short enough or pagination is disabled, send normally
        if not content or len(content) <= 2000 or not paginate:
            if content and len(content) > 2000:
                content = content[: 2000 - 3] + "..."
            return await super().send(
                content, *args, suppress_embeds=suppress_embeds, **kwargs
            )

        # Split into pages
        pages = self._split_into_pages(content)

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
