"""Pytest configuration and fixtures."""

import uuid
from discord import Asset, Guild, Member, Message, MessageReference
import pytest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from collections.abc import Callable, Generator
from typing import Any, cast

from emilybot.database import DB, Entry
from emilybot.discord import EmilyBot, EmilyContext


@pytest.fixture
def db() -> Generator[DB, Any, None]:
    """Create a temporary database instance."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        data_dir = temp_path / "data"
        db_instance = DB(data_dir=data_dir)
        yield db_instance


@pytest.fixture
def server_context(
    db: DB, entry_factory: Callable[..., Entry]
) -> Generator[SimpleNamespace, Any, None]:
    """Create a server context with a temporary database and test data."""
    user_id = 12345
    server_id = 67890
    other_user_id = 99999

    # Server-specific command
    entry = entry_factory(name="test-command", content="This is a test command")
    entry.server_id = server_id
    entry.user_id = user_id
    db.remember.add(entry)

    # Promoted server command
    entry = entry_factory(
        name="another-cmd", content="Another command content", promoted=True
    )
    entry.server_id = server_id
    entry.user_id = user_id
    db.remember.add(entry)

    # DM command (should not appear in server context)
    entry = entry_factory(name="dm-command", content="DM only command")
    entry.server_id = None
    entry.user_id = user_id
    db.remember.add(entry)

    # Different user's command (should not appear)
    entry = entry_factory(name="other-user-cmd", content="Other user's command")
    entry.server_id = server_id
    entry.user_id = other_user_id
    db.remember.add(entry)

    yield SimpleNamespace(
        db=db, user_id=user_id, server_id=server_id, other_user_id=other_user_id
    )


# TODO: remove this one
@pytest.fixture
def dm_context(
    db: DB, entry_factory: Callable[..., Entry]
) -> Generator[SimpleNamespace, Any, None]:
    """Create a DM context with a temporary database and test data."""

    # DM command
    entry = entry_factory(name="dm-command", content="DM only command", server_id=None)
    db.remember.add(entry)

    # Another DM command
    entry = entry_factory(
        name="personal-cmd",
        content="Personal command content",
        promoted=True,
        server_id=None,
    )
    db.remember.add(entry)

    # Server command (should not appear in DM context)
    entry = entry_factory(
        name="server-command",
        content="Server only command",
        server_id=777,
    )
    db.remember.add(entry)

    yield SimpleNamespace(db=db, user_id=12345, server_id=777)


@pytest.fixture
def entry_factory() -> Callable[..., Entry]:
    """Create a factory for generating Entry objects."""

    def _factory(
        server_id: int | None = None,
        user_id: int = 12345,
        name: str | None = None,
        content: str | None = None,
        promoted: bool = False,
        run: str | None = None,
    ) -> Entry:
        """Generate an Entry object with default values."""
        return Entry(
            id=uuid.uuid4(),
            server_id=server_id,
            user_id=user_id,
            created_at="2025-01-29T12:00:00Z",
            name=name or "test-entry",
            content=content or "Default content",
            promoted=promoted,
            run=run,
        )

    return _factory


type MakeCtx = Callable[[str, Entry | None], EmilyContext]


@pytest.fixture
def make_ctx(db: DB):
    def _make_ctx(message: str, entry: Entry | None = None) -> EmilyContext:
        """Create a mock context object that mimics EmilyContext."""
        mock = cast(EmilyContext, MagicMock(spec=EmilyContext))
        mock.bot = cast(EmilyBot, MagicMock(spec=EmilyBot))
        mock.bot.db = db
        db.remember.add(entry) if entry else None

        # These must correspond to Discord types, *not* to the Ctx* types

        mock.author = cast(Member, MagicMock(spec=Member))
        mock.author.id = 67890
        mock.author.name = "TestUser_123"  # pyright: ignore[reportAttributeAccessIssue]
        mock.author.display_name = "TestUser"  # pyright: ignore[reportAttributeAccessIssue]
        mock.author.global_name = "TestUser Global"  # pyright: ignore[reportAttributeAccessIssue]
        mock.author.display_avatar = cast(Asset, MagicMock(spec=Asset))  # pyright: ignore[reportAttributeAccessIssue]
        mock.author.display_avatar.url = (
            "https://cdn.discordapp.com/avatars/12345/1234567890.png"  # pyright: ignore[reportAttributeAccessIssue]
        )

        mock.guild = cast(Guild, MagicMock(spec=Guild))
        mock.guild.id = 12345

        mock.message = cast(Message, MagicMock(spec=Message))
        mock.message.content = message
        mock.message.reference = None  # Default to no reference

        return mock

    return _make_ctx


def make_ctx_with_reply(
    db: DB,
    message: str,
    reply_text: str,
    reply_author_name: str,
    entry: Entry | None = None,
) -> EmilyContext:
    """Create a mock context object with a reply to another message."""
    mock = cast(EmilyContext, MagicMock(spec=EmilyContext))
    mock.bot = cast(EmilyBot, MagicMock(spec=EmilyBot))
    mock.bot.db = db
    db.remember.add(entry) if entry else None

    # These must correspond to Discord types, *not* to the Ctx* types

    mock.author = cast(Member, MagicMock(spec=Member))
    mock.author.id = 67890
    mock.author.name = "TestUser_123"  # pyright: ignore[reportAttributeAccessIssue]
    mock.author.display_name = "TestUser"  # pyright: ignore[reportAttributeAccessIssue]
    mock.author.global_name = "TestUser Global"  # pyright: ignore[reportAttributeAccessIssue]
    mock.author.display_avatar = cast(Asset, MagicMock(spec=Asset))  # pyright: ignore[reportAttributeAccessIssue]
    mock.author.display_avatar.url = (
        "https://cdn.discordapp.com/avatars/12345/1234567890.png"  # pyright: ignore[reportAttributeAccessIssue]
    )

    mock.guild = cast(Guild, MagicMock(spec=Guild))
    mock.guild.id = 12345

    # Create the original message that's being replied to
    original_message = cast(Message, MagicMock(spec=Message))
    original_message.content = reply_text
    original_message.author = cast(Member, MagicMock(spec=Member))
    original_message.author.display_name = reply_author_name  # pyright: ignore[reportAttributeAccessIssue]
    original_message.author.global_name = reply_author_name  # pyright: ignore[reportAttributeAccessIssue]
    original_message.author.display_avatar = cast(Asset, MagicMock(spec=Asset))  # pyright: ignore[reportAttributeAccessIssue]
    original_message.author.display_avatar.url = (
        "https://cdn.discordapp.com/avatars/12345/1234567890.png"  # pyright: ignore[reportAttributeAccessIssue]
    )
    original_message.author.id = 90009

    # Create the message reference
    message_ref = cast(MessageReference, MagicMock(spec=MessageReference))
    message_ref.resolved = original_message

    mock.message = cast(Message, MagicMock(spec=Message))
    mock.message.content = message
    mock.message.reference = message_ref

    return mock
