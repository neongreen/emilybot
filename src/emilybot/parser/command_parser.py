import re
from typing import Union

from emilybot.parser.js_parser import is_js_pattern, is_quoted_content, parse_js_code
from emilybot.parser.list_children_parser import (
    is_list_children_pattern,
    parse_list_children,
)
from emilybot.parser.types import JS, Command, ListChildren


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

    # Check if it starts with "$ " (dollar followed by any amount of whitespace) - treat as JavaScript
    if len(message_content) > 1 and message_content[1].isspace():
        code = message_content[1:].strip()
        if not code:
            raise ValueError("No content found after '$'")
        return parse_js_code(message_content)  # Strip "$" and whitespace, return as JS

    # Remove the '$' prefix
    content = message_content[1:].strip()

    if not content:
        raise ValueError("No content found after '$'")

    # Check for list children pattern first
    if is_list_children_pattern(content):
        return parse_list_children(content)

    # Check for dot notation command patterns
    if "." in content and not is_js_pattern(content):
        dot_command = _parse_dot_command(content)
        if dot_command:
            return dot_command

    # Split by whitespace to get the first word (potential command name)
    parts = content.split(None, 1)  # Split on whitespace, max 1 split
    first_word = parts[0]

    # Check if the first word looks like a valid alias
    if _is_valid_alias(first_word):
        # It looks like a valid alias, treat as command
        cmd_name = first_word
        args = _parse_arguments(parts[1]) if len(parts) > 1 else []
        return Command(cmd=cmd_name, args=args)
    else:
        # If it doesn't match the alias pattern, treat as JavaScript
        return JS(code=message_content)


def _parse_dot_command(content: str) -> Union[Command, None]:
    """
    Parse dot notation command patterns like $foo.bar args.

    Args:
        content: The content to parse (without the '$' prefix)

    Returns:
        Command object if it's a valid dot command, None otherwise
    """
    # Check for $foo.bar pattern (but not $foo._bar)
    # Only apply this if the content looks like a simple command pattern
    # and doesn't contain JavaScript-like patterns (but allow / for commands)
    if "." in content and not any(char in content for char in "()[]{};=+*<>!&|^%~"):
        dot_command_pattern = r"^([a-zA-Z0-9_][a-zA-Z0-9_/\-]*[a-zA-Z0-9_/])\.([a-zA-Z0-9][a-zA-Z0-9_/\-]*[a-zA-Z0-9_/])(.*)$"
        dot_command_match = re.match(dot_command_pattern, content)
        if dot_command_match:
            parent = dot_command_match.group(1)
            child = dot_command_match.group(2)
            remaining = dot_command_match.group(3).strip()

            # Additional check: only treat as command if it looks like a simple command
            # (no quotes, no complex patterns)
            if not is_quoted_content(content):
                # Additional check: only treat as command if both parent and child look like valid aliases
                if _is_valid_alias(parent) and _is_valid_alias(child):
                    # Construct the command as parent/child
                    cmd_name = f"{parent}/{child}"
                    args = _parse_arguments(remaining) if remaining else []
                    return Command(cmd=cmd_name, args=args)

    return None


def _parse_arguments(args_string: str) -> list[str]:
    """
    Parse command arguments, handling quoted strings properly.

    Args:
        args_string: The string containing arguments

    Returns:
        List of parsed arguments
    """
    if not args_string.strip():
        return []

    args: list[str] = []
    current_arg = ""
    in_quotes = False
    quote_char: str | None = None
    i = 0

    while i < len(args_string):
        char = args_string[i]

        if not in_quotes:
            if char in ['"', "'"]:
                in_quotes = True
                quote_char = char
                current_arg += char
            elif char.isspace():
                if current_arg:
                    args.append(current_arg)
                    current_arg = ""
            else:
                current_arg += char
        else:
            current_arg += char
            if char == quote_char:
                in_quotes = False
                quote_char = None

        i += 1

    if current_arg:
        args.append(current_arg)

    return args


def _is_valid_alias(alias: str) -> bool:
    """
    Check if a string looks like a valid alias.

    Args:
        alias: The string to check

    Returns:
        True if the string matches the alias pattern
    """
    # A valid alias follows the same rules as the AliasValidator
    # It must start with alphanumeric or underscore, contain only alphanumeric, underscore, hyphen, or slash
    # and end with alphanumeric, underscore, or slash
    alias_pattern = r"^[a-zA-Z0-9_][a-zA-Z0-9_/\-]*[a-zA-Z0-9_/]$"
    return bool(re.match(alias_pattern, alias))
