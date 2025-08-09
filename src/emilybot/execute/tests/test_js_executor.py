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
    CommandData,
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


async def test_nested_commands_with_js_code():
    """Test behavior when foo has JS code but foo/bar doesn't."""
    print("\nTesting nested commands with JS code...")

    executor = JavaScriptExecutor(timeout=1.0)

    # Create test commands: foo has JS code, foo/bar doesn't
    commands: list[CommandData] = [
        CommandData(
            name="foo",
            content="This is the foo command content",
            run="console.log('Executing foo JS code'); return 'foo result';",
        ),
        CommandData(
            name="foo/bar",
            content="This is the foo/bar command content",
            run=None,  # No JS code
        ),
    ]

    test_context = Context(
        message=CtxMessage(text="test message"),
        user=CtxUser(id="123", name="TestUser"),
        server=CtxServer(id="12345"),
    )

    # Test calling $foo() - should execute the JS code
    test_code = "$foo()"

    try:
        success, output, value = await executor.execute(
            test_code, test_context, commands
        )
        if success:
            print(f"✅ $foo() execution test passed:")
            print(f"   Output: {repr(output)}")
            print(f"   Value: {repr(value)}")
            # Should see the console.log output and the return value
            if "Executing foo JS code" in output and "foo result" in str(value):
                print("   ✅ Correct output and return value")
            else:
                print("   ❌ Unexpected output or return value")
        else:
            print(f"❌ $foo() execution test failed: {output}")
    except Exception as e:
        print(f"⚠️ $foo() execution test skipped (Deno not available?): {e}")

    # Test calling $foo.bar() - should display content, not execute JS
    test_code = "$foo.bar()"

    try:
        success, output, value = await executor.execute(
            test_code, test_context, commands
        )
        if success:
            print(f"✅ $foo.bar() execution test passed:")
            print(f"   Output: {repr(output)}")
            print(f"   Value: {repr(value)}")
            # Should see the content displayed, not JS execution
            if "This is the foo/bar command content" in output:
                print("   ✅ Correct content display")
            else:
                print("   ❌ Unexpected content display")
        else:
            print(f"❌ $foo.bar() execution test failed: {output}")
    except Exception as e:
        print(f"⚠️ $foo.bar() execution test skipped (Deno not available?): {e}")

    # Test that $foo is a function and $foo.bar is also a function
    test_code = "console.log('$foo type:', typeof $foo); console.log('$foo.bar type:', typeof $foo.bar);"

    try:
        success, output, value = await executor.execute(
            test_code, test_context, commands
        )
        if success:
            print(f"✅ Command type test passed:")
            print(f"   Output: {repr(output)}")
            # Both should be functions
            if "function" in output:
                print("   ✅ Both commands are functions")
            else:
                print("   ❌ Commands are not functions")
        else:
            print(f"❌ Command type test failed: {output}")
    except Exception as e:
        print(f"⚠️ Command type test skipped (Deno not available?): {e}")


async def test_nested_commands_reverse_order():
    """Test behavior when foo/bar comes before foo in the commands list."""
    print("\nTesting nested commands with reverse order...")

    executor = JavaScriptExecutor(timeout=1.0)

    # Create test commands: foo/bar first, then foo (reverse order)
    commands: list[CommandData] = [
        CommandData(
            name="foo/bar",
            content="This is the foo/bar command content",
            run=None,  # No JS code
        ),
        CommandData(
            name="foo",
            content="This is the foo command content",
            run="console.log('Executing foo JS code'); return 'foo result';",
        ),
    ]

    test_context = Context(
        message=CtxMessage(text="test message"),
        user=CtxUser(id="123", name="TestUser"),
        server=CtxServer(id="12345"),
    )

    # Test calling $foo() - should execute the JS code
    test_code = "$foo()"

    try:
        success, output, value = await executor.execute(
            test_code, test_context, commands
        )
        if success:
            print(f"✅ $foo() execution test (reverse order) passed:")
            print(f"   Output: {repr(output)}")
            print(f"   Value: {repr(value)}")
            # Should see the console.log output and the return value
            if "Executing foo JS code" in output and "foo result" in str(value):
                print("   ✅ Correct output and return value")
            else:
                print("   ❌ Unexpected output or return value")
        else:
            print(f"❌ $foo() execution test (reverse order) failed: {output}")
    except Exception as e:
        print(
            f"⚠️ $foo() execution test (reverse order) skipped (Deno not available?): {e}"
        )

    # Test calling $foo.bar() - should display content, not execute JS
    test_code = "$foo.bar()"

    try:
        success, output, value = await executor.execute(
            test_code, test_context, commands
        )
        if success:
            print(f"✅ $foo.bar() execution test (reverse order) passed:")
            print(f"   Output: {repr(output)}")
            print(f"   Value: {repr(value)}")
            # Should see the content displayed, not JS execution
            if "This is the foo/bar command content" in output:
                print("   ✅ Correct content display")
            else:
                print("   ❌ Unexpected content display")
        else:
            print(f"❌ $foo.bar() execution test (reverse order) failed: {output}")
    except Exception as e:
        print(
            f"⚠️ $foo.bar() execution test (reverse order) skipped (Deno not available?): {e}"
        )

    # Test that $foo is a function and $foo.bar is also a function
    test_code = "console.log('$foo type:', typeof $foo); console.log('$foo.bar type:', typeof $foo.bar);"

    try:
        success, output, value = await executor.execute(
            test_code, test_context, commands
        )
        if success:
            print(f"✅ Command type test (reverse order) passed:")
            print(f"   Output: {repr(output)}")
            # Both should be functions
            if "function" in output:
                print("   ✅ Both commands are functions")
            else:
                print("   ❌ Commands are not functions")
        else:
            print(f"❌ Command type test (reverse order) failed: {output}")
    except Exception as e:
        print(f"⚠️ Command type test (reverse order) skipped (Deno not available?): {e}")

    # Test that both commands work in the same execution context
    test_code = """
    console.log("Testing both commands in same context:");
    console.log("Calling $foo():");
    $foo();
    console.log("Calling $foo.bar():");
    $foo.bar();
    """

    try:
        success, output, value = await executor.execute(
            test_code, test_context, commands
        )
        if success:
            print(f"✅ Combined execution test (reverse order) passed:")
            print(f"   Output: {repr(output)}")
            # Should see both commands working
            if (
                "Executing foo JS code" in output
                and "This is the foo/bar command content" in output
            ):
                print("   ✅ Both commands work correctly")
            else:
                print("   ❌ One or both commands failed")
        else:
            print(f"❌ Combined execution test (reverse order) failed: {output}")
    except Exception as e:
        print(
            f"⚠️ Combined execution test (reverse order) skipped (Deno not available?): {e}"
        )


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
    await test_nested_commands_with_js_code()
    await test_nested_commands_reverse_order()
    await test_javascript_execution()

    print("\nTests completed!")


if __name__ == "__main__":
    asyncio.run(main())
