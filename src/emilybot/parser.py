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


def parse_command(message_content: str) -> Union[Command, JS]:
    """
    Parse a message content into either a Command or JS.

    Args:
        message_content: The message content to parse

    Returns:
        Either Command with cmd name and list of arguments, or JS with code to execute

    Examples:
        >>> parse_command("$foo a b c")
        Command(cmd='foo', args=['a', 'b', 'c'])

        >>> parse_command("$bar")
        Command(cmd='bar', args=[])

        >>> parse_command("$test;")
        JS(code='$test;')
    """

    if not message_content.startswith("$"):
        raise ValueError("Message content must start with '$'")

    # Check if it's just "$" (no content)
    if message_content == "$":
        raise ValueError("No content found after '$'")

    # Check if it starts with "$ " (dollar followed by any amount of whitespace) - treat as JavaScript
    if len(message_content) > 1 and message_content[1].isspace():
        return JS(
            code=message_content[1:].strip()
        )  # Strip "$" and whitespace, return as JS

    # Remove the '$' prefix
    content = message_content[1:].strip()

    if not content:
        raise ValueError("No content found after '$'")

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
