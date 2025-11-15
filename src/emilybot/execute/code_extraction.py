"""JavaScript code extraction and parsing utilities."""


def extract_js_code(raw_code: str) -> str:
    """Parse and clean JavaScript code by stripping triple backticks.

    Handles various backtick formats (markdown):
    - Plain triple backticks:
      ```
      code
      ```

    - With a language identifier (for now we accept anything):
      ```js|javascript|...
      code
      ```

    - With additional text after language identifier:
      ```js foo bar
      code
      ```

    Args:
        raw_code: Raw JavaScript code that may contain triple backticks

    Returns:
        Cleaned JavaScript code with backticks and language identifiers removed

    Examples:
        >>> extract_js_code('```js\\nfoo\\n```')
        'foo'
        >>> extract_js_code('```js foo ```')
        'js foo'
        >>> extract_js_code('```\\nfoo\\n```')
        'foo'
        >>> extract_js_code('```foo```')
        'foo'
        >>> extract_js_code('foo(abc)')
        'foo(abc)'
    """
    code = raw_code.strip()

    # Handle empty or whitespace-only input
    if not code:
        return ""

    # Handle single-line case (no newlines)
    if "\n" not in code:
        # Strip backticks from start and end
        if code.startswith("```") and code.endswith("```"):
            return code[3:-3].strip()
        return code

    lines = code.splitlines()

    # Remove opening backticks line (first line that is exactly ```<identifier>)
    if lines and _is_code_block_opener(lines[0]):
        lines.pop(0)

    # Remove closing backticks line (last line that is exactly ```)
    if lines and lines[-1].strip() == "```":
        lines.pop()

    # Handle edge case where we removed all lines
    if not lines:
        return ""

    return "\n".join(lines).strip()


def _is_code_block_opener(line: str) -> bool:
    """Check if a line is a code block opener (```<identifier> with no extra content).

    Args:
        line: Line to check

    Returns:
        True if the line is exactly ``` followed by optional identifier and whitespace
    """
    stripped = line.strip()
    if not stripped.startswith("```"):
        return False

    # Remove the opening ```
    content = stripped[3:].strip()

    # If there's no content after ```, it's a valid opener
    if not content:
        return True

    # If there's content, it should be just an identifier (no spaces or extra text)
    # This allows ```js, ```javascript, etc. but not ```js foo bar
    return " " not in content
