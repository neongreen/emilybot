"""Mock builders for Discord objects in tests."""

from dataclasses import dataclass
from typing import Optional, cast
from discord import (
    Asset,
    DMChannel,
    Guild,
    Member,
    Message,
    MessageReference,
    TextChannel,
    Thread,
)
from unittest.mock import MagicMock


@dataclass
class AuthorConfig:
    """Configuration for creating a mock author."""

    id: int = 67890
    name: str = "TestUser_123"
    display_name: str = "TestUser"
    global_name: str = "TestUser Global"
    avatar_url: str = "https://cdn.discordapp.com/avatars/12345/1234567890.png"


@dataclass
class GuildConfig:
    """Configuration for creating a mock guild."""

    id: int = 12345


@dataclass
class ChannelConfig:
    """Configuration for creating a mock channel."""

    id: int = 55555
    name: str = "general"
    parent_id: Optional[int] = None
    """Set to make the channel a thread of this parent"""


@dataclass
class ReplyConfig:
    """Configuration for creating a mock reply."""

    reply_text: str
    reply_author_name: str
    reply_author_id: int = 90009
    reply_author_avatar_url: str = (
        "https://cdn.discordapp.com/avatars/12345/1234567890.png"
    )


def create_mock_author(config: Optional[AuthorConfig] = None) -> Member:
    """Create a mock Discord Member object.

    Args:
        config: Optional configuration for the author. Uses defaults if not provided.

    Returns:
        Mock Member object configured with the provided settings.
    """
    config = config or AuthorConfig()
    mock = cast(Member, MagicMock(spec=Member))
    mock.id = config.id
    mock.name = config.name  # pyright: ignore[reportAttributeAccessIssue]
    mock.display_name = config.display_name  # pyright: ignore[reportAttributeAccessIssue]
    mock.global_name = config.global_name  # pyright: ignore[reportAttributeAccessIssue]
    mock.display_avatar = cast(Asset, MagicMock(spec=Asset))  # pyright: ignore[reportAttributeAccessIssue]
    mock.display_avatar.url = config.avatar_url  # pyright: ignore[reportAttributeAccessIssue]
    return mock


def create_mock_guild(config: Optional[GuildConfig] = None) -> Guild:
    """Create a mock Discord Guild object.

    Args:
        config: Optional configuration for the guild. Uses defaults if not provided.

    Returns:
        Mock Guild object configured with the provided settings.
    """
    config = config or GuildConfig()
    mock = cast(Guild, MagicMock(spec=Guild))
    mock.id = config.id
    return mock


def create_mock_message_reference(
    reply_text: str, reply_author: Member
) -> MessageReference:
    """Create a mock Discord MessageReference object.

    Args:
        reply_text: The content of the message being replied to.
        reply_author: The author of the message being replied to.

    Returns:
        Mock MessageReference object with resolved message.
    """
    original_message = cast(Message, MagicMock(spec=Message))
    original_message.content = reply_text
    original_message.author = reply_author

    message_ref = cast(MessageReference, MagicMock(spec=MessageReference))
    message_ref.resolved = original_message
    return message_ref


def create_mock_channel(
    config: Optional[ChannelConfig] = None, *, is_dm: bool = False
) -> TextChannel | Thread | DMChannel:
    """Create a mock text channel, thread (when `parent_id` is set), or DM channel."""
    config = config or ChannelConfig()
    if is_dm:
        dm = cast(DMChannel, MagicMock(spec=DMChannel))
        dm.id = config.id
        return dm
    if config.parent_id is not None:
        thread = cast(Thread, MagicMock(spec=Thread))
        thread.id = config.id
        thread.name = config.name
        thread.parent_id = config.parent_id
        return thread
    channel = cast(TextChannel, MagicMock(spec=TextChannel))
    channel.id = config.id
    channel.name = config.name
    return channel
