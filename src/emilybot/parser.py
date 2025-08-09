from typing import List, Union
from dataclasses import dataclass
import re


@dataclass
class Command:
    """Represents a parsed command"""

    cmd: str
    args: List[str]


@dataclass
class JS:
    """Represents JavaScript code to execute"""

    code: str


@dataclass
class ListChildren:
    """Represents a request to list children of a command"""

    parent: str


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
        return JS(code=code)  # Strip "$" and whitespace, return as JS

    # Remove the '$' prefix
    content = message_content[1:].strip()

    if not content:
        raise ValueError("No content found after '$'")

    # Handle dot notation patterns
    # Check for $foo. (with optional trailing dots or slashes)
    dot_listing_pattern = r"^([a-zA-Z0-9_][a-zA-Z0-9_/\-]*[a-zA-Z0-9_/])[./]+$"
    dot_listing_match = re.match(dot_listing_pattern, content)
    if dot_listing_match:
        parent = dot_listing_match.group(1)
        return ListChildren(parent=parent)

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
            if not any(char in content for char in "'\"`"):
                # Additional check: only treat as command if both parent and child look like valid aliases
                if re.match(
                    r"^[a-zA-Z0-9_][a-zA-Z0-9_/\-]*[a-zA-Z0-9_/]$", parent
                ) and re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_/\-]*[a-zA-Z0-9_/]$", child):
                    # Construct the command as parent/child
                    cmd_name = f"{parent}/{child}"
                    args = remaining.split() if remaining else []

                    return Command(cmd=cmd_name, args=args)

    # Split by whitespace to get the first word (potential command name)
    parts = content.split(None, 1)  # Split on whitespace, max 1 split
    first_word = parts[0]

    # Check if the first word looks like a valid alias
    # A valid alias follows the same rules as the AliasValidator
    # It must start with alphanumeric or underscore, contain only alphanumeric, underscore, hyphen, or slash
    # and end with alphanumeric, underscore, or slash
    alias_pattern = r"^[a-zA-Z0-9_][a-zA-Z0-9_/\-]*[a-zA-Z0-9_/]$"

    if re.match(alias_pattern, first_word):
        # It looks like a valid alias, treat as command
        cmd_name = first_word
        args = parts[1].split() if len(parts) > 1 else []

        return Command(cmd=cmd_name, args=args)
    else:
        # If it doesn't match the alias pattern, treat as JavaScript
        return JS(code=message_content)
