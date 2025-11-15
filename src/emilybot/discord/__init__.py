"""Discord integration components for EmilyBot.

This package contains:
- bot: EmilyBot class
- bot_context: EmilyContext class
- views: PaginatedView class
- message_formatting: Utility functions for message formatting
"""

from emilybot.discord.bot import EmilyBot
from emilybot.discord.bot_context import EmilyContext
from emilybot.discord.views import PaginatedView
from emilybot.discord.message_formatting import split_into_pages

__all__ = ["EmilyBot", "EmilyContext", "PaginatedView", "split_into_pages"]
