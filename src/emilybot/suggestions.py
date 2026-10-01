"""Suggest existing names when someone types an alias that does not exist.

Suggestions are read-only: they never run, create or rename anything.
"""

import re

from emilybot.discord import EmilyContext

MAX_SUGGESTIONS = 3

# Names people have guessed when they wanted to see an alias's source.
# They are not registered as commands, so a community alias with one of
# these names still wins; the hint only appears when nothing matched.
SOURCE_VIEW_GUESSES = frozenset({"view", "code", "debug", "source", "src", "cat"})


def edit_distance(a: str, b: str) -> int:
    """Optimal string alignment distance: insertions, deletions, substitutions
    and swaps of two adjacent characters each cost 1.

    >>> edit_distance("hepl", "help")
    1
    >>> edit_distance("joke", "jokes")
    1
    >>> edit_distance("abc", "xyz")
    3
    """
    prev2: list[int] = []
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        prev2, prev = prev, cur
    return prev[len(b)]


def max_distance(name: str) -> int:
    """Short names get a tighter bound; otherwise every 3-letter name matches."""
    return 1 if len(name) <= 4 else 2


def close_names(name: str, candidates: set[str]) -> list[str]:
    """Return up to MAX_SUGGESTIONS candidates closest to `name`.

    >>> close_names("jokse", {"jokes", "joke", "weather"})
    ['joke', 'jokes']
    >>> close_names("zzz", {"jokes", "help"})
    []
    """
    name = name.lower()
    limit = max_distance(name)
    scored = [
        (d, c)
        for c in candidates
        if c != name and (d := edit_distance(name, c)) <= limit
    ]
    return [c for _, c in sorted(scored)[:MAX_SUGGESTIONS]]


def suggest_names(ctx: EmilyContext, name: str) -> list[str]:
    """Close names the caller could actually run from here.

    Candidates are built-in commands plus aliases visible in the caller's
    scope (this server, or the caller's own DM aliases). An alias that shares
    a name with a built-in is skipped because the built-in would run instead.
    """
    builtins = {c.name for c in ctx.bot.commands}
    aliases = ctx.bot.db.find_alias(
        re.compile(".*"),
        server_id=ctx.guild.id if ctx.guild else None,
        user_id=ctx.author.id,
    )
    candidates = builtins | {e.name for e in aliases if e.name not in builtins}
    return close_names(name, candidates)


def format_suggestion_lines(ctx: EmilyContext, name: str) -> str:
    """Lines to append to a not-found reply, each starting with a newline.

    Returns an empty string when there is nothing useful to add.
    """
    prefix = ctx.bot.just_command_prefix
    lines: list[str] = []
    if names := suggest_names(ctx, name):
        lines.append(
            "💡 Did you mean " + ", ".join(f"`{prefix}{n}`" for n in names) + "?"
        )
    if name.lower() in SOURCE_VIEW_GUESSES:
        lines.append(f"💡 To see an alias's text and code, use `{prefix}show [alias]`.")
    return "".join("\n" + line for line in lines)
