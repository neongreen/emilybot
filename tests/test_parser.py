#!/usr/bin/env python3
"""Unit tests for command parser functionality."""

import pytest
from emilybot.parser import parse_command, Command, JS


class TestParser:
    """Test cases for command parser functionality."""

    def test_command_with_args(self):
        """Test parsing a command with arguments."""
        result = parse_command("$foo a b c")
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == ["a", "b", "c"]

    def test_command_without_args(self):
        """Test parsing a command without arguments."""
        result = parse_command("$bar")
        assert isinstance(result, Command)
        assert result.cmd == "bar"
        assert result.args == []

    def test_command_with_single_arg(self):
        """Test parsing a command with a single argument."""
        result = parse_command("$test hello")
        assert isinstance(result, Command)
        assert result.cmd == "test"
        assert result.args == ["hello"]

    def test_command_with_underscores(self):
        """Test parsing a command with underscores in the name."""
        result = parse_command("$user_settings dark")
        assert isinstance(result, Command)
        assert result.cmd == "user_settings"
        assert result.args == ["dark"]

    def test_command_with_slashes(self):
        """Test parsing a command with forward slashes in the name."""
        result = parse_command("$docs/api reference")
        assert isinstance(result, Command)
        assert result.cmd == "docs/api"
        assert result.args == ["reference"]

    def test_command_with_numbers(self):
        """Test parsing a command with numbers in the name."""
        result = parse_command("$api_v1 users")
        assert isinstance(result, Command)
        assert result.cmd == "api_v1"
        assert result.args == ["users"]

    def test_javascript_with_semicolon(self):
        """Test that JavaScript with semicolon is treated as JS."""
        result = parse_command("$console.log('hello');")
        assert isinstance(result, JS)
        assert result.code == "$console.log('hello');"

    def test_javascript_with_parentheses(self):
        """Test that JavaScript with parentheses is treated as JS."""
        result = parse_command("$foo()")
        assert isinstance(result, JS)
        assert result.code == "$foo()"

    def test_javascript_with_brackets(self):
        """Test that JavaScript with brackets is treated as JS."""
        result = parse_command("$array[0]")
        assert isinstance(result, JS)
        assert result.code == "$array[0]"

    def test_javascript_with_braces(self):
        """Test that JavaScript with braces is treated as JS."""
        result = parse_command("${foo: 'bar'}")
        assert isinstance(result, JS)
        assert result.code == "${foo: 'bar'}"

    def test_javascript_with_comma(self):
        """Test that JavaScript with comma is treated as JS."""
        result = parse_command("$foo, bar")
        assert isinstance(result, JS)
        assert result.code == "$foo, bar"

    def test_javascript_with_operators(self):
        """Test that JavaScript with operators is treated as JS."""
        result = parse_command("$x + y")
        assert isinstance(result, JS)
        assert result.code == "$x + y"

    def test_javascript_with_quotes(self):
        """Test that JavaScript with quotes is treated as JS."""
        result = parse_command("$'hello'")
        assert isinstance(result, JS)
        assert result.code == "$'hello'"

    def test_javascript_with_backticks(self):
        """Test that JavaScript with backticks is treated as JS."""
        result = parse_command("$`hello`")
        assert isinstance(result, JS)
        assert result.code == "$`hello`"

    def test_javascript_with_dot_notation(self):
        """Test that JavaScript with dot notation is treated as JS."""
        result = parse_command("$object.property")
        assert isinstance(result, JS)
        assert result.code == "$object.property"

    def test_javascript_with_function_call(self):
        """Test that JavaScript function calls are treated as JS."""
        result = parse_command("$getUser(123)")
        assert isinstance(result, JS)
        assert result.code == "$getUser(123)"

    def test_javascript_with_assignment(self):
        """Test that JavaScript assignments are treated as JS."""
        result = parse_command("$let x = 5")
        assert isinstance(result, Command)
        assert result.cmd == "let"
        assert result.args == ["x", "=", "5"]

    def test_javascript_with_arrow_function(self):
        """Test that JavaScript arrow functions are treated as JS."""
        result = parse_command("$() => {}")
        assert isinstance(result, JS)
        assert result.code == "$() => {}"

    def test_javascript_with_template_literal(self):
        """Test that JavaScript template literals are treated as JS."""
        result = parse_command("$`Hello ${name}`")
        assert isinstance(result, JS)
        assert result.code == "$`Hello ${name}`"

    def test_javascript_with_regex(self):
        """Test that JavaScript with regex is treated as JS."""
        result = parse_command("$/pattern/")
        assert isinstance(result, JS)
        assert result.code == "$/pattern/"

    def test_javascript_with_comment(self):
        """Test that JavaScript with comment is treated as JS."""
        result = parse_command("$// comment")
        assert isinstance(result, JS)
        assert result.code == "$// comment"

    def test_javascript_with_multiline(self):
        """Test that JavaScript with newlines is treated as JS."""
        result = parse_command("$console.log('hello');\nconsole.log('world');")
        assert isinstance(result, JS)
        assert result.code == "$console.log('hello');\nconsole.log('world');"

    def test_command_with_multiple_spaces(self):
        """Test parsing a command with multiple spaces between args."""
        result = parse_command("$foo  a   b    c")
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == ["a", "b", "c"]

    def test_command_with_tabs(self):
        """Test parsing a command with tabs between args."""
        result = parse_command("$foo\ta\tb\tc")
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == ["a", "b", "c"]

    def test_command_with_mixed_whitespace(self):
        """Test parsing a command with mixed whitespace between args."""
        result = parse_command("$foo a\tb  c")
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == ["a", "b", "c"]

    def test_invalid_no_dollar_prefix(self):
        """Test that messages without $ prefix raise ValueError."""
        with pytest.raises(ValueError, match="Message content must start with"):
            parse_command("foo a b c")

    def test_invalid_empty_after_dollar(self):
        """Test that messages with only $ raise ValueError."""
        with pytest.raises(ValueError, match="No content found after"):
            parse_command("$")

    def test_invalid_whitespace_after_dollar(self):
        """Test that messages with only whitespace after $ are treated as JavaScript."""
        result = parse_command("$   ")
        assert isinstance(result, JS)
        assert result.code == ""

    def test_command_with_empty_args(self):
        """Test parsing a command with empty arguments (should be filtered out)."""
        result = parse_command("$foo a  b   c")
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == ["a", "b", "c"]

    def test_dollar_space_javascript(self):
        """Test that messages starting with '$ ' are treated as JavaScript with $ stripped."""
        result = parse_command("$ console.log('hello')")
        assert isinstance(result, JS)
        assert result.code == "console.log('hello')"

        result = parse_command("$ let x = 5")
        assert isinstance(result, JS)
        assert result.code == "let x = 5"

        result = parse_command("$ foo bar baz")
        assert isinstance(result, JS)
        assert result.code == "foo bar baz"
