"""Pytest configuration and fixtures.

Test Fixtures:
- db: Temporary database instance
- entry_factory: Factory for creating Entry objects
- make_ctx: Flexible factory for creating mock EmilyContext
  - Supports replies, DM contexts, custom author/guild
- server_context: Pre-populated server with test data

Examples:
    # Basic context
    ctx = make_ctx("message content")

    # Context with entry
    ctx = make_ctx("message", entry)

    # Context with reply
    ctx = make_ctx(
        "reply message",
        reply=ReplyConfig(reply_text="original", reply_author_name="User")
    )

    # DM context
    ctx = make_ctx("dm message", is_dm=True)
"""

import logging
import uuid
from discord import Message
import pytest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, cast
from collections.abc import Callable, Generator
from typing import Any, Optional

from emilybot.database import DB, Entry
from emilybot.discord import EmilyBot, EmilyContext
from emilybot.test_utils import (
    AuthorConfig,
    GuildConfig,
    ReplyConfig,
    create_mock_author,
    create_mock_guild,
    create_mock_message_reference,
)

# Configure logging for tests
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


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


MakeCtx = Callable[..., EmilyContext]


@pytest.fixture
def make_ctx(db: DB) -> MakeCtx:
    """Create a flexible context factory that handles all test scenarios.

    Args:
        db: Database fixture

    Returns:
        Factory function for creating mock EmilyContext objects
    """

    def _make_ctx(
        message: str,
        entry: Optional[Entry] = None,
        *,
        reply: Optional[ReplyConfig] = None,
        author: Optional[AuthorConfig] = None,
        guild: Optional[GuildConfig] = None,
        is_dm: bool = False,
    ) -> EmilyContext:
        """Create a mock context with flexible configuration.

        Args:
            message: The message content
            entry: Optional entry to add to DB
            reply: Optional reply configuration for message references
            author: Optional author configuration (uses defaults if not provided)
            guild: Optional guild configuration (uses defaults if not provided)
            is_dm: If True, sets guild to None (overrides guild parameter)

        Returns:
            Mock EmilyContext object configured as specified
        """
        mock = cast(EmilyContext, MagicMock(spec=EmilyContext))
        mock.bot = cast(EmilyBot, MagicMock(spec=EmilyBot))
        mock.bot.db = db

        if entry:
            db.remember.add(entry)

        # Create author
        mock.author = create_mock_author(author)

        # Create guild (None for DM)
        if is_dm:
            mock.guild = None
        else:
            mock.guild = create_mock_guild(guild)

        # Create message
        mock.message = cast(Message, MagicMock(spec=Message))
        mock.message.content = message

        # Handle reply if provided
        if reply:
            reply_author = create_mock_author(
                AuthorConfig(
                    id=reply.reply_author_id,
                    name=reply.reply_author_name,
                    display_name=reply.reply_author_name,
                    global_name=reply.reply_author_name,
                    avatar_url=reply.reply_author_avatar_url,
                )
            )
            mock.message.reference = create_mock_message_reference(
                reply.reply_text, reply_author
            )
        else:
            mock.message.reference = None

        return mock

    return _make_ctx
