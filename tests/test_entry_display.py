#!/usr/bin/env python3
"""Test script for entry display with JavaScript execution."""

import uuid
import pytest

from emilybot.commands.show import format_entry_content
from emilybot.database import Entry


@pytest.mark.asyncio
async def test_entry_without_javascript():
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

    result = await format_entry_content(entry)
    expected = "This is a simple entry without JavaScript"

    assert result == expected


@pytest.mark.asyncio
async def test_entry_with_javascript():
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
        run="console.log('Hello from ' + context.name + '!');",
    )

    result = await format_entry_content(entry)

    assert "Hello from test-entry!" in result


@pytest.mark.asyncio
async def test_entry_with_javascript_error():
    """Test entry display with JavaScript error."""
    print("\nTesting entry display with JavaScript error...")

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

    result = await format_entry_content(entry)
    assert "This is an entry with broken JavaScript" in result
    assert "'undefinedVariable' is not defined" in result


@pytest.mark.asyncio
async def test_entry_with_empty_javascript():
    """Test entry display with empty JavaScript code."""
    print("\nTesting entry display with empty JavaScript...")

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

    result = await format_entry_content(entry)
    expected = "This is an entry with empty JavaScript"

    assert result == expected


@pytest.mark.asyncio
async def test_entry_with_no_output_javascript():
    """Test entry display with JavaScript that produces no output."""
    print("\nTesting entry display with JavaScript that produces no output...")

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

    result = await format_entry_content(entry)

    assert result == ""
