"""Unit tests for command parser functionality."""

from emilybot.parser import parse_message, Command, JS, ListChildren


class TestParser:
    """Test cases for command parser functionality."""

    def test_command_with_args(self):
        """Test that command with arguments is parsed correctly."""
        result = parse_message("$foo a b c")
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == ["a", "b", "c"]

    def test_command_without_args(self):
        """Test that command without arguments is parsed correctly."""
        result = parse_message("$bar")
        assert isinstance(result, Command)
        assert result.cmd == "bar"
        assert result.args == []

    def test_command_with_single_arg(self):
        """Test that command with single argument is parsed correctly."""
        result = parse_message("$test hello")
        assert isinstance(result, Command)
        assert result.cmd == "test"
        assert result.args == ["hello"]

    def test_command_with_underscores(self):
        """Test that command with underscores is parsed correctly."""
        result = parse_message("$user_settings dark")
        assert isinstance(result, Command)
        assert result.cmd == "user_settings"
        assert result.args == ["dark"]

    def test_command_with_slashes(self):
        """Test that command with slashes is parsed correctly."""
        result = parse_message("$docs/api reference")
        assert isinstance(result, Command)
        assert result.cmd == "docs/api"
        assert result.args == ["reference"]

    def test_command_with_numbers(self):
        """Test that command with numbers is parsed correctly."""
        result = parse_message("$api_v1 users")
        assert isinstance(result, Command)
        assert result.cmd == "api_v1"
        assert result.args == ["users"]

    def test_javascript_with_semicolon(self):
        """Test that JavaScript with semicolon is treated as JS."""
        result = parse_message("$console.log('hello');")
        assert isinstance(result, JS)
        assert result.code == "$console.log('hello');"

    def test_javascript_with_parentheses(self):
        """Test that JavaScript with parentheses is treated as JS."""
        result = parse_message("$foo()")
        assert isinstance(result, JS)
        assert result.code == "$foo()"

    def test_javascript_with_brackets(self):
        """Test that JavaScript with brackets is treated as JS."""
        result = parse_message("$array[0]")
        assert isinstance(result, JS)
        assert result.code == "$array[0]"

    def test_javascript_with_comma(self):
        """Test that JavaScript with comma is treated as JS."""
        result = parse_message("$foo, bar")
        assert isinstance(result, JS)
        assert result.code == "$foo, bar"

    def test_javascript_with_dot_notation(self):
        """Test that JavaScript with dot notation is treated as command."""
        result = parse_message("$object.property")
        assert isinstance(result, Command)
        assert result.cmd == "object/property"
        assert result.args == []

    def test_javascript_with_function_call(self):
        """Test that JavaScript function calls are treated as JS."""
        result = parse_message("$getUser(123)")
        assert isinstance(result, JS)
        assert result.code == "$getUser(123)"

    def test_javascript_with_assignment(self):
        """Test that JavaScript assignments are treated as JS."""
        result = parse_message("$let x = 5")
        assert isinstance(result, Command)
        assert result.cmd == "let"
        assert result.args == ["x", "=", "5"]

    def test_javascript_with_multiline(self):
        """Test that JavaScript with newlines is treated as JS."""
        result = parse_message("$console.log('hello');\nconsole.log('world');")
        assert isinstance(result, JS)
        assert result.code == "$console.log('hello');\nconsole.log('world');"

    def test_command_with_multiple_spaces(self):
        """Test that command with multiple spaces is parsed correctly."""
        result = parse_message("$foo  a   b    c")
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == ["a", "b", "c"]

    def test_command_with_tabs(self):
        """Test that command with tabs is parsed correctly."""
        result = parse_message("$foo\ta\tb\tc")
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == ["a", "b", "c"]

    def test_command_with_mixed_whitespace(self):
        """Test that command with mixed whitespace is parsed correctly."""
        result = parse_message("$foo a\tb  c")
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == ["a", "b", "c"]

    def test_command_with_quoted_arguments(self):
        """Test that command with quoted arguments is parsed correctly."""
        result = parse_message('$foo "hello world" "test arg"')
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == ["hello world", "test arg"]

    def test_command_with_special_characters_in_args(self):
        """Test that command with special characters in arguments is parsed correctly."""
        result = parse_message("$foo arg1 arg2-with-dashes arg3_with_underscores")
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == ["arg1", "arg2-with-dashes", "arg3_with_underscores"]

    def test_command_with_no_arguments(self):
        """Test that command with no arguments is parsed correctly."""
        result = parse_message("$foo")
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == []

    def test_command_with_empty_args(self):
        """Test that command with empty args is parsed correctly."""
        result = parse_message("$foo a  b   c")
        assert isinstance(result, Command)
        assert result.cmd == "foo"
        assert result.args == ["a", "b", "c"]

    def test_invalid_no_dollar_prefix(self):
        """Test that message without $ prefix returns None."""
        result = parse_message("foo a b c")
        assert result is None

    def test_invalid_empty_after_dollar(self):
        """Test that message with just $ returns None."""
        result = parse_message("$")
        assert result is None

    def test_invalid_whitespace_after_dollar(self):
        """Test that message with $ and whitespace returns None."""
        result = parse_message("$   ")
        assert result is None

    def test_dollar_space_javascript(self):
        """Test that $ followed by space and JavaScript is treated as JS."""
        result = parse_message("$ console.log('hello')")
        assert isinstance(result, JS)
        assert result.code == "console.log('hello')"

    def test_dollar_space_arithmetic(self):
        """Test that $ followed by space and arithmetic is treated as JS."""
        result = parse_message("$ 2 + 2")
        assert isinstance(result, JS)
        assert result.code == "2 + 2"

    def test_dollar_newline_javascript(self):
        """Test that $ followed by newline and JavaScript is treated as JS."""
        result = parse_message("$\nconsole.log('hello')")
        assert isinstance(result, JS)
        assert result.code == "console.log('hello')"

    def test_dollar_tab_javascript(self):
        """Test that $ followed by tab and JavaScript is treated as JS."""
        result = parse_message("$\tconsole.log('hello')")
        assert isinstance(result, JS)
        assert result.code == "console.log('hello')"

    def test_dollar_multiple_spaces_javascript(self):
        """Test that $ followed by multiple spaces and JavaScript is treated as JS."""
        result = parse_message("$   console.log('hello')")
        assert isinstance(result, JS)
        assert result.code == "console.log('hello')"

    def test_dollar_mixed_whitespace_javascript(self):
        """Test that $ followed by mixed whitespace and JavaScript is treated as JS."""
        result = parse_message("$ \t\n console.log('hello')")
        assert isinstance(result, JS)
        assert result.code == "console.log('hello')"

    def test_dollar_newline_arithmetic(self):
        """Test that $ followed by newline and arithmetic is treated as JS."""
        result = parse_message("$\n2 + 2")
        assert isinstance(result, JS)
        assert result.code == "2 + 2"

    def test_dollar_tab_arithmetic(self):
        """Test that $ followed by tab and arithmetic is treated as JS."""
        result = parse_message("$\t2 + 2")
        assert isinstance(result, JS)
        assert result.code == "2 + 2"

    # New tests for dot notation functionality
    def test_dot_command_simple(self):
        """Test that $foo.bar is treated as command foo/bar."""
        result = parse_message("$foo.bar")
        assert isinstance(result, Command)
        assert result.cmd == "foo/bar"
        assert result.args == []

    def test_dot_command_with_args(self):
        """Test that $foo.bar a b c is treated as command foo/bar with args."""
        result = parse_message("$foo.bar a b c")
        assert isinstance(result, Command)
        assert result.cmd == "foo/bar"
        assert result.args == ["a", "b", "c"]

    def test_dot_command_with_underscores(self):
        """Test that $foo.bar_baz is treated as command foo/bar_baz."""
        result = parse_message("$foo.bar_baz")
        assert isinstance(result, Command)
        assert result.cmd == "foo/bar_baz"
        assert result.args == []

    def test_dot_command_with_hyphens(self):
        """Test that $foo.bar-baz is treated as command foo/bar-baz."""
        result = parse_message("$foo.bar-baz")
        assert isinstance(result, Command)
        assert result.cmd == "foo/bar-baz"
        assert result.args == []

    def test_dot_command_with_slashes(self):
        """Test that $foo.bar/baz is treated as command foo/bar/baz."""
        result = parse_message("$foo.bar/baz")
        assert isinstance(result, Command)
        assert result.cmd == "foo/bar/baz"
        assert result.args == []

    def test_dot_command_with_numbers(self):
        """Test that $foo.bar123 is treated as command foo/bar123."""
        result = parse_message("$foo.bar123")
        assert isinstance(result, Command)
        assert result.cmd == "foo/bar123"
        assert result.args == []

    def test_underscore_start_child_is_js(self):
        """Test that $foo._bar is treated as JavaScript (child starts with _)."""
        result = parse_message("$foo._bar")
        assert isinstance(result, JS)
        assert result.code == "$foo._bar"

    def test_list_children_single_dot(self):
        """Test that $foo. is treated as listing children of foo."""
        result = parse_message("$foo.")
        assert isinstance(result, ListChildren)
        assert result.parent == "foo"

    def test_list_children_double_dot(self):
        """Test that $foo.. is treated as listing children of foo."""
        result = parse_message("$foo..")
        assert isinstance(result, ListChildren)
        assert result.parent == "foo"

    def test_list_children_triple_dot(self):
        """Test that $foo... is treated as listing children of foo."""
        result = parse_message("$foo...")
        assert isinstance(result, ListChildren)
        assert result.parent == "foo"

    def test_list_children_slash(self):
        """Test that $foo/ is treated as listing children of foo."""
        result = parse_message("$foo/")
        assert isinstance(result, ListChildren)
        assert result.parent == "foo"

    def test_list_children_with_underscores(self):
        """Test that $foo_bar. is treated as listing children of foo_bar."""
        result = parse_message("$foo_bar.")
        assert isinstance(result, ListChildren)
        assert result.parent == "foo_bar"

    def test_list_children_with_hyphens(self):
        """Test that $foo-bar. is treated as listing children of foo-bar."""
        result = parse_message("$foo-bar.")
        assert isinstance(result, ListChildren)
        assert result.parent == "foo-bar"

    def test_list_children_with_slashes(self):
        """Test that $foo/bar. is treated as listing children of foo/bar."""
        result = parse_message("$foo/bar.")
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
            result = parse_message(pattern)
            assert isinstance(result, Command), f"Expected Command for: {pattern}"
            assert result.cmd == expected_cmd
