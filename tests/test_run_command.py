"""Tests for the .run command."""

import pytest
from unittest.mock import AsyncMock
from emilybot.commands.run import cmd_run
from emilybot.discord import EmilyContext


class MockBot:
    """Mock bot for testing."""

    pass


class MockAuthor:
    """Mock author for testing."""

    def __init__(self, user_id: int = 123456789):
        self.id = user_id


class MockGuild:
    """Mock guild for testing."""

    def __init__(self, guild_id: int = 987654321):
        self.id = guild_id


@pytest.mark.asyncio
async def test_run_command_basic_execution():
    """Test basic JavaScript execution with .run command."""
    # Create mock context
    ctx = AsyncMock(spec=EmilyContext)
    ctx.bot = MockBot()
    ctx.author = MockAuthor()
    ctx.guild = MockGuild()

    # Test basic console.log
    await cmd_run(ctx, code='console.log("Hello, world!")')

    # Verify send was called with the output
    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert "Hello, world!" in call_args


@pytest.mark.asyncio
async def test_run_command_with_backticks():
    """Test .run command with code wrapped in backticks."""
    ctx = AsyncMock(spec=EmilyContext)
    ctx.bot = MockBot()
    ctx.author = MockAuthor()
    ctx.guild = MockGuild()

    # Test with triple backticks
    code_with_backticks = """```js
console.log("Test with backticks")
```"""

    await cmd_run(ctx, code=code_with_backticks)

    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert "Test with backticks" in call_args


@pytest.mark.asyncio
async def test_run_command_no_output():
    """Test .run command with code that produces no output."""
    ctx = AsyncMock(spec=EmilyContext)
    ctx.bot = MockBot()
    ctx.author = MockAuthor()
    ctx.guild = MockGuild()

    # Test code that doesn't produce output
    await cmd_run(ctx, code="let x = 5;")

    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert "JavaScript executed successfully" in call_args
    assert "no output" in call_args


@pytest.mark.asyncio
async def test_run_command_syntax_error():
    """Test .run command with syntax error."""
    ctx = AsyncMock(spec=EmilyContext)
    ctx.bot = MockBot()
    ctx.author = MockAuthor()
    ctx.guild = MockGuild()

    # Test invalid JavaScript syntax
    await cmd_run(ctx, code='console.log("missing quote)')

    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert "❌" in call_args or "⚠️" in call_args  # Error indicator should be present


@pytest.mark.asyncio
async def test_run_command_dm_context():
    """Test .run command in DM (no guild)."""
    ctx = AsyncMock(spec=EmilyContext)
    ctx.bot = MockBot()
    ctx.author = MockAuthor()
    ctx.guild = None  # DM context

    await cmd_run(ctx, code='console.log("DM test")')

    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert "DM test" in call_args
