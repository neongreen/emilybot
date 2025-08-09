#!/usr/bin/env python3
"""Unit tests for command parser functionality."""

import pytest
from emilybot.parser import parse_command, Command, JS, ListChildren


class TestParser:
    """Test cases for command parser functionality."""

    def test_command_with_args(self):
        """Test that command with arguments is parsed correctly."""
        result = parse_command("$foo a b c")
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == ["a", "b", "c"]

    def test_command_without_args(self):
        """Test that command without arguments is parsed correctly."""
        result = parse_command("$bar")
        assert isinstance(result, Command)
        assert result.cmd == "bar"
        assert result.args == []

    def test_command_with_single_arg(self):
        """Test that command with single argument is parsed correctly."""
        result = parse_command("$test hello")
        assert isinstance(result, Command)
        assert result.cmd == "test"
        assert result.args == ["hello"]

    def test_command_with_underscores(self):
        """Test that command with underscores is parsed correctly."""
        result = parse_command("$user_settings dark")
        assert isinstance(result, Command)
        assert result.cmd == "user_settings"
        assert result.args == ["dark"]

    def test_command_with_slashes(self):
        """Test that command with slashes is parsed correctly."""
        result = parse_command("$docs/api reference")
        assert isinstance(result, Command)
        assert result.cmd == "docs/api"
        assert result.args == ["reference"]

    def test_command_with_numbers(self):
        """Test that command with numbers is parsed correctly."""
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
        """Test that JavaScript with dot notation is treated as command."""
        result = parse_command("$object.property")
        assert isinstance(result, Command)
        assert result.cmd == "object/property"
        assert result.args == []

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
        """Test that command with multiple spaces is parsed correctly."""
        result = parse_command("$foo  a   b    c")
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == ["a", "b", "c"]

    def test_command_with_tabs(self):
        """Test that command with tabs is parsed correctly."""
        result = parse_command("$foo\ta\tb\tc")
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == ["a", "b", "c"]

    def test_command_with_mixed_whitespace(self):
        """Test that command with mixed whitespace is parsed correctly."""
        result = parse_command("$foo a\tb  c")
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == ["a", "b", "c"]

    def test_invalid_no_dollar_prefix(self):
        """Test that message without $ prefix raises error."""
        import pytest

        with pytest.raises(ValueError, match="Message content must start with"):
            parse_command("foo a b c")

    def test_invalid_empty_after_dollar(self):
        """Test that message with just $ raises error."""
        import pytest

        with pytest.raises(ValueError, match="No content found after"):
            parse_command("$")

    def test_invalid_whitespace_after_dollar(self):
        """Test that message with $ and whitespace raises error."""
        import pytest

        with pytest.raises(ValueError, match="No content found after"):
            parse_command("$   ")

    def test_command_with_empty_args(self):
        """Test that command with empty args is parsed correctly."""
        result = parse_command("$foo a  b   c")
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == ["a", "b", "c"]

    def test_dollar_space_javascript(self):
        """Test that $ followed by space and JavaScript is treated as JS."""
        result = parse_command("$ console.log('hello')")
        assert isinstance(result, JS)
        assert result.code == "console.log('hello')"

    def test_dollar_space_arithmetic(self):
        """Test that $ followed by space and arithmetic is treated as JS."""
        result = parse_command("$ 2 + 2")
        assert isinstance(result, JS)
        assert result.code == "2 + 2"

    def test_dollar_newline_javascript(self):
        """Test that $ followed by newline and JavaScript is treated as JS."""
        result = parse_command("$\nconsole.log('hello')")
        assert isinstance(result, JS)
        assert result.code == "console.log('hello')"

    def test_dollar_tab_javascript(self):
        """Test that $ followed by tab and JavaScript is treated as JS."""
        result = parse_command("$\tconsole.log('hello')")
        assert isinstance(result, JS)
        assert result.code == "console.log('hello')"

    def test_dollar_multiple_spaces_javascript(self):
        """Test that $ followed by multiple spaces and JavaScript is treated as JS."""
        result = parse_command("$   console.log('hello')")
        assert isinstance(result, JS)
        assert result.code == "console.log('hello')"

    def test_dollar_mixed_whitespace_javascript(self):
        """Test that $ followed by mixed whitespace and JavaScript is treated as JS."""
        result = parse_command("$ \t\n console.log('hello')")
        assert isinstance(result, JS)
        assert result.code == "console.log('hello')"

    def test_dollar_newline_arithmetic(self):
        """Test that $ followed by newline and arithmetic is treated as JS."""
        result = parse_command("$\n2 + 2")
        assert isinstance(result, JS)
        assert result.code == "2 + 2"

    def test_dollar_tab_arithmetic(self):
        """Test that $ followed by tab and arithmetic is treated as JS."""
        result = parse_command("$\t2 + 2")
        assert isinstance(result, JS)
        assert result.code == "2 + 2"

    # New tests for dot notation functionality
    def test_dot_command_simple(self):
        """Test that $foo.bar is treated as command foo/bar."""
        result = parse_command("$foo.bar")
        assert isinstance(result, Command)
        assert result.cmd == "foo/bar"
        assert result.args == []

    def test_dot_command_with_args(self):
        """Test that $foo.bar a b c is treated as command foo/bar with args."""
        result = parse_command("$foo.bar a b c")
        assert isinstance(result, Command)
        assert result.cmd == "foo/bar"
        assert result.args == ["a", "b", "c"]

    def test_dot_command_with_underscores(self):
        """Test that $foo.bar_baz is treated as command foo/bar_baz."""
        result = parse_command("$foo.bar_baz")
        assert isinstance(result, Command)
        assert result.cmd == "foo/bar_baz"
        assert result.args == []

    def test_dot_command_with_hyphens(self):
        """Test that $foo.bar-baz is treated as command foo/bar-baz."""
        result = parse_command("$foo.bar-baz")
        assert isinstance(result, Command)
        assert result.cmd == "foo/bar-baz"
        assert result.args == []

    def test_dot_command_with_slashes(self):
        """Test that $foo.bar/baz is treated as command foo/bar/baz."""
        result = parse_command("$foo.bar/baz")
        assert isinstance(result, Command)
        assert result.cmd == "foo/bar/baz"
        assert result.args == []

    def test_dot_command_with_numbers(self):
        """Test that $foo.bar123 is treated as command foo/bar123."""
        result = parse_command("$foo.bar123")
        assert isinstance(result, Command)
        assert result.cmd == "foo/bar123"
        assert result.args == []

    def test_underscore_start_child_is_js(self):
        """Test that $foo._bar is treated as JavaScript (child starts with _)."""
        result = parse_command("$foo._bar")
        assert isinstance(result, JS)
        assert result.code == "$foo._bar"

    def test_list_children_single_dot(self):
        """Test that $foo. is treated as listing children of foo."""
        result = parse_command("$foo.")
        assert isinstance(result, ListChildren)
        assert result.parent == "foo"

    def test_list_children_double_dot(self):
        """Test that $foo.. is treated as listing children of foo."""
        result = parse_command("$foo..")
        assert isinstance(result, ListChildren)
        assert result.parent == "foo"

    def test_list_children_triple_dot(self):
        """Test that $foo... is treated as listing children of foo."""
        result = parse_command("$foo...")
        assert isinstance(result, ListChildren)
        assert result.parent == "foo"

    def test_list_children_slash(self):
        """Test that $foo/ is treated as listing children of foo."""
        result = parse_command("$foo/")
        assert isinstance(result, ListChildren)
        assert result.parent == "foo"

    def test_list_children_with_underscores(self):
        """Test that $foo_bar. is treated as listing children of foo_bar."""
        result = parse_command("$foo_bar.")
        assert isinstance(result, ListChildren)
        assert result.parent == "foo_bar"

    def test_list_children_with_hyphens(self):
        """Test that $foo-bar. is treated as listing children of foo-bar."""
        result = parse_command("$foo-bar.")
        assert isinstance(result, ListChildren)
        assert result.parent == "foo-bar"

    def test_list_children_with_slashes(self):
        """Test that $foo/bar. is treated as listing children of foo/bar."""
        result = parse_command("$foo/bar.")
        assert isinstance(result, ListChildren)
        assert result.parent == "foo/bar"

    def test_common_js_patterns_as_commands(self):
        """Test that common JavaScript patterns are now treated as commands."""
        # These should now be treated as commands with dot notation applied
        command_patterns = [
            ("$console.log", "console/log"),
            ("$document.getElementById", "document/getElementById"),
            ("$window.location", "window/location"),
            ("$Math.random", "Math/random"),
            ("$Array.from", "Array/from"),
            ("$Promise.resolve", "Promise/resolve"),
            ("$fetch", "fetch"),
            ("$JSON.stringify", "JSON/stringify"),
        ]

        for pattern, expected_cmd in command_patterns:
            result = parse_command(pattern)
            assert isinstance(result, Command), f"Expected Command for: {pattern}"
            assert result.cmd == expected_cmd
