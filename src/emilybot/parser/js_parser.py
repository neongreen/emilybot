from emilybot.parser.types import JS


def parse_js_code(message_content: str) -> JS:
    """
    Parse message content as JavaScript code.

    Args:
        message_content: The message content to parse as JavaScript

    Returns:
        JS object with the code to execute
    """
    # Remove the '$' prefix and any leading whitespace
    code = message_content[1:].strip()
    return JS(code=code)


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
