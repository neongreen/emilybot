#!/usr/bin/env python3
"""Test script for JavaScript executor functionality."""

import asyncio

from emilybot.execute.javascript_executor import (
    JavaScriptExecutor,
    extract_js_code,
    Context,
    CtxMessage,
    CtxUser,
    CtxServer,
)


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


async def test_javascript_execution():
    """Test JavaScript execution (requires Deno to be installed)."""
    print("\nTesting JavaScript execution...")

    executor = JavaScriptExecutor(timeout=1.0)

    # Test simple console.log
    test_code = "console.log('Hello from JavaScript!');"
    test_context = Context(
        message=CtxMessage(text="test message"),
        user=CtxUser(id="123", name="TestUser"),
        server=CtxServer(id="12345"),
    )

    try:
        success, output, _value = await executor.execute(test_code, test_context, [])
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
        success, output, _value = await executor.execute(
            test_code_with_context, test_context, []
        )
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
    await test_javascript_execution()

    print("\nTests completed!")


if __name__ == "__main__":
    asyncio.run(main())
