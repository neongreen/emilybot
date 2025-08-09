import re

from emilybot.parser.types import ListChildren


def parse_list_children(content: str) -> ListChildren:
    """
    Parse content as a request to list children of a command.

    Args:
        content: The content to parse (without the '$' prefix)

    Returns:
        ListChildren object with the parent command
    """
    # Handle dot notation patterns
    # Check for $foo. (with optional trailing dots or slashes)
    dot_listing_pattern = r"^([a-zA-Z0-9_][a-zA-Z0-9_/\-]*[a-zA-Z0-9_/])[./]+$"
    dot_listing_match = re.match(dot_listing_pattern, content)
    if dot_listing_match:
        parent = dot_listing_match.group(1)
        return ListChildren(parent=parent)

    raise ValueError(f"Content '{content}' is not a valid list children pattern")


def is_list_children_pattern(content: str) -> bool:
    """
    Check if content looks like a list children pattern.

    Args:
        content: The content to check (without the '$' prefix)

    Returns:
        True if content appears to be a list children pattern
    """
    dot_listing_pattern = r"^([a-zA-Z0-9_][a-zA-Z0-9_/\-]*[a-zA-Z0-9_/])[./]+$"
    return bool(re.match(dot_listing_pattern, content))
