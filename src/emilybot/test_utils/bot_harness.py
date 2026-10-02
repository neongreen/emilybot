"""Drive the real bot's message handling with fake Discord messages.

`BotHarness.say(...)` passes a fake message to the same `on_message` handler
production uses, so built-in command dispatch, the alias parser, the command
error listener and the JavaScript executor all run for real. Only the
Discord edges are replaced: replies and reactions are recorded instead of
sent, and nothing connects to Discord.
"""

import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Optional, cast
from unittest.mock import MagicMock

import pytest
from discord import Message

import emilybot.discord.bot
from emilybot.database import DB
from emilybot.discord import EmilyBot, EmilyContext
from emilybot.main import init_bot
from emilybot.test_utils.mock_builders import (
    AuthorConfig,
    ChannelConfig,
    GuildConfig,
    create_mock_author,
    create_mock_channel,
    create_mock_guild,
)


@dataclass
class Sent:
    replies: list[str] = field(default_factory=lambda: [])
    reactions: list[str] = field(default_factory=lambda: [])


@dataclass
class BotHarness:
    bot: EmilyBot
    sent: Sent

    async def say(
        self,
        content: str,
        *,
        author_id: int = 67890,
        guild_id: Optional[int] = 12345,
        channel: Optional[ChannelConfig] = None,
        author_name: Optional[str] = None,
    ) -> list[str]:
        """Send `content` as a message and return the replies it produced.

        `guild_id=None` sends it as a DM.
        """
        before = len(self.sent.replies)
        message = cast(Message, MagicMock(spec=Message))
        message.content = content
        author = create_mock_author(
            AuthorConfig(id=author_id)
            if author_name is None
            else AuthorConfig(id=author_id, name=author_name, display_name=author_name)
        )
        author.bot = False  # pyright: ignore[reportAttributeAccessIssue]
        message.author = author
        message.guild = (
            None if guild_id is None else create_mock_guild(GuildConfig(id=guild_id))
        )
        message.reference = None
        message.channel = create_mock_channel(channel, is_dm=guild_id is None)
        tasks_before = asyncio.all_tasks()
        await self.bot.on_message(message)
        # Command errors are delivered as separately scheduled event tasks.
        while pending := asyncio.all_tasks() - tasks_before - {asyncio.current_task()}:
            await asyncio.gather(*pending)
            tasks_before |= pending
        return self.sent.replies[before:]


async def make_bot_harness(db: DB, monkeypatch: pytest.MonkeyPatch) -> BotHarness:
    """Build the production bot (non-dev prefixes) around a test database."""
    sent = Sent()

    async def fake_send(
        self: EmilyContext, content: Optional[str] = None, *args: Any, **kwargs: Any
    ) -> Message:
        sent.replies.append(content or "")
        return cast(Message, SimpleNamespace(id=len(sent.replies)))

    async def fake_react_success(self: EmilyContext) -> None:
        sent.reactions.append(self.message.content)

    monkeypatch.setattr(EmilyContext, "send", fake_send)
    monkeypatch.setattr(EmilyContext, "react_success", fake_react_success)

    # The bot would otherwise open the default `data/` directory.
    monkeypatch.setattr(emilybot.discord.bot, "DB", lambda: db)
    bot = await init_bot(dev=False)
    # Event dispatch needs the loop that login would normally set up.
    bot.loop = asyncio.get_running_loop()
    # get_context compares the author with the logged-in user.
    bot._connection.user = SimpleNamespace(id=1)  # pyright: ignore[reportAttributeAccessIssue, reportPrivateUsage]
    return BotHarness(bot=bot, sent=sent)
