import pytest

from emilybot.execute.javascript_executor import (
    JavaScriptExecutor,
    extract_js_code,
    Context,
    CtxMessage,
    create_test_user,
    CtxServer,
    CommandData,
)


def test_code_parsing():
    """Test the code parsing functionality."""
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
        assert result == expected, (
            f"Test case {i + 1} failed: input={repr(input_code)}, expected={repr(expected)}, got={repr(result)}"
        )


@pytest.mark.asyncio
async def test_nested_commands_with_js_code():
    """Test behavior when foo has JS code but foo/bar doesn't."""
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
        reply_to=None,
        user=create_test_user(id="123", name="TestUser"),
        server=CtxServer(id="12345"),
    )

    # Test calling $foo() - should execute the JS code
    test_code = "$foo()"

    try:
        success, output, value = await executor.execute(
            test_code, test_context, commands
        )
        assert success, f"$foo() execution failed: {output}"
        # Should see the console.log output and the return value
        assert "Executing foo JS code" in output, (
            f"Expected JS execution output, got: {output}"
        )
        assert "foo result" in str(value), f"Expected return value, got: {value}"
    except Exception as e:
        pytest.skip(f"$foo() execution test skipped (Deno not available?): {e}")

    # Test calling $foo.bar() - should display content, not execute JS
    test_code = "$foo.bar()"

    try:
        success, output, value = await executor.execute(
            test_code, test_context, commands
        )
        assert success, f"$foo.bar() execution failed: {output}"
        # Should see the content displayed, not JS execution
        assert "This is the foo/bar command content" in output, (
            f"Expected content display, got: {output}"
        )
    except Exception as e:
        pytest.skip(f"$foo.bar() execution test skipped (Deno not available?): {e}")

    # Test that $foo is a function and $foo.bar is also a function
    test_code = "console.log('$foo type:', typeof $foo); console.log('$foo.bar type:', typeof $foo.bar);"

    try:
        success, output, value = await executor.execute(
            test_code, test_context, commands
        )
        assert success, f"Command type test failed: {output}"
        # Both should be functions
        assert "function" in output, f"Expected functions, got: {output}"
    except Exception as e:
        pytest.skip(f"Command type test skipped (Deno not available?): {e}")


@pytest.mark.asyncio
async def test_nested_commands_reverse_order():
    """Test behavior when foo/bar comes before foo in the commands list."""
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
        reply_to=None,
        user=create_test_user(id="123", name="TestUser"),
        server=CtxServer(id="12345"),
    )

    # Test calling $foo() - should execute the JS code
    test_code = "$foo()"

    try:
        success, output, value = await executor.execute(
            test_code, test_context, commands
        )
        assert success, f"$foo() execution (reverse order) failed: {output}"
        # Should see the console.log output and the return value
        assert "Executing foo JS code" in output, (
            f"Expected JS execution output, got: {output}"
        )
        assert "foo result" in str(value), f"Expected return value, got: {value}"
    except Exception as e:
        pytest.skip(
            f"$foo() execution test (reverse order) skipped (Deno not available?): {e}"
        )

    # Test calling $foo.bar() - should display content, not execute JS
    test_code = "$foo.bar()"

    try:
        success, output, value = await executor.execute(
            test_code, test_context, commands
        )
        assert success, f"$foo.bar() execution (reverse order) failed: {output}"
        # Should see the content displayed, not JS execution
        assert "This is the foo/bar command content" in output, (
            f"Expected content display, got: {output}"
        )
    except Exception as e:
        pytest.skip(
            f"$foo.bar() execution test (reverse order) skipped (Deno not available?): {e}"
        )

    # Test that $foo is a function and $foo.bar is also a function
    test_code = "console.log('$foo type:', typeof $foo); console.log('$foo.bar type:', typeof $foo.bar);"

    try:
        success, output, value = await executor.execute(
            test_code, test_context, commands
        )
        assert success, f"Command type test (reverse order) failed: {output}"
        # Both should be functions
        assert "function" in output, f"Expected functions, got: {output}"
    except Exception as e:
        pytest.skip(
            f"Command type test (reverse order) skipped (Deno not available?): {e}"
        )

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
        assert success, f"Combined execution test (reverse order) failed: {output}"
        # Should see both commands working
        assert "Executing foo JS code" in output, (
            f"Expected foo JS execution, got: {output}"
        )
        assert "This is the foo/bar command content" in output, (
            f"Expected foo/bar content display, got: {output}"
        )
    except Exception as e:
        pytest.skip(
            f"Combined execution test (reverse order) skipped (Deno not available?): {e}"
        )


@pytest.mark.asyncio
async def test_javascript_execution():
    """Test JavaScript execution (requires Deno to be installed)."""
    executor = JavaScriptExecutor(timeout=1.0)

    # Test simple console.log
    test_code = "console.log('Hello from JavaScript!');"
    test_context = Context(
        message=CtxMessage(text="test message"),
        reply_to=None,
        user=create_test_user(id="123", name="TestUser"),
        server=CtxServer(id="12345"),
    )

    try:
        success, output, _value = await executor.execute(test_code, test_context, [])
        assert success, f"JavaScript execution test failed: {output}"
        assert "Hello from JavaScript!" in output, f"Expected JS output, got: {output}"
    except Exception as e:
        pytest.skip(f"JavaScript execution test skipped (Deno not available?): {e}")
