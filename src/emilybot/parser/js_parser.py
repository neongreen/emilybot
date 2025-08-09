def is_js_pattern(content: str) -> bool:
    """
    Check if content looks like JavaScript code rather than a command.

    Args:
        content: The content to check (without the '$' prefix)

    Returns:
        True if content appears to be JavaScript code
    """
    # Check for JavaScript-like patterns
    js_patterns = [
        "()",
        "[]",
        "{}",
        ";",
        "+",
        "*",
        "<",
        ">",
        "!",
        "&",
        "|",
        "^",
        "%",
        "~",
    ]

    # Check for specific JavaScript patterns
    if any(char in content for char in js_patterns):
        return True

    # Check for regex patterns (starts with / and ends with /)
    if content.startswith("/") and content.endswith("/") and len(content) > 2:
        return True

    # Check for comments (starts with //)
    if content.startswith("//"):
        return True

    return False


def is_quoted_content(content: str) -> bool:
    """
    Check if content contains quotes, indicating it might be JavaScript.

    Args:
        content: The content to check

    Returns:
        True if content contains quotes
    """
    return any(char in content for char in "'\"`")
