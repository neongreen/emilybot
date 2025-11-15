"""Discord UI components for pagination."""

import discord
from discord.message import Message
from typing import Any


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
