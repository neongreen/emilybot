"""Tests for `.show` source attachments and `.random`."""

import io
import json
from collections.abc import Callable
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from emilybot.commands import show as show_module
from emilybot.commands.show import cmd_random, cmd_show, safe_attachment_stem
from emilybot.conftest import MakeCtx
from emilybot.database import Entry

DISCORD_LIMIT = 2000


def sent_calls(ctx: Any) -> list[Any]:
    return list(cast(AsyncMock, ctx.send).call_args_list)


def attachment_bytes(call: Any) -> dict[str, bytes]:
    files: list[discord.File] = call.kwargs.get("files", [])
    result: dict[str, bytes] = {}
    for f in files:
        fp = cast(io.BytesIO, f.fp)
        fp.seek(0)
        result[f.filename] = fp.read()
    return result


def make_entry(
    entry_factory: Callable[..., Entry], ctx_guild_id: int, **kwargs: Any
) -> Entry:
    entry = entry_factory(**kwargs)
    entry.server_id = ctx_guild_id
    return entry


def new_ctx(make_ctx: MakeCtx, message: str) -> Any:
    ctx: Any = make_ctx(message)
    ctx.bot.just_command_prefix = "."
    return ctx


@pytest.fixture
def no_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(".show must not execute code")

    monkeypatch.setattr(show_module, "run_code", fail)


@pytest.mark.asyncio
async def test_show_short_entry_has_no_attachments(
    make_ctx: MakeCtx, entry_factory: Callable[..., Entry], no_execution: None
):
    ctx = new_ctx(make_ctx, ".show small")
    entry = make_entry(
        entry_factory, ctx.guild.id, name="small", content="hi", run="print(1)"
    )
    ctx.bot.db.remember.add(entry)

    await cmd_show(ctx, "small")

    [call] = sent_calls(ctx)
    assert "files" not in call.kwargs
    assert "hi" in call.args[0] and "print(1)" in call.args[0]


@pytest.mark.parametrize(
    "content,run",
    [
        pytest.param("x" * 2500, None, id="long-content-only"),
        pytest.param("short", "print('a');\n" * 300, id="long-code"),
        pytest.param("y" * 1500, "z" * 1500, id="content-and-code"),
        pytest.param("a" * 5000, None, id="single-long-line"),
        pytest.param(
            "```\nfence\n```\n" * 200, "let s = '```';\n" * 200, id="backticks"
        ),
        pytest.param("🎲🃏 émoji\n" * 400, "print('🎲');\n" * 300, id="emoji"),
    ],
)
@pytest.mark.asyncio
async def test_show_shortened_attaches_exact_source(
    make_ctx: MakeCtx,
    entry_factory: Callable[..., Entry],
    no_execution: None,
    content: str,
    run: str | None,
):
    ctx = new_ctx(make_ctx, ".show big/game")
    entry = make_entry(
        entry_factory, ctx.guild.id, name="big/game", content=content, run=run
    )
    ctx.bot.db.remember.add(entry)

    await cmd_show(ctx, "big/game")

    [call] = sent_calls(ctx)
    text: str = call.args[0]
    assert len(text) <= DISCORD_LIMIT
    assert "full source attached" in text
    expected = {"big_game.txt": content.encode("utf-8")}
    if run:
        expected["big_game.js"] = run.encode("utf-8")
    assert attachment_bytes(call) == expected


@pytest.mark.asyncio
async def test_show_falls_back_to_pagination_when_upload_forbidden(
    make_ctx: MakeCtx, entry_factory: Callable[..., Entry], no_execution: None
):
    ctx = new_ctx(make_ctx, ".show big")
    content = "line of content\n" * 200
    run = "print('code line');\n" * 200
    entry = make_entry(
        entry_factory, ctx.guild.id, name="big", content=content, run=run
    )
    ctx.bot.db.remember.add(entry)

    response = MagicMock(status=403, reason="Forbidden")
    forbidden = discord.Forbidden(response, "Missing Permissions")
    seen: list[Any] = []

    async def send(text: str, **kwargs: Any) -> None:
        seen.append((text, kwargs))
        if "files" in kwargs:
            raise forbidden

    ctx.send = send

    await cmd_show(ctx, "big")

    assert len(seen) == 2
    fallback_text, fallback_kwargs = seen[1]
    assert "files" not in fallback_kwargs
    assert "Could not attach" in fallback_text
    assert content in fallback_text
    assert run.strip() in fallback_text


def test_safe_attachment_stem():
    assert safe_attachment_stem("games/sudoku.daily") == "games_sudoku_daily"
    assert safe_attachment_stem("../../etc") == "etc"
    assert safe_attachment_stem("🎲") == "alias"
    assert safe_attachment_stem("rand-flag_alt") == "rand-flag_alt"


@pytest.mark.parametrize(
    "name,content,run",
    [
        pytest.param("lines", "apple\n\n  banana  \n\ncherry\n", None, id="content"),
        pytest.param("games/coin", "heads\ntails", None, id="nested"),
        pytest.param(
            "printer",
            "ignored",
            "print('apple'); print(''); print('banana'); print('cherry')",
            id="printing-alias",
        ),
    ],
)
@pytest.mark.asyncio
async def test_random_picks_nonblank_output_line(
    make_ctx: MakeCtx,
    entry_factory: Callable[..., Entry],
    name: str,
    content: str,
    run: str | None,
):
    ctx = new_ctx(make_ctx, f".random {name}")
    entry = make_entry(entry_factory, ctx.guild.id, name=name, content=content, run=run)
    ctx.bot.db.remember.add(entry)

    await cmd_random(ctx, name)

    [call] = sent_calls(ctx)
    expected = (
        {"apple", "banana", "cherry"} if name != "games/coin" else {"heads", "tails"}
    )
    assert call.args[0] in expected


@pytest.mark.asyncio
async def test_random_whitespace_only_output(
    make_ctx: MakeCtx, entry_factory: Callable[..., Entry]
):
    ctx = new_ctx(make_ctx, ".random blank")
    entry = make_entry(entry_factory, ctx.guild.id, name="blank", content="  \n \n")
    ctx.bot.db.remember.add(entry)

    await cmd_random(ctx, "blank")

    [call] = sent_calls(ctx)
    assert "no non-blank lines" in call.args[0]


@pytest.mark.asyncio
async def test_random_passes_name_as_one_js_string_literal(
    make_ctx: MakeCtx,
    entry_factory: Callable[..., Entry],
    monkeypatch: pytest.MonkeyPatch,
):
    seen: list[str] = []

    async def fake_run_code(ctx: Any, *, code: str) -> tuple[bool, str, None]:
        seen.append(code)
        return True, "one", None

    monkeypatch.setattr(show_module, "run_code", fake_run_code)
    ctx = new_ctx(make_ctx, ".random games/coin")
    entry = make_entry(entry_factory, ctx.guild.id, name="games/coin", content="x")
    ctx.bot.db.remember.add(entry)

    await cmd_random(ctx, "games/coin")

    [code] = seen
    assert code.startswith("$.cmd(") and code.endswith(")")
    assert json.loads(code[len("$.cmd(") : -1]) == "games/coin"
