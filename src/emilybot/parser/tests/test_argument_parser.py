"""
Direct unit tests for the _parse_arguments function.

These tests focus on testing the argument parsing logic in isolation,
ensuring it correctly handles various edge cases and input patterns.
"""

import pytest
from emilybot.parser.command_parser import _parse_arguments
from emilybot.parser.string_view import (
    StringView,
    UnexpectedQuoteError,
    ExpectedClosingQuoteError,
    InvalidEndOfQuotedStringError,
)


class TestParseArguments:
    """Test _parse_arguments function directly."""

    def test_empty_string(self) -> None:
        """Test parsing empty string returns empty list."""
        assert _parse_arguments(StringView("")) == []

    def test_whitespace_only(self) -> None:
        """Test parsing whitespace-only string returns empty list."""
        assert _parse_arguments(StringView("   ")) == []
        assert _parse_arguments(StringView("\t\t")) == []
        assert _parse_arguments(StringView("\n\n")) == []

    def test_single_argument(self) -> None:
        """Test parsing single unquoted argument."""
        assert _parse_arguments(StringView("hello")) == ["hello"]
        assert _parse_arguments(StringView("  hello  ")) == ["hello"]

    def test_multiple_arguments(self) -> None:
        """Test parsing multiple unquoted arguments."""
        assert _parse_arguments(StringView("a b c")) == ["a", "b", "c"]
        assert _parse_arguments(StringView("foo bar baz")) == ["foo", "bar", "baz"]

    def test_arguments_with_extra_whitespace(self) -> None:
        """Test that extra whitespace between arguments is handled correctly."""
        assert _parse_arguments(StringView("a  b  c")) == ["a", "b", "c"]
        assert _parse_arguments(StringView("a   b   c")) == ["a", "b", "c"]
        assert _parse_arguments(StringView("  a  b  c  ")) == ["a", "b", "c"]

    def test_arguments_with_tabs(self) -> None:
        """Test arguments separated by tabs."""
        assert _parse_arguments(StringView("a\tb\tc")) == ["a", "b", "c"]
        assert _parse_arguments(StringView("\ta\tb\t")) == ["a", "b"]

    def test_quoted_argument(self) -> None:
        """Test parsing single quoted argument."""
        assert _parse_arguments(StringView('"hello world"')) == ["hello world"]
        assert _parse_arguments(StringView('  "hello world"  ')) == ["hello world"]

    def test_multiple_quoted_arguments(self) -> None:
        """Test parsing multiple quoted arguments."""
        assert _parse_arguments(StringView('"arg 1" "arg 2"')) == ["arg 1", "arg 2"]
        assert _parse_arguments(StringView('"foo bar" "baz qux"')) == [
            "foo bar",
            "baz qux",
        ]

    def test_mixed_quoted_and_unquoted(self) -> None:
        """Test mixing quoted and unquoted arguments."""
        assert _parse_arguments(StringView('hello "world foo" bar')) == [
            "hello",
            "world foo",
            "bar",
        ]
        assert _parse_arguments(StringView('"first arg" second "third arg"')) == [
            "first arg",
            "second",
            "third arg",
        ]

    def test_escaped_quotes(self) -> None:
        """Test arguments with escaped quotes inside."""
        assert _parse_arguments(StringView(r'"hello \"world\""')) == ['hello "world"']
        assert _parse_arguments(StringView(r'"escaped \" quote"')) == ['escaped " quote']

    def test_unicode_quotes(self) -> None:
        """Test that Unicode quotation marks work."""
        # U+201C LEFT DOUBLE QUOTATION MARK, U+201D RIGHT DOUBLE QUOTATION MARK
        assert _parse_arguments(StringView('"hello world"')) == ["hello world"]
        # Japanese corner brackets (need space between them)
        assert _parse_arguments(StringView('「hello」 「world」')) == ["hello", "world"]

    def test_single_quotes_not_special(self) -> None:
        """Test that regular single quotes (apostrophes) are not treated as quote characters."""
        # Regular apostrophes should NOT be treated as quotes
        result = _parse_arguments(StringView("'hello world'"))
        # They should be treated as regular characters, splitting on whitespace
        assert result == ["'hello", "world'"]

    def test_special_characters_in_arguments(self) -> None:
        """Test arguments containing special characters."""
        assert _parse_arguments(StringView("foo-bar")) == ["foo-bar"]
        assert _parse_arguments(StringView("foo_bar")) == ["foo_bar"]
        assert _parse_arguments(StringView("test123")) == ["test123"]
        assert _parse_arguments(StringView("!@#$%")) == ["!@#$%"]

    def test_empty_quoted_string(self) -> None:
        """Test empty quoted string."""
        assert _parse_arguments(StringView('""')) == [""]
        assert _parse_arguments(StringView('"" ""')) == ["", ""]

    def test_backslash_handling(self) -> None:
        """Test how backslashes are handled."""
        # Backslash followed by non-quote character is kept as-is in quoted strings
        assert _parse_arguments(StringView(r'"hello\world"')) == [r"hello\world"]
        # Backslash in unquoted string is kept as-is
        assert _parse_arguments(StringView(r"test\\")) == ["test\\"]

    def test_complex_real_world_examples(self) -> None:
        """Test complex real-world command argument patterns."""
        # Command with file paths
        assert _parse_arguments(StringView('"path/to/file.txt" output.log')) == [
            "path/to/file.txt",
            "output.log",
        ]

        # Command with URL
        assert _parse_arguments(StringView('"https://example.com" --verbose')) == [
            "https://example.com",
            "--verbose",
        ]

        # Mixed types of arguments
        assert _parse_arguments(StringView('cmd "arg 1" arg2 "arg 3" arg4')) == [
            "cmd",
            "arg 1",
            "arg2",
            "arg 3",
            "arg4",
        ]


