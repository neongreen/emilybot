def format_show_content(content: str, value: str | None) -> str:
    # trim if >1800char, *then* trim if >100 lines.
    # Discord limit is 2000 but we go a bit lower.
    content = content.strip()
    if content == "" and value is None:
        return "No output or value returned."
    elif content == "" and value is not None:
        return f"**Returned value:**{single_or_triple_backticks(limit(value, 1900))}"
    else:
        content = limit(content, 1800)
        if value:
            content += f"\n\n**Returned value:**{single_or_triple_backticks(limit(value, 100, 10))}"
        return content


def limit(text: str, max_length: int, max_lines: int = 100) -> str:
    """Limit text to max_length characters and max_lines lines."""
    if len(text) > max_length:
        text = text[:max_length] + "..."
    if text.count("\n") > max_lines:
        text = "\n".join(text.split("\n")[:max_lines]) + "..."
    return text


def single_or_triple_backticks(code: str) -> str:
    """Wrap code in single or triple backticks based on its length."""
    code = code.strip()
    if len(code) > 120 or "\n" in code:
        return f"\n```js\n{code}\n```"
    else:
        return f"`{code}`"
