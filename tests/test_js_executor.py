#!/usr/bin/env python3
"""Test script for JavaScript executor functionality."""

import asyncio

from emilybot.javascript_executor import (
    JavaScriptExecutor,
    extract_js_code,
    create_context_from_entry,
)
from emilybot.database import Entry
import uuid


async def test_code_parsing():
    """Test the code parsing functionality."""
    print("Testing code parsing...")

    # Test cases for code parsing
    test_cases = [
        # Plain code without backticks
        ("console.log('hello');", "console.log('hello');"),
        # Code with plain triple backticks
        ("```\nconsole.log('hello');\n```", "console.log('hello');"),
        # Code with js language identifier
        ("```js\nconsole.log('hello');\n```", "console.log('hello');"),
        # Code with javascript language identifier
        ("```javascript\nconsole.log('hello');\n```", "console.log('hello');"),
        # Code with empty language identifier
        ("```\nconsole.log('hello');\n```", "console.log('hello');"),
        # Multi-line code
        (
            "```js\nconsole.log('line 1');\nconsole.log('line 2');\n```",
            "console.log('line 1');\nconsole.log('line 2');",
        ),
        # Code with extra whitespace
        ("  ```js  \n  console.log('hello');  \n  ```  ", "console.log('hello');"),
    ]

    for i, (input_code, expected) in enumerate(test_cases):
        result = extract_js_code(input_code)
        if result == expected:
            print(f"✅ Test case {i + 1} passed")
        else:
            print(f"❌ Test case {i + 1} failed:")
            print(f"   Input: {repr(input_code)}")
            print(f"   Expected: {repr(expected)}")
            print(f"   Got: {repr(result)}")


async def test_context_creation():
    """Test context creation from Entry."""
    print("\nTesting context creation...")

    # Create a test entry
    entry = Entry(
        id=uuid.uuid4(),
        server_id=12345,
        user_id=67890,
        created_at="2025-01-29T12:00:00Z",
        name="test-entry",
        content="This is test content",
        promoted=False,
        run=None,
    )

    context = create_context_from_entry(entry)

    expected_context = {
        "content": "This is test content",
        "name": "test-entry",
        "created_at": "2025-01-29T12:00:00Z",
        "user_id": 67890,
    }

    if context == expected_context:
        print("✅ Context creation test passed")
    else:
        print("❌ Context creation test failed:")
        print(f"   Expected: {expected_context}")
        print(f"   Got: {context}")


async def test_javascript_execution():
    """Test JavaScript execution (requires Deno to be installed)."""
    print("\nTesting JavaScript execution...")

    executor = JavaScriptExecutor(timeout=1.0)

    # Test simple console.log
    test_code = "console.log('Hello from JavaScript!');"
    # Create a proper test entry for context
    test_entry = Entry(
        id=uuid.uuid4(),
        server_id=12345,
        user_id=123,
        created_at="2025-01-29T12:00:00Z",
        name="test",
        content="test content",
        promoted=False,
        run=None,
    )
    test_context = create_context_from_entry(test_entry)

    try:
        success, output = await executor.execute(test_code, test_context)
        if success:
            print(f"✅ JavaScript execution test passed: {repr(output)}")
        else:
            print(f"❌ JavaScript execution test failed: {output}")
    except Exception as e:
        print(f"⚠️ JavaScript execution test skipped (Deno not available?): {e}")

    # Test context access
    test_code_with_context = (
        "console.log('Entry name: ' + context.name + ', content: ' + context.content);"
    )

    try:
        success, output = await executor.execute(test_code_with_context, test_context)
        if success:
            print(f"✅ Context access test passed: {repr(output)}")
        else:
            print(f"❌ Context access test failed: {output}")
    except Exception as e:
        print(f"⚠️ Context access test skipped (Deno not available?): {e}")


async def main():
    """Run all tests."""
    print("Running JavaScript executor tests...\n")

    await test_code_parsing()
    await test_context_creation()
    await test_javascript_execution()

    print("\nTests completed!")


if __name__ == "__main__":
    asyncio.run(main())
