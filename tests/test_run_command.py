"""Tests for the .run command."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from emilybot.commands.run import cmd_run
from tests.conftest import MakeCtx


@pytest.mark.asyncio
async def test_run_command_basic_execution(make_ctx: MakeCtx):
    """Test basic JavaScript execution with .run command."""
    code = 'console.log("Hello, world!")'
    ctx = make_ctx(f".run {code}", None)

    # Test basic console.log
    await cmd_run(ctx, code=code)

    # Verify send was called with the output
    assert isinstance(ctx.send, (MagicMock, AsyncMock))
    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert "Hello, world!" in call_args


@pytest.mark.asyncio
async def test_run_command_with_backticks(make_ctx: MakeCtx):
    """Test .run command with code wrapped in backticks."""
    # Test with triple backticks
    code = """```js
console.log("Test with backticks")
```"""
    ctx = make_ctx(f".run {code}", None)

    await cmd_run(ctx, code=code)

    assert isinstance(ctx.send, (MagicMock, AsyncMock))
    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert "Test with backticks" in call_args


@pytest.mark.asyncio
async def test_run_command_no_output(make_ctx: MakeCtx):
    """Test .run command with code that produces no output."""
    code = "let x = 5;"
    ctx = make_ctx(f".run {code}", None)

    # Test code that doesn't produce output
    await cmd_run(ctx, code=code)

    assert isinstance(ctx.send, (MagicMock, AsyncMock))
    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert "No output" in call_args


@pytest.mark.asyncio
async def test_run_command_syntax_error(make_ctx: MakeCtx):
    """Test .run command with syntax error."""
    code = "console.log('missing quote)"
    ctx = make_ctx(f".run {code}", None)

    # Test invalid JavaScript syntax
    await cmd_run(ctx, code=code)

    assert isinstance(ctx.send, (MagicMock, AsyncMock))
    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert "❌" in call_args or "⚠️" in call_args  # Error indicator should be present


@pytest.mark.asyncio
async def test_run_command_dm_context(make_ctx: MakeCtx):
    """Test .run command in DM (no guild)."""
    code = "console.log('DM test')"
    ctx = make_ctx(f".run {code}", None)
    ctx.guild = None  # Simulate DM context

    await cmd_run(ctx, code=code)

    assert isinstance(ctx.send, (MagicMock, AsyncMock))
    ctx.send.assert_called_once()
    call_args = ctx.send.call_args[0][0]
    assert "DM test" in call_args
