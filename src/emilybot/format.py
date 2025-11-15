def format_show_content(content: str, value: str | None) -> str:
    # Let ctx.send() handle pagination instead of truncating here
    content = content.strip()
    if content == "" and value is None:
        return "*No output or value returned.*"
    elif content == "" and value is not None:
        return f"*Result:* {single_or_triple_backticks(value)}"
    else:
        if value:
            content += f"\n\n*Result:* {single_or_triple_backticks(value)}"
        return content


def single_or_triple_backticks(code: str) -> str:
    """Wrap code in single or triple backticks based on its length."""
    code = code.strip()
    if len(code) > 120 or "\n" in code:
        return f"\n```js\n{code}\n```"
    else:
        return f"`{code}`"
