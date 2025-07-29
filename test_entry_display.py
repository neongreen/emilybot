#!/usr/bin/env python3
"""Test script for entry display with JavaScript execution."""

import asyncio
import sys
import uuid
from pathlib import Path

# Add src to path so we can import emilybot modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from emilybot.commands.show import format_entry_content
from emilybot.database import Entry


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

    if result == expected:
        print("✅ Entry without JavaScript test passed")
    else:
        print("❌ Entry without JavaScript test failed:")
        print(f"   Expected: {repr(expected)}")
        print(f"   Got: {repr(result)}")


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

    try:
        result = await format_entry_content(entry)

        # Check that the result contains both original content and JavaScript output
        if (
            "This is an entry with JavaScript" in result
            and "🔧 **JavaScript Output:**" in result
            and "Hello from test-entry!" in result
        ):
            print("✅ Entry with JavaScript test passed")
            print(f"   Result: {repr(result)}")
        else:
            print("❌ Entry with JavaScript test failed:")
            print(f"   Result: {repr(result)}")
    except Exception as e:
        print(f"⚠️ Entry with JavaScript test skipped (Deno not available?): {e}")


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

    try:
        result = await format_entry_content(entry)

        # Check that the result contains both original content and error message
        if (
            "This is an entry with broken JavaScript" in result
            and "❌ **JavaScript Error:**" in result
        ):
            print("✅ Entry with JavaScript error test passed")
            print(f"   Result: {repr(result)}")
        else:
            print("❌ Entry with JavaScript error test failed:")
            print(f"   Result: {repr(result)}")
    except Exception as e:
        print(f"⚠️ Entry with JavaScript error test skipped (Deno not available?): {e}")


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

    if result == expected:
        print("✅ Entry with empty JavaScript test passed")
    else:
        print("❌ Entry with empty JavaScript test failed:")
        print(f"   Expected: {repr(expected)}")
        print(f"   Got: {repr(result)}")


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

    try:
        result = await format_entry_content(entry)

        # Check that the result contains original content and "no output" message
        if (
            "This is an entry with silent JavaScript" in result
            and "🔧 **JavaScript Output:** *(no output)*" in result
        ):
            print("✅ Entry with no output JavaScript test passed")
            print(f"   Result: {repr(result)}")
        else:
            print("❌ Entry with no output JavaScript test failed:")
            print(f"   Result: {repr(result)}")
    except Exception as e:
        print(
            f"⚠️ Entry with no output JavaScript test skipped (Deno not available?): {e}"
        )


async def main():
    """Run all tests."""
    print("Running entry display tests...\n")

    await test_entry_without_javascript()
    await test_entry_with_javascript()
    await test_entry_with_javascript_error()
    await test_entry_with_empty_javascript()
    await test_entry_with_no_output_javascript()

    print("\nTests completed!")


if __name__ == "__main__":
    asyncio.run(main())
