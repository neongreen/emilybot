"""
Equivalence tests to verify our extracted StringView matches discord.py's implementation.

These tests compare the behavior of our extracted StringView with the original
discord.py StringView to ensure they are functionally identical.
"""

import pytest
from discord.ext.commands.view import StringView as DiscordStringView  # pyright: ignore[reportMissingTypeStubs]
from emilybot.parser.string_view import StringView as OurStringView
from discord.ext.commands.errors import (  # pyright: ignore[reportMissingTypeStubs]
    UnexpectedQuoteError as DiscordUnexpectedQuoteError,
    InvalidEndOfQuotedStringError as DiscordInvalidEndOfQuotedStringError,
    ExpectedClosingQuoteError as DiscordExpectedClosingQuoteError,
)
from emilybot.parser.string_view import (
    UnexpectedQuoteError as OurUnexpectedQuoteError,
    InvalidEndOfQuotedStringError as OurInvalidEndOfQuotedStringError,
    ExpectedClosingQuoteError as OurExpectedClosingQuoteError,
)


# Test data: various inputs that exercise different code paths
TEST_INPUTS = [
    # Simple words
    "hello",
    "hello world",
    "hello world foo bar",
    # Quoted strings
    '"hello world"',
    '"hello" "world"',
    "'single quotes'",
    # Mixed
    'hello "world foo" bar',
    'one "two three" four "five"',
    # Escaped quotes
    r'"hello \"world\""',
    r'"escaped \" quote"',
    r"'escaped \' quote'",
    # Unicode quotes
    '"fancy quotes"',
    "「Japanese」",
    "《Chinese》",
    # Edge cases
    "",
    " ",
    "  ",
    "\t",
    "\n",
    "a",
    " a ",
    "  a  b  ",
    # Special characters
    "hello-world",
    "foo_bar",
    "test123",
    "!@#$%",
    # Whitespace variations
    "a\tb\tc",
    "a\nb\nc",
    "a  b  c",
    # Backslashes
    r"hello\world",
    "test\\",
    r"\\",
    # Quote edge cases
    '"',
    '""',
    '"a',
    'a"',
    'a "b',
    'a" b',
    # Complex cases
    'cmd "arg 1" arg2 "arg 3"',
    '"first arg" second "third arg" fourth',
]


class TestGetWord:
    """Test get_word() method equivalence."""

    @pytest.mark.parametrize("input_str", TEST_INPUTS)
    def test_get_word_equivalence(self, input_str: str) -> None:
        """Test that get_word() produces identical results."""
        discord_view = DiscordStringView(input_str)
        our_view = OurStringView(input_str)

        # Get first word from both
        discord_word = discord_view.get_word()
        our_word = our_view.get_word()

        assert our_word == discord_word, f"get_word() mismatch for input: {input_str!r}"
        assert our_view.index == discord_view.index, (
            f"index mismatch after get_word() for input: {input_str!r}"
        )
        assert our_view.eof == discord_view.eof, (
            f"eof mismatch after get_word() for input: {input_str!r}"
        )


class TestGetQuotedWord:
    """Test get_quoted_word() method equivalence."""

    @pytest.mark.parametrize("input_str", TEST_INPUTS)
    def test_get_quoted_word_success(self, input_str: str) -> None:
        """Test that get_quoted_word() produces identical results for valid inputs."""
        discord_view = DiscordStringView(input_str)
        our_view = OurStringView(input_str)

        discord_error = None
        our_error = None
        discord_result = None
        our_result = None

        try:
            discord_result = discord_view.get_quoted_word()
        except (
            DiscordUnexpectedQuoteError,
            DiscordInvalidEndOfQuotedStringError,
            DiscordExpectedClosingQuoteError,
        ) as e:
            discord_error = e

        try:
            our_result = our_view.get_quoted_word()
        except (
            OurUnexpectedQuoteError,
            OurInvalidEndOfQuotedStringError,
            OurExpectedClosingQuoteError,
        ) as e:
            our_error = e

        # Both should either succeed or fail
        if discord_error is None and our_error is None:
            assert our_result == discord_result, (
                f"get_quoted_word() result mismatch for input: {input_str!r}"
            )
            assert our_view.index == discord_view.index, (
                f"index mismatch after get_quoted_word() for input: {input_str!r}"
            )
            assert our_view.eof == discord_view.eof, (
                f"eof mismatch after get_quoted_word() for input: {input_str!r}"
            )
        elif discord_error is not None and our_error is not None:
            # Both raised errors - check they're the same type
            assert type(our_error).__name__ == type(discord_error).__name__, (
                f"Exception type mismatch for input: {input_str!r}\n"
                f"Discord raised: {type(discord_error).__name__}\n"
                f"Ours raised: {type(our_error).__name__}"
            )
            # Check error messages are identical
            assert str(our_error) == str(discord_error), (
                f"Exception message mismatch for input: {input_str!r}\n"
                f"Discord: {discord_error}\n"
                f"Ours: {our_error}"
            )
        else:
            pytest.fail(
                f"One implementation raised error, other didn't for input: {input_str!r}\n"
                f"Discord error: {discord_error}\n"
                f"Our error: {our_error}"
            )


