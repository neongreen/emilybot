import io
import json
import re
import random
import discord
from discord.ext import commands
from emilybot.execute.run_code import run_code
from emilybot.discord import EmilyContext

from emilybot.database import Entry
from emilybot.store import StoreRecord, json_size
from emilybot.utils.list import first
from emilybot.validation import validate_path, ValidationError
from emilybot.utils.inflect import inflect
from emilybot.suggestions import format_suggestion_lines


def format_not_found_message(command: str, command_prefix: str) -> str:
    """Format a helpful error message when a command is not found."""
    return (
        f"❓ Command '{command}' not found.\n"
        f"💡 Use `{command_prefix}add {command} [text]` to create this command."
    )


def format_validation_error(error_message: str) -> str:
    """Format validation error messages for user-friendly display."""
    return f"❌ {error_message}"


def trim_text(text: str, max_length: int = 900) -> str:
    """Trim text to max_length characters and append '...' if trimmed.

    Args:
        text: The text to trim
        max_length: Maximum length before trimming (default: 900)

    Returns:
        Original text if length <= max_length, otherwise trimmed text with '...'
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def allocate_display_budget(
    content_length: int,
    js_length: int,
    total_budget: int = 1800,
    min_per_section: int = 200,
) -> tuple[int, int]:
    """Allocate display budget between content and JavaScript based on their lengths.

    Args:
        content_length: Actual length of content text
        js_length: Actual length of JavaScript code
        total_budget: Total characters available (default: 1800)
        min_per_section: Minimum characters per section if both exist (default: 200)

    Returns:
        Tuple of (content_limit, js_limit) for how many characters to display
    """
    # If both fit within budget, show everything
    if content_length + js_length <= total_budget:
        return (content_length, js_length)

    # If only one section exists, give it the full budget
    if js_length == 0:
        return (min(content_length, total_budget), 0)
    if content_length == 0:
        return (0, min(js_length, total_budget))

    # If content is very short, give JS the remaining budget
    if content_length <= min_per_section:
        js_limit = min(js_length, total_budget - content_length)
        return (content_length, js_limit)

    # If JS is very short, give content the remaining budget
    if js_length <= min_per_section:
        content_limit = min(content_length, total_budget - js_length)
        return (content_limit, js_length)

    # Both are long - allocate proportionally, ensuring minimums
    total_length = content_length + js_length
    content_ratio = content_length / total_length
    js_ratio = js_length / total_length

    # Proportional allocation
    content_limit = int(total_budget * content_ratio)
    js_limit = int(total_budget * js_ratio)

    # Ensure minimums are met
    if content_limit < min_per_section:
        content_limit = min_per_section
        js_limit = total_budget - content_limit
    elif js_limit < min_per_section:
        js_limit = min_per_section
        content_limit = total_budget - js_limit

    return (content_limit, js_limit)


def _format_entry_sections(entry: Entry, content_limit: int, js_limit: int) -> str:
    js_text = entry.run.strip() if entry.run else ""
    formatted_content = f'**===** 📜 *Content of "{entry.name}"* **===**\n'
    trimmed_content = trim_text(entry.content, max_length=content_limit)
    formatted_content += f"```\n{trimmed_content}\n```\n"
    if js_text:
        formatted_content += f'\n**===** 🔧 *JavaScript of "{entry.name}"* **===**\n'
        trimmed_js = trim_text(js_text, max_length=js_limit)
        formatted_content += f"```js\n{trimmed_js}\n```"
    return formatted_content


def _entry_display_limits(entry: Entry) -> tuple[int, int, bool]:
    """Return (content_limit, js_limit, shortened) for the `.show` display."""
    js_text = entry.run.strip() if entry.run else ""
    content_limit, js_limit = allocate_display_budget(
        content_length=len(entry.content),
        js_length=len(js_text),
    )
    shortened = len(entry.content) > content_limit or len(js_text) > js_limit
    return content_limit, js_limit, shortened


async def format_entry_content(entry: Entry, ctx: EmilyContext) -> str:
    """Format entry content, *not* executing JavaScript.

    Args:
        entry: The database entry to format
        ctx: Discord context for accessing database and user info

    Returns:
        Formatted content and JS code
    """
    content_limit, js_limit, _ = _entry_display_limits(entry)
    return _format_entry_sections(entry, content_limit, js_limit)


def safe_attachment_stem(name: str) -> str:
    """Turn an alias name into a filename stem without path separators."""
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    return stem[:80] or "alias"


def entry_source_files(entry: Entry) -> list[discord.File]:
    """Attach the exact stored content and JavaScript of an entry."""
    stem = safe_attachment_stem(entry.name)
    files: list[discord.File] = []
    if entry.content:
        files.append(
            discord.File(io.BytesIO(entry.content.encode("utf-8")), f"{stem}.txt")
        )
    if entry.run:
        files.append(discord.File(io.BytesIO(entry.run.encode("utf-8")), f"{stem}.js"))
    return files


def format_store_summary(store: StoreRecord | None) -> str:
    """One line about an alias's `this.store`: key names and size, never values."""
    if store is None or not store.data:
        return ""
    keys = list(store.data)
    shown = ", ".join(f"`{k}`" for k in keys[:20])
    more = f" and {len(keys) - 20} more" if len(keys) > 20 else ""
    return (
        f"\n🗄️ *Stored data:* {len(keys)} {'key' if len(keys) == 1 else 'keys'}, "
        f"{json_size(store.data)} bytes ({shown}{more}). Values are not shown."
    )


