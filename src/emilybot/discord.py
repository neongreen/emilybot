"""Discord integration for EmilyBot.

DEPRECATED: This module is a compatibility layer. Import from the following modules instead:
- emilybot.discord.bot: EmilyBot class
- emilybot.discord.bot_context: EmilyContext class
- emilybot.discord.views: PaginatedView class
- emilybot.discord.message_formatting: Utility functions
"""

# Re-export everything from the new modules for backward compatibility
from emilybot.discord.bot import EmilyBot
from emilybot.discord.bot_context import EmilyContext
from emilybot.discord.views import PaginatedView
from emilybot.discord.message_formatting import split_into_pages

__all__ = ["EmilyBot", "EmilyContext", "PaginatedView", "split_into_pages"]
