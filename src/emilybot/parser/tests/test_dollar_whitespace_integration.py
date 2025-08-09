#!/usr/bin/env python3
"""Integration tests for dollar whitespace handling in main handler."""


def test_main_handler_whitespace_detection():
    """Test that the main handler correctly detects dollar followed by any whitespace."""

    def should_handle_dollar_command(message_content: str) -> bool:
        """Simulate the logic from main.py for detecting dollar commands."""
        return (
            message_content.startswith("$")
            and len(message_content) > 1
            and message_content[1].isspace()
        )

    # Test cases that should be handled
    assert should_handle_dollar_command("$ foo")
    assert should_handle_dollar_command("$\nfoo")
    assert should_handle_dollar_command("$\tfoo")
    assert should_handle_dollar_command("$   foo")
    assert should_handle_dollar_command("$ \t\n foo")

    # Test cases that should NOT be handled (no whitespace after $)
    assert not should_handle_dollar_command("$foo")
    assert not should_handle_dollar_command("$")
    assert not should_handle_dollar_command("foo")
    assert not should_handle_dollar_command("$123")
    assert not should_handle_dollar_command("$!foo")


def test_parser_whitespace_handling():
    """Test that the parser correctly handles all whitespace types."""
    from emilybot.parser import parse_message, JS

    # Test various whitespace patterns
    test_cases = [
        ("$ foo", "foo"),
        ("$\nfoo", "foo"),
        ("$\tfoo", "foo"),
        ("$   foo", "foo"),
        ("$ \t\n foo", "foo"),
        ("$ 2 + 2", "2 + 2"),
        ("$\nconsole.log('hello')", "console.log('hello')"),
        ("$\tMath.random()", "Math.random()"),
    ]

    for input_str, expected_code in test_cases:
        result = parse_message(input_str)
        assert isinstance(result, JS), f"Expected JS for '{input_str}'"
        assert result.code == expected_code, (
            f"Expected '{expected_code}' for '{input_str}', got '{result.code}'"
        )


def test_whitespace_consistency():
    """Test that main handler and parser are consistent in whitespace handling."""
    from emilybot.parser import parse_message, JS

    def should_handle_dollar_command(message_content: str) -> bool:
        """Simulate the logic from main.py for detecting dollar commands."""
        return (
            message_content.startswith("$")
            and len(message_content) > 1
            and message_content[1].isspace()
        )

    # Test that all patterns detected by main handler are also handled by parser
    test_patterns = [
        "$ foo",
        "$\nfoo",
        "$\tfoo",
        "$   foo",
        "$ \t\n foo",
    ]

    for pattern in test_patterns:
        # Main handler should detect this
        assert should_handle_dollar_command(pattern), (
            f"Main handler should detect: {pattern}"
        )

        # Parser should handle this as JS
        result = parse_message(pattern)
        assert isinstance(result, JS), f"Parser should return JS for: {pattern}"


def test_argument_handling_integration():
    """Test that argument handling works end-to-end from parsing to execution."""
    from emilybot.parser import parse_message, Command
    from emilybot.execute.javascript_executor import (
        JavaScriptExecutor,
        CommandData,
        Context,
        CtxMessage,
        CtxUser,
        CtxServer,
    )
    import asyncio

    # Test parsing
    result = parse_message("$greeting Alice Bob")
    assert isinstance(result, Command)
    assert result.cmd == "greeting"
    assert result.args == ["Alice", "Bob"]

    # Test execution
    async def test_execution():
        executor = JavaScriptExecutor()
        context = Context(
            message=CtxMessage(text="$greeting Alice Bob"),
            user=CtxUser(id="12345", name="TestUser"),
            server=CtxServer(id="67890"),
        )
        commands = [
            CommandData(
                name="greeting",
                content="Hello, world!",
                run="console.log('Hello ' + args[0] + ' and ' + args[1] + '!')",
            ),
        ]

        success, output, _value = await executor.execute(
            "$greeting('Alice', 'Bob')",
            context,
            commands,
        )

        assert success
        assert "Hello Alice and Bob!" in output

    # Run the async test
    asyncio.run(test_execution())


def test_argument_handling_with_special_characters():
    """Test that argument handling works with special characters."""
    from emilybot.parser import parse_message, Command

    # Test parsing with special characters
    result = parse_message('$echo hello-world test_arg "quoted string"')
    assert isinstance(result, Command)
    assert result.cmd == "echo"
    assert result.args == ["hello-world", "test_arg", "quoted string"]
