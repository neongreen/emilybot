import re
from typing import Union

from discord.ext.commands.view import StringView  # pyright: ignore[reportMissingTypeStubs]

from emilybot.execute.javascript_executor import extract_js_code
from emilybot.parser.list_children_parser import (
    is_list_children_pattern,
    parse_list_children,
)
from emilybot.parser.types import JS, Command, ListChildren
from emilybot.validation import validate_path


def parse_command_invocation(content: str) -> Command | None:
    """
    Parse a message content into a command invocation.

    Args:
        content: The message content to parse, without the prefix

    Returns:
        Command with cmd name and list of arguments

    Examples:
        >>> parse_command_invocation("foo a b c")
        Command(cmd='foo', args=['a', 'b', 'c'])

        >>> parse_command_invocation("foo")
        Command(cmd='foo', args=[])

        >>> parse_command_invocation("foo.bar a b c")
        Command(cmd='foo/bar', args=['a', 'b', 'c'])

        >>> parse_command_invocation("foo/bar a b c")
        Command(cmd='foo/bar', args=['a', 'b', 'c'])

        >>> parse_command_invocation("foo-bar a b c")
        Command(cmd='foo-bar', args=['a', 'b', 'c'])

        >>> parse_command_invocation("") is None
        True

        >>> parse_command_invocation("$$") is None
        True
    """

    if not content:
        return None

    # Use StringView to parse the command and arguments
    view = StringView(content)

    # Get the command name (first word)
    cmd_name = view.get_word()
    if not cmd_name:
        return None

    try:
        cmd_name = validate_path(
            cmd_name,
            allow_trailing_slash=False,
            normalize_dots=True,
            normalize_dashes=False,
            check_component_length=True,
        )
        args = _parse_arguments(view)
        return Command(cmd=cmd_name, args=args)
    except Exception:
        return None


def parse_message(
    message: str, extra_prefixes: list[str] = []
) -> Union[Command, JS, ListChildren, None]:
    r"""
    Parse a message content into either a Command, JS, or ListChildren.

    Args:
        message: The message content to parse
        extra_prefixes: The prefixes to expect for the command (default: []).
          JavaScript code is *only* allowed for "$", not for any other prefix.

    Returns:
        Either Command with cmd name and list of arguments, JS with code to execute,
        or ListChildren with parent command to list children of.

    Command invocation:
        >>> parse_message("$foo a b c")
        Command(cmd='foo', args=['a', 'b', 'c'])

        >>> parse_message("$bar")
        Command(cmd='bar', args=[])

        >>> parse_message(".foo a b c", extra_prefixes=["."])
        Command(cmd='foo', args=['a', 'b', 'c'])

    List children:
        >>> parse_message(".foo/x/", extra_prefixes=["."])
        ListChildren(parent='foo/x')

        >>> parse_message("$foo.")
        ListChildren(parent='foo')

        >>> parse_message("$foo..")
        ListChildren(parent='foo')

        >>> parse_message("$foo/")
        ListChildren(parent='foo')

    JavaScript:
        >>> parse_message("$test;")
        JS(code='$test;')

        >>> parse_message('''$foo('a b', "c d")''')
        JS(code='$foo(\'a b\', "c d")')

        >>> parse_message("$foo._bar")  # invalid command because _bar starts with _
        JS(code='$foo._bar')

        >>> parse_message("$ f(x)")
        JS(code='f(x)')

        >>> parse_message("$\nf(x)")
        JS(code='f(x)')

    Stripping JS code blocks:
        >>> parse_message("$\n```js\nconsole.log('hello');\n```")
        JS(code="console.log('hello');")

        >>> parse_message("$```js\nconsole.log('hello');\n```")
        JS(code="console.log('hello');")

    Normalization:
        >>> parse_message("$foo.bar a b c")
        Command(cmd='foo/bar', args=['a', 'b', 'c'])

    Not a command:
        >>> parse_message("foo a b c") is None
        True
        >>> parse_message("$$$") is None
        True
        >>> parse_message("$") is None
        True
        >>> parse_message("/foo/bar") is None
        True
        >>> parse_message("//") is None
        True
        >>> parse_message("") is None
        True
        >>> parse_message("  ") is None
        True
        >>> parse_message("this is $dollar") is None
        True
        >>> parse_message("foo.bar a b c") is None
        True
        >>> parse_message("foo/bar a b c") is None
        True
        >>> parse_message("`js`") is None
        True
        >>> parse_message("```js\nconsole.log('hello');\n```") is None
        True
        >>> parse_message("$888") is None  # Just digits
        True
        >>> parse_message("$13.2") is None  # Dollar amount
        True
        >>> parse_message("$.12") is None  # Dollar amount
        True
        >>> parse_message("$/foo/") is None  # Just slashes
        True
    """

    # Determine the prefix used
    all_prefixes = ["$"] + extra_prefixes
    used_prefix = None

    for prefix in all_prefixes:
        if message.startswith(prefix):
            used_prefix = prefix
            break

    if used_prefix is None:
        return None

    content = message[len(used_prefix) :]

    if not content:
        return None

    if command := parse_command_invocation(content):
        return command

    # Check for list children pattern first
    if is_list_children_pattern(content):
        return parse_list_children(content)

    # JavaScript parsing is only allowed for "$" prefix
    if message.startswith("$"):
        # The only valid JS patterns are:
        # 1. Letters: $foo("a", "b")
        # 2. Digits followed by underscore or letter: $8ball(), $123abc()
        # 3. Whitespace followed by anything: $ console.log()
        # 4. Code blocks: $```js...```
        if (
            re.match(r"^\$[a-zA-Z]", message)  # $foo("x")
            or re.match(r"^\$\d+[a-zA-Z_]", message)  # $8ball(), $123abc(), $123_abc()
        ):
            return JS(code=message)
        elif (
            re.match(r"^\$\s+[^\s]", message)  # $ console.log()
            or re.match(r"^\$```", message)  # $```js...```
        ):
            if code := extract_js_code(message[1:]):
                return JS(code=code)

    return None


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
