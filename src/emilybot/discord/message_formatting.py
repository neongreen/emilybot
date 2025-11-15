"""Message formatting utilities for Discord messages."""


def split_into_pages(content: str, max_length: int = 1900) -> list[str]:
    """Split content into pages that fit within Discord's message limit.

    Uses max_length of 1900 by default to leave room for page indicators.

    Args:
        content: The content to split into pages
        max_length: Maximum length per page (default: 1900)

    Returns:
        List of page strings with page indicators if multiple pages
    """
    if len(content) <= max_length:
        return [content]

    pages: list[str] = []
    lines = content.split("\n")
    current_page = ""

    for line in lines:
        # If adding this line would exceed the limit, start a new page
        if len(current_page) + len(line) + 1 > max_length:
            if current_page:
                pages.append(current_page)
                current_page = ""

            # If a single line is too long, split it by character
            if len(line) > max_length:
                while line:
                    chunk = line[:max_length]
                    pages.append(chunk)
                    line = line[max_length:]
            else:
                current_page = line + "\n"
        else:
            current_page += line + "\n"

    # Add the last page if there's content
    if current_page:
        pages.append(current_page)

    # Add page indicators
    if len(pages) > 1:
        pages = [
            f"{page.rstrip()}\n\n*Page {i + 1}/{len(pages)}*"
            for i, page in enumerate(pages)
        ]

    return pages
