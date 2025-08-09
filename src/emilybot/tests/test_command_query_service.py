"""Tests for the CommandQueryService."""

from types import SimpleNamespace
from emilybot.database import DB
from emilybot.command_query_service import CommandQueryService


def test_get_available_commands_server_context(server_context: SimpleNamespace):
    """Test getting available commands in server context."""
    service = CommandQueryService(server_context.db)
    commands = service.get_available_commands(
        server_context.user_id, server_context.server_id
    )

    # Verify results
    assert len(commands) == 3
    command_names = [cmd["name"] for cmd in commands]
    command_by_name = {cmd["name"]: cmd for cmd in commands}

    assert "test-command" in command_names
    assert "another-cmd" in command_names
    assert "other-user-cmd" in command_names
    assert command_by_name["test-command"]["content"] == "This is a test command"
    assert command_by_name["test-command"]["name"] == "test-command"
    assert command_by_name["another-cmd"]["content"] == "Another command content"
    assert command_by_name["another-cmd"]["name"] == "another-cmd"

    # Verify excluded commands
    assert "dm-command" not in command_names


def test_get_available_commands_dm_context(dm_context: SimpleNamespace):
    """Test getting available commands in DM context."""
    service = CommandQueryService(dm_context.db)
    commands = service.get_available_commands(dm_context.user_id, None)

    # Verify results
    assert len(commands) == 2
    command_names = [cmd["name"] for cmd in commands]
    command_by_name = {cmd["name"]: cmd for cmd in commands}

    assert "dm-command" in command_names
    assert "personal-cmd" in command_names
    assert command_by_name["dm-command"]["content"] == "DM only command"
    assert command_by_name["dm-command"]["name"] == "dm-command"
    assert command_by_name["personal-cmd"]["content"] == "Personal command content"
    assert command_by_name["personal-cmd"]["name"] == "personal-cmd"

    # Verify excluded commands
    assert "server-command" not in command_names


def test_get_available_commands_empty_result(db: DB):
    """Test getting available commands when no commands exist."""
    service = CommandQueryService(db)
    commands = service.get_available_commands(12345, 67890)

    # Verify empty result
    assert len(commands) == 0
    assert commands == []