class TestSkipWs:
    """Test skip_ws() method equivalence."""

    @pytest.mark.parametrize("input_str", TEST_INPUTS)
    def test_skip_ws_equivalence(self, input_str: str) -> None:
        """Test that skip_ws() produces identical results."""
        discord_view = DiscordStringView(input_str)
        our_view = OurStringView(input_str)

        discord_result = discord_view.skip_ws()
        our_result = our_view.skip_ws()

        assert our_result == discord_result, (
            f"skip_ws() return value mismatch for input: {input_str!r}"
        )
        assert our_view.index == discord_view.index, (
            f"index mismatch after skip_ws() for input: {input_str!r}"
        )
        assert our_view.eof == discord_view.eof, (
            f"eof mismatch after skip_ws() for input: {input_str!r}"
        )


class TestReadRest:
    """Test read_rest() method equivalence."""

    @pytest.mark.parametrize("input_str", TEST_INPUTS)
    def test_read_rest_equivalence(self, input_str: str) -> None:
        """Test that read_rest() produces identical results."""
        discord_view = DiscordStringView(input_str)
        our_view = OurStringView(input_str)

        discord_result = discord_view.read_rest()
        our_result = our_view.read_rest()

        assert our_result == discord_result, (
            f"read_rest() mismatch for input: {input_str!r}"
        )
        assert our_view.index == discord_view.index, (
            f"index mismatch after read_rest() for input: {input_str!r}"
        )
        assert our_view.eof == discord_view.eof, (
            f"eof mismatch after read_rest() for input: {input_str!r}"
        )


class TestSequentialOperations:
    """Test sequences of operations to ensure stateful behavior matches."""

    def test_skip_ws_then_get_word(self) -> None:
        """Test skip_ws() followed by get_word()."""
        input_str = "  hello world"

        discord_view = DiscordStringView(input_str)
        our_view = OurStringView(input_str)

        discord_view.skip_ws()
        our_view.skip_ws()

        discord_word = discord_view.get_word()
        our_word = our_view.get_word()

        assert our_word == discord_word
        assert our_view.index == discord_view.index

    def test_get_word_then_skip_ws_then_get_word(self) -> None:
        """Test multiple operations in sequence."""
        input_str = "hello  world  foo"

        discord_view = DiscordStringView(input_str)
        our_view = OurStringView(input_str)

        # First word
        assert our_view.get_word() == discord_view.get_word()
        assert our_view.index == discord_view.index

        # Skip whitespace
        assert our_view.skip_ws() == discord_view.skip_ws()
        assert our_view.index == discord_view.index

        # Second word
        assert our_view.get_word() == discord_view.get_word()
        assert our_view.index == discord_view.index

    def test_multiple_quoted_words(self) -> None:
        """Test parsing multiple quoted words."""
        input_str = '"first" "second" "third"'

        discord_view = DiscordStringView(input_str)
        our_view = OurStringView(input_str)

        for _ in range(3):
            assert our_view.get_quoted_word() == discord_view.get_quoted_word()
            assert our_view.index == discord_view.index
            our_view.skip_ws()
            discord_view.skip_ws()


class TestExceptionEquivalence:
    """Test that exceptions are raised in the same cases with the same messages."""

    def test_unclosed_quote_error(self) -> None:
        """Test that unclosed quotes raise identical errors."""
        input_str = '"unclosed'

        discord_view = DiscordStringView(input_str)
        our_view = OurStringView(input_str)

        with pytest.raises(DiscordExpectedClosingQuoteError) as discord_exc:
            discord_view.get_quoted_word()

        with pytest.raises(OurExpectedClosingQuoteError) as our_exc:
            our_view.get_quoted_word()

        assert str(our_exc.value) == str(discord_exc.value)

    def test_unexpected_quote_error(self) -> None:
        """Test that unexpected quotes raise identical errors."""
        input_str = 'hello"world'

        discord_view = DiscordStringView(input_str)
        our_view = OurStringView(input_str)

        with pytest.raises(DiscordUnexpectedQuoteError) as discord_exc:
            discord_view.get_quoted_word()

        with pytest.raises(OurUnexpectedQuoteError) as our_exc:
            our_view.get_quoted_word()

        assert str(our_exc.value) == str(discord_exc.value)

    def test_invalid_end_of_quoted_string(self) -> None:
        """Test that invalid quote endings raise identical errors."""
        input_str = '"hello"world'

        discord_view = DiscordStringView(input_str)
        our_view = OurStringView(input_str)

        with pytest.raises(DiscordInvalidEndOfQuotedStringError) as discord_exc:
            discord_view.get_quoted_word()

        with pytest.raises(OurInvalidEndOfQuotedStringError) as our_exc:
            our_view.get_quoted_word()

        assert str(our_exc.value) == str(discord_exc.value)
