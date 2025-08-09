from typing import List, Union
from dataclasses import dataclass


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

    # Remove the '$' prefix
    content = message_content[1:].strip()

    if not content:
        raise ValueError("No content found after '$'")

    # Check if it looks like JavaScript (contains parentheses, brackets, etc.)
    if any(char in content for char in "()[]{};,"):
        return JS(code=message_content)

    # Split by whitespace and filter out empty strings
    parts = [part.strip() for part in content.split() if part.strip()]

    if not parts:
        raise ValueError("No command name found after '$'")

    cmd_name = parts[0]
    args = parts[1:] if len(parts) > 1 else []

    return Command(cmd=cmd_name, args=args)