class TestParseArgumentsErrors:
    """Test error cases in _parse_arguments."""

    def test_unclosed_quote_raises_error(self) -> None:
        """Test that unclosed quotes raise ExpectedClosingQuoteError."""
        with pytest.raises(ExpectedClosingQuoteError):
            _parse_arguments(StringView('"unclosed'))

        with pytest.raises(ExpectedClosingQuoteError):
            _parse_arguments(StringView('hello "unclosed'))

    def test_unexpected_quote_in_word_raises_error(self) -> None:
        """Test that unexpected quotes in unquoted words raise UnexpectedQuoteError."""
        with pytest.raises(UnexpectedQuoteError):
            _parse_arguments(StringView('hello"world'))

        with pytest.raises(UnexpectedQuoteError):
            _parse_arguments(StringView('test "arg" bad"quote'))

    def test_invalid_end_of_quoted_string_raises_error(self) -> None:
        """Test that invalid characters after closing quote raise InvalidEndOfQuotedStringError."""
        with pytest.raises(InvalidEndOfQuotedStringError):
            _parse_arguments(StringView('"hello"world'))

        with pytest.raises(InvalidEndOfQuotedStringError):
            _parse_arguments(StringView('"test"x'))


class TestParseArgumentsEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_argument(self) -> None:
        """Test parsing very long arguments."""
        long_arg = "a" * 1000
        assert _parse_arguments(StringView(long_arg)) == [long_arg]

        long_quoted = '"' + "x" * 1000 + '"'
        assert _parse_arguments(StringView(long_quoted)) == ["x" * 1000]

    def test_many_arguments(self) -> None:
        """Test parsing many arguments."""
        args = " ".join([f"arg{i}" for i in range(100)])
        result = _parse_arguments(StringView(args))
        assert len(result) == 100
        assert result[0] == "arg0"
        assert result[99] == "arg99"

    def test_newlines_as_whitespace(self) -> None:
        """Test that newlines are treated as whitespace."""
        assert _parse_arguments(StringView("a\nb\nc")) == ["a", "b", "c"]
        assert _parse_arguments(StringView("arg1\n\narg2")) == ["arg1", "arg2"]

    def test_mixed_whitespace_types(self) -> None:
        """Test mixing spaces, tabs, and newlines."""
        assert _parse_arguments(StringView("a \t b \n c")) == ["a", "b", "c"]
        assert _parse_arguments(StringView("\t \n a \t \n b")) == ["a", "b"]

    def test_quotes_with_internal_whitespace(self) -> None:
        """Test that quotes preserve internal whitespace."""
        assert _parse_arguments(StringView('"  hello  world  "')) == [
            "  hello  world  "
        ]
        assert _parse_arguments(StringView('"a\tb\nc"')) == ["a\tb\nc"]
