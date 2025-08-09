import re
from typing import Union

from discord.ext.commands.view import StringView  # pyright: ignore[reportMissingTypeStubs]

from emilybot.execute.javascript_executor import extract_js_code
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


def parse_command(
    message_content: str, extra_command_prefixes: list[str] = []
) -> Union[Command, JS, ListChildren]:
    r"""
    Parse a message content into either a Command, JS, or ListChildren.

    Args:
        message_content: The message content to parse
        extra_command_prefixes: The prefixes to expect for the command (default: []).
          JavaScript code is *only* allowed for "$", not for any other prefix.

    Returns:
        Either Command with cmd name and list of arguments, JS with code to execute,
        or ListChildren with parent command to list children of.

    Command invocation:
        >>> parse_command("$foo a b c")
        Command(cmd='foo', args=['a', 'b', 'c'])

        >>> parse_command("$bar")
        Command(cmd='bar', args=[])

        >>> parse_command(".foo a b c", extra_command_prefixes=["."])
        Command(cmd='foo', args=['a', 'b', 'c'])

    List children:
        >>> parse_command(".foo/x/", extra_command_prefixes=["."])
        ListChildren(parent='foo/x')

        >>> parse_command("$foo.")
        ListChildren(parent='foo')

        >>> parse_command("$foo..")
        ListChildren(parent='foo')

        >>> parse_command("$foo/")
        ListChildren(parent='foo')

    JavaScript:
        >>> parse_command("$test;")
        JS(code='$test;')

        >>> parse_command('''$foo('a b', "c d")''')
        JS(code='$foo(\'a b\', "c d")')

        >>> parse_command("$foo._bar")  # invalid comment because _bar starts with _
        JS(code='$foo._bar')

        >>> parse_command("$ f(x)")
        JS(code='f(x)')

        >>> parse_command("$\nf(x)")
        JS(code='f(x)')

    Stripping JS code blocks:
        >>> parse_command("$\n```js\nconsole.log('hello');\n```")
        JS(code="console.log('hello');")

        >>> parse_command("$```js\nconsole.log('hello');\n```")
        JS(code="console.log('hello');")

    Normalization:
        >>> parse_command("$foo.bar a b c")
        Command(cmd='foo/bar', args=['a', 'b', 'c'])
    """

    # Determine the prefix used
    all_prefixes = ["$"] + extra_command_prefixes
    used_prefix = None

    for prefix in all_prefixes:
        if message_content.startswith(prefix):
            used_prefix = prefix
            break

    if used_prefix is None:
        raise ValueError(
            f"Message content must start with one of: {', '.join(all_prefixes)}"
        )

    # Check if it's just the prefix (no content)
    if message_content == used_prefix:
        raise ValueError(f"No content found after '{used_prefix}'")

    content_without_prefix = message_content[len(used_prefix) :]

    if not content_without_prefix:
        raise ValueError(f"No content found after '{used_prefix}'")

    # JavaScript parsing is only allowed for "$" prefix
    if used_prefix == "$":
        # Check if it starts with "$ ", "$\n", "$`"
        if re.match(r"^([\s]+|`)", content_without_prefix, re.UNICODE):
            code = extract_js_code(content_without_prefix)
            if not code:
                raise ValueError("Couldn't extract JavaScript code")
            return JS(code=code)
        if not content_without_prefix:
            raise ValueError("No content found after '$'")

    # Check for list children pattern first
    if is_list_children_pattern(content_without_prefix):
        return parse_list_children(content_without_prefix)

    try:
        return parse_command_invocation(message_content, prefix=used_prefix)
    except ValueError:
        # Only treat as JavaScript if using "$" prefix
        if used_prefix == "$":
            return JS(code=message_content)
        else:
            raise


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
