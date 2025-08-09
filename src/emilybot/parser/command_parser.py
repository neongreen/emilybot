from typing import Union

from discord.ext.commands.view import StringView  # pyright: ignore[reportMissingTypeStubs]

from emilybot.parser.js_parser import parse_js_code
from emilybot.parser.list_children_parser import (
    is_list_children_pattern,
    parse_list_children,
)
from emilybot.parser.types import JS, Command, ListChildren
from emilybot.validation import validate_path, ValidationError


def parse_command_invocation(message_content: str, *, prefix: str = "$") -> Command:
    """
    Parse a message content into a command invocation.

    Args:
        message_content: The message content to parse
        prefix: The prefix to expect for the command (default: "$")

    Returns:
        Command with cmd name and list of arguments

    Examples:
        >>> parse_command_invocation("$foo a b c")
        Command(cmd='foo', args=['a', 'b', 'c'])

        >>> parse_command_invocation("##foo a b c", prefix="##")
        Command(cmd='foo', args=['a', 'b', 'c'])

        >>> parse_command_invocation("$foo")
        Command(cmd='foo', args=[])

        >>> parse_command_invocation("$foo.bar a b c")
        Command(cmd='foo/bar', args=['a', 'b', 'c'])

        >>> parse_command_invocation("$foo/bar a b c")
        Command(cmd='foo/bar', args=['a', 'b', 'c'])
    """

    if not message_content.startswith(prefix):
        raise ValueError(f"Message content must start with '{prefix}'")

    content_without_prefix = message_content[len(prefix) :].strip()

    if not content_without_prefix:
        raise ValueError(f"No content found after '{prefix}'")

    # Use StringView to parse the command and arguments
    view = StringView(content_without_prefix)

    # Get the command name (first word)
    cmd_name = view.get_word()

    if not cmd_name:
        raise ValueError("No command name found")

    # Check if the command name looks like a valid alias
    try:
        cmd_name = validate_path(
            cmd_name, allow_trailing_slash=True, normalize_dots=True
        )
        args = _parse_arguments(view)
        return Command(cmd=cmd_name, args=args)
    except ValidationError:
        raise ValueError(f"Invalid command name: '{cmd_name}'")


def parse_command(message_content: str) -> Union[Command, JS, ListChildren]:
    """
    Parse a message content into either a Command, JS, or ListChildren.

    Args:
        message_content: The message content to parse

    Returns:
        Either Command with cmd name and list of arguments, JS with code to execute,
        or ListChildren with parent command to list children of

    Examples:
        >>> parse_command("$foo a b c")
        Command(cmd='foo', args=['a', 'b', 'c'])

        >>> parse_command("$bar")
        Command(cmd='bar', args=[])

        >>> parse_command("$test;")
        JS(code='$test;')

        >>> parse_command("$foo.bar a b c")
        Command(cmd='foo/bar', args=['a', 'b', 'c'])

        >>> parse_command("$foo._bar")
        JS(code='$foo._bar')

        >>> parse_command("$foo.")
        ListChildren(parent='foo')

        >>> parse_command("$foo..")
        ListChildren(parent='foo')

        >>> parse_command("$foo/")
        ListChildren(parent='foo')
    """

    if not message_content.startswith("$"):
        raise ValueError("Message content must start with '$'")

    # Check if it's just "$" (no content)
    if message_content == "$":
        raise ValueError("No content found after '$'")

    content_without_prefix = message_content[1:].strip()

    # Check if it starts with "$ " (dollar followed by any amount of whitespace) - treat as JavaScript
    if len(message_content) > 1 and message_content[1].isspace():
        code = message_content[1:].strip()
        if not code:
            raise ValueError("No content found after '$'")
        return parse_js_code(
            message_content
        )  # Strip prefix and whitespace, return as JS

    if not content_without_prefix:
        raise ValueError("No content found after '$'")

    # Check for list children pattern first
    if is_list_children_pattern(content_without_prefix):
        return parse_list_children(content_without_prefix)

    # Check for regex patterns (starts with / and ends with /)
    if (
        content_without_prefix.startswith("/")
        and content_without_prefix.endswith("/")
        and len(content_without_prefix) > 2
    ):
        return JS(code=message_content)

    # Check for comments (starts with //)
    if content_without_prefix.startswith("//"):
        return JS(code=message_content)

    try:
        return parse_command_invocation(message_content)
    except ValueError:
        return JS(code=message_content)


def _parse_arguments(view: StringView) -> list[str]:
    """
    Parse command arguments using Discord.py's StringView class.

    This function uses StringView's get_quoted_word() method to properly handle
    quoted strings and whitespace.

    Args:
        view: StringView instance positioned after the command name

    Returns:
        List of parsed arguments

    Examples:
        >>> _parse_arguments(StringView("a b c"))
        ['a', 'b', 'c']

    Single quotes are not supported:

        >>> _parse_arguments(StringView('''a b "c d" 'e f g' '''))
        ['a', 'b', 'c d', "'e", 'f', "g'"]
    """
    args: list[str] = []

    # Skip any leading whitespace
    view.skip_ws()

    while not view.eof:
        # Try to get a quoted word first
        arg = view.get_quoted_word()

        if arg is None:
            # No more arguments
            break

        args.append(arg)

        # Skip whitespace before next argument
        view.skip_ws()

    return args
