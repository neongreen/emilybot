"""Tests for command invocation functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from emilybot.commands.run import cmd_cmd
from emilybot.conftest import MakeCtx
from typing import Callable
from emilybot.database import Entry


@pytest.mark.parametrize("message", [".cmd test", ".test", "$test"])
@pytest.mark.asyncio
async def test_cmd_command_with_empty_args(
    make_ctx: MakeCtx, entry_factory: Callable[..., Entry], message: str
):
    """Test .cmd command with an empty list of arguments using different message formats."""
    # Create a test command entry
    entry = entry_factory(
        name="test",
        content=".",
        run="console.log(args)",
        user_id=67890,  # Match the user ID from make_ctx
        server_id=12345,  # Match the guild ID from make_ctx
    )
    ctx = make_ctx(message, entry)

    # Set up the required bot attribute
    ctx.bot.just_command_prefix = "."

    # Test with empty args list
    await cmd_cmd(ctx, alias="test", args=[])

    # Verify send was called with the output
    assert isinstance(ctx.send, (MagicMock, AsyncMock))
    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert call_args == "[]"


@pytest.mark.parametrize(
    "message", [".cmd test-cmd hello", ".test-cmd hello", "$test-cmd hello"]
)
@pytest.mark.asyncio
async def test_cmd_command_with_single_arg(
    make_ctx: MakeCtx, entry_factory: Callable[..., Entry], message: str
):
    """Test .cmd command with a single argument using different message formats."""
    entry = entry_factory(
        name="test-cmd",
        content="Test command content",
        run="console.log('First arg:', args[0]); console.log('Args length:', args.length)",
        user_id=67890,  # Match the user ID from make_ctx
        server_id=12345,  # Match the guild ID from make_ctx
    )
    ctx = make_ctx(message, entry)

    # Set up the required bot attribute
    ctx.bot.just_command_prefix = "."

    # Test with single argument
    await cmd_cmd(ctx, alias="test-cmd", args=["hello"])

    # Verify send was called with the output
    assert isinstance(ctx.send, (MagicMock, AsyncMock))
    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert "First arg: hello" in call_args
    assert "Args length: 1" in call_args


@pytest.mark.parametrize(
    "message",
    [".cmd test-cmd hello world", ".test-cmd hello world", "$test-cmd hello world"],
)
@pytest.mark.asyncio
async def test_cmd_command_with_multiple_args(
    make_ctx: MakeCtx, entry_factory: Callable[..., Entry], message: str
):
    """Test .cmd command with multiple arguments using different message formats."""
    entry = entry_factory(
        name="test-cmd",
        content="Test command content",
        run="console.log('Args:', args); console.log('First:', args[0]); console.log('Second:', args[1])",
        user_id=67890,  # Match the user ID from make_ctx
        server_id=12345,  # Match the guild ID from make_ctx
    )
    ctx = make_ctx(message, entry)

    # Set up the required bot attribute
    ctx.bot.just_command_prefix = "."

    # Test with multiple arguments
    await cmd_cmd(ctx, alias="test-cmd", args=["hello", "world"])

    # Verify send was called with the output
    assert isinstance(ctx.send, (MagicMock, AsyncMock))
    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert 'Args: [ "hello", "world" ]' in call_args
    assert "First: hello" in call_args
    assert "Second: world" in call_args


@pytest.mark.asyncio
async def test_cmd_command_alias_not_found(make_ctx: MakeCtx):
    """Test .cmd command when alias is not found."""
    ctx = make_ctx(".cmd nonexistent", None)

    # Set up the required bot attribute
    ctx.bot.just_command_prefix = "."

    # Test with non-existent alias
    await cmd_cmd(ctx, alias="nonexistent", args=[])

    # Verify send was called with error message
    assert isinstance(ctx.send, (MagicMock, AsyncMock))
    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert "not found" in call_args.lower()


@pytest.mark.parametrize("message", [".cmd dm-cmd", ".dm-cmd", "$dm-cmd"])
@pytest.mark.asyncio
async def test_cmd_command_in_dm_context(
    make_ctx: MakeCtx, entry_factory: Callable[..., Entry], message: str
):
    """Test .cmd command in DM context (no guild) using different message formats."""
    entry = entry_factory(
        name="dm-cmd",
        content="DM command content",
        run="console.log('DM command executed with args:', args)",
        user_id=67890,  # Match the user ID from make_ctx
    )
    ctx = make_ctx(message, entry)
    ctx.guild = None  # Simulate DM context

    # Set up the required bot attribute
    ctx.bot.just_command_prefix = "."

    # Test in DM context
    await cmd_cmd(ctx, alias="dm-cmd", args=[])

    # Verify send was called with the output
    assert isinstance(ctx.send, (MagicMock, AsyncMock))
    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert "DM command executed with args: []" in call_args


@pytest.mark.parametrize("message", [".cmd working", ".working", "$working"])
@pytest.mark.asyncio
async def test_cmd_command_with_broken_javascript_present(
    make_ctx: MakeCtx, entry_factory: Callable[..., Entry], message: str
):
    """Test .cmd command when there's broken JavaScript in another command in the database."""
    # Create a working command that the user will call
    working_entry = entry_factory(
        name="working",
        content="Working command content",
        run="console.log('Working command executed with args:', args)",
        user_id=67890,  # Match the user ID from make_ctx
        server_id=12345,  # Match the guild ID from make_ctx
    )

    # Create a broken command with invalid JavaScript (but user won't call this one)
    broken_entry = entry_factory(
        name="broken-js",
        content="Broken JS command content",
        run="console.log('This is valid JS'); console.log(args); syntax error here;",
        user_id=67890,  # Match the user ID from make_ctx
        server_id=12345,  # Match the guild ID from make_ctx
    )

    # Set up context with both entries in the database
    ctx = make_ctx(message, working_entry)
    # Add the broken entry to the database as well
    ctx.bot.db.remember.add(broken_entry)

    # Set up the required bot attribute
    ctx.bot.just_command_prefix = "."

    # Test the working command (should work despite broken JS being present elsewhere)
    await cmd_cmd(ctx, alias="working", args=["test"])

    # Verify send was called with the working command's output
    assert isinstance(ctx.send, (MagicMock, AsyncMock))
    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]

    # The working command should execute successfully
    assert 'Working command executed with args: [ "test" ]' in call_args