async def send_entry(entry: Entry, ctx: EmilyContext) -> None:
    """Send the `.show` display, attaching the complete source when it is shortened.

    Never executes the entry's JavaScript.
    """
    content_limit, js_limit, shortened = _entry_display_limits(entry)
    store_summary = format_store_summary(ctx.bot.db.store.get(entry.id))
    display = _format_entry_sections(entry, content_limit, js_limit) + store_summary
    if not shortened:
        await ctx.send(display)
        return

    try:
        await ctx.send(
            display + "\n📎 *Shortened above; full source attached.*",
            files=entry_source_files(entry),
        )
    except discord.HTTPException:
        # Uploads forbidden or rejected: send everything through pagination.
        full = (
            _format_entry_sections(
                entry, len(entry.content), len(entry.run.strip() if entry.run else "")
            )
            + store_summary
        )
        await ctx.send(
            "📎 *Could not attach the source here, so here it is in full:*\n" + full
        )


def format_entry_line(entry: Entry) -> str:
    first_line = entry.content.split("\n")[0]
    if len(first_line) > 100:
        first_line = first_line[:100] + "..."
    return f"- {entry.name}: {first_line}"


@commands.command(name="show")
async def cmd_show(ctx: EmilyContext, alias: str) -> None:
    """`.show [alias][/]`: Show content of the alias."""

    db = ctx.bot.db
    command_prefix = ctx.bot.just_command_prefix
    server_id = ctx.guild.id if ctx.guild else None

    # `.show foo/` - list all aliases starting with "foo/"
    if alias.endswith("/"):
        # list by prefix
        results = db.find_alias(
            re.compile("^" + re.escape(alias), re.IGNORECASE),
            server_id=server_id,
            user_id=ctx.author.id,
        )
        if not results:
            await ctx.send(f"❓ No entries found for prefix '{alias}'.")
        else:
            await ctx.send(
                inflect(f"📜 Found no('entry', {len(results)})")
                + f" for '{alias}':\n"
                + "\n".join(format_entry_line(entry) for entry in results),
            )

    else:
        entry = first(db.find_alias(alias, server_id=server_id, user_id=ctx.author.id))
        if entry:
            await send_entry(entry, ctx)
        else:
            await ctx.send(
                format_not_found_message(alias, command_prefix)
                + format_suggestion_lines(ctx, alias)
            )


@commands.command(name="list")
async def cmd_list(ctx: EmilyContext) -> None:
    """`.list`: List all aliases."""

    db = ctx.bot.db
    server_id = ctx.guild.id if ctx.guild else None

    results = db.find_alias(
        re.compile(".*"), server_id=server_id, user_id=ctx.author.id
    )
    if not results:
        await ctx.send(f"❓ No entries found.")
    else:
        await ctx.send(", ".join(entry.name for entry in results))


@commands.command(name="random")
async def cmd_random(ctx: EmilyContext, alias: str) -> None:
    """`.random [alias]`: Get a random non-blank line from an entry."""

    db = ctx.bot.db
    command_prefix = ctx.bot.just_command_prefix

    try:
        # Validate alias
        validate_path(
            alias,
            normalize_dashes=False,
            normalize_dots=True,
            check_component_length=False,
            allow_trailing_slash=False,
        )

        server_id = ctx.guild.id if ctx.guild else None

        # Find existing entry
        entry = first(db.find_alias(alias, server_id=server_id, user_id=ctx.author.id))

        if not entry:
            await ctx.send(
                format_not_found_message(alias, command_prefix)
                + format_suggestion_lines(ctx, alias)
            )
            return

        # Run
        success, output, _ = await run_code(
            ctx, code=f"$.cmd({json.dumps(entry.name)})"
        )
        if not success:
            await ctx.send(output)  # Error message is already formatted
            return

        # Split content into lines and filter out blank lines
        lines = [line.strip() for line in output.split("\n")]
        non_blank_lines = [line for line in lines if line]

        if not non_blank_lines:
            await ctx.send(f"❓ '{alias}' gave no non-blank lines.")
            return

        # Select a random non-blank line
        random_line = random.choice(non_blank_lines)
        await ctx.send(random_line)

    except ValidationError as e:
        await ctx.send(format_validation_error(str(e)))
