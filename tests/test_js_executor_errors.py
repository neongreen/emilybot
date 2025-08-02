#!/usr/bin/env python3
"""Test script for JavaScript executor error handling."""

import asyncio

from emilybot.execute.javascript_executor import (
    JavaScriptExecutor,
    Context,
    CtxMessage,
    CtxUser,
    CtxServer,
)


async def test_error_handling():
    """Test various error conditions."""
    print("Testing error handling...")

    executor = JavaScriptExecutor(timeout=1.0)

    # Create a test context directly
    test_context = Context(
        message=CtxMessage(text="test message"),
        user=CtxUser(id=123, name="TestUser"),
        server=CtxServer(id=12345),
    )

    # Test syntax error
    print("\n1. Testing syntax error...")
    syntax_error_code = "console.log('missing quote);"
    try:
        success, output, value = await executor.execute(
            syntax_error_code, test_context, []
        )
        print(
            f"   Result: success={success}, output={repr(output)}, value={repr(value)}"
        )
    except Exception as e:
        print(f"   Exception: {e}")

    # Test runtime error
    print("\n2. Testing runtime error...")
    runtime_error_code = "console.log(undefinedVariable);"
    try:
        success, output, value = await executor.execute(
            runtime_error_code, test_context, []
        )
        print(
            f"   Result: success={success}, output={repr(output)}, value={repr(value)}"
        )
    except Exception as e:
        print(f"   Exception: {e}")

    # Test timeout (this should be handled by Deno's internal timeout)
    print("\n3. Testing timeout...")
    timeout_code = "while(true) { /* infinite loop */ }"
    try:
        success, output, value = await executor.execute(timeout_code, test_context, [])
        print(
            f"   Result: success={success}, output={repr(output)}, value={repr(value)}"
        )
    except Exception as e:
        print(f"   Exception: {e}")

    # Test successful execution with multiple console.log calls
    print("\n4. Testing multiple console.log calls...")
    multi_log_code = """
    console.log('Line 1');
    console.log('Line 2');
    console.log('Context name: ' + context.name);
    """
    try:
        success, output, value = await executor.execute(
            multi_log_code, test_context, []
        )
        print(
            f"   Result: success={success}, output={repr(output)}, value={repr(value)}"
        )
    except Exception as e:
        print(f"   Exception: {e}")


async def main():
    """Run error handling tests."""
    print("Running JavaScript executor error handling tests...\n")

    await test_error_handling()

    print("\nError handling tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
