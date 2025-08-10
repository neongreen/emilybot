#!/usr/bin/env python3
"""Test script for entry display with JavaScript execution."""

import json
import uuid
import pytest

from emilybot.commands.run import run_code
from emilybot.database import Entry
from emilybot.conftest import MakeCtx


@pytest.mark.asyncio
async def test_entry_without_javascript(make_ctx: MakeCtx):
    """Test entry display without JavaScript code."""
    print("Testing entry display without JavaScript...")

    entry = Entry(
        id=uuid.uuid4(),
        server_id=12345,
        user_id=67890,
        created_at="2025-01-29T12:00:00Z",
        name="test-entry",
        content="This is a simple entry without JavaScript",
        promoted=False,
        run=None,
    )

    ctx = make_ctx("test message", entry)
    success, result, value = await run_code(
        ctx, code=f"$.cmd({json.dumps(entry.name)})"
    )
    expected = "This is a simple entry without JavaScript"

    assert success
    assert result == expected
    assert value is None


@pytest.mark.asyncio
async def test_entry_with_javascript(make_ctx: MakeCtx):
    """Test entry display with JavaScript code."""
    print("\nTesting entry display with JavaScript...")

    entry = Entry(
        id=uuid.uuid4(),
        server_id=12345,
        user_id=67890,
        created_at="2025-01-29T12:00:00Z",
        name="test-entry",
        content="This is an entry with JavaScript",
        promoted=False,
        run="console.log('Hello from ' + this.name + '!');",
    )

    ctx = make_ctx("test message", entry)
    success, result, value = await run_code(
        ctx, code=f"$.cmd({json.dumps(entry.name)})"
    )

    assert success
    assert "Hello from test-entry!" in result
    assert value is None


@pytest.mark.asyncio
async def test_entry_with_javascript_error(make_ctx: MakeCtx):
    """Test entry display with JavaScript error."""

    entry = Entry(
        id=uuid.uuid4(),
        server_id=12345,
        user_id=67890,
        created_at="2025-01-29T12:00:00Z",
        name="test-entry",
        content="This is an entry with broken JavaScript",
        promoted=False,
        run="console.log(undefinedVariable);",  # This will cause a runtime error
    )

    ctx = make_ctx("test message", entry)
    success, result, _value = await run_code(
        ctx, code=f"$.cmd({json.dumps(entry.name)})"
    )
    assert "'undefinedVariable' is not defined" in result
    assert not success


@pytest.mark.asyncio
async def test_entry_with_empty_javascript(make_ctx: MakeCtx):
    """Test entry display with empty JavaScript code."""

    entry = Entry(
        id=uuid.uuid4(),
        server_id=12345,
        user_id=67890,
        created_at="2025-01-29T12:00:00Z",
        name="test-entry",
        content="This is an entry with empty JavaScript",
        promoted=False,
        run="   ",  # Empty/whitespace-only JavaScript
    )

    ctx = make_ctx("test message", entry)
    success, output, value = await run_code(
        ctx, code=f"$.cmd({json.dumps(entry.name)})"
    )

    assert success
    assert output == "This is an entry with empty JavaScript"
    assert value is None


@pytest.mark.asyncio
async def test_entry_with_no_output_javascript(make_ctx: MakeCtx):
    """Test entry display with JavaScript that produces no output."""

    entry = Entry(
        id=uuid.uuid4(),
        server_id=12345,
        user_id=67890,
        created_at="2025-01-29T12:00:00Z",
        name="test-entry",
        content="This is an entry with silent JavaScript",
        promoted=False,
        run="let x = 1 + 1;",  # Valid JavaScript but no console.log
    )

    ctx = make_ctx("test message", entry)
    success, output, value = await run_code(
        ctx, code=f"$.cmd({json.dumps(entry.name)})"
    )

    assert success
    assert output == ""
    assert value is None
