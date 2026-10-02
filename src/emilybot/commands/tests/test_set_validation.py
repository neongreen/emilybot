"""`.set name.run` rejects invalid JavaScript and keeps the old code."""

import asyncio
from dataclasses import replace
import json
import time
from pathlib import Path
from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock

import pytest

from emilybot.commands import set as set_module
from emilybot.commands.set import cmd_set
from emilybot.atomic_json_db import DBSaveError
from emilybot.conftest import MakeCtx
from emilybot.database import DB, ActionEdit, Entry
from emilybot.execute.code_validation import (
    InvalidCode,
    ValidatorFailed,
    validate_command_code,
)
from emilybot.execute.executor import JavaScriptExecutor
from emilybot.execute.javascript_executor import extract_js_code
from emilybot.execute.context import Context, CtxMessage, create_test_user

SERVER_ID = 12345  # GuildConfig default
COMMUNITY = json.loads(
    (Path(__file__).parent / "fixtures" / "community_commands.json").read_text()
)
OLD_CODE = "print('old')"


@pytest.fixture
def entry(entry_factory: Callable[..., Entry]) -> Entry:
    return entry_factory(name="foo", content="FOO", server_id=SERVER_ID, run=OLD_CODE)


def set_ctx(make_ctx: MakeCtx, message: str, entry: Entry) -> Any:
    ctx = make_ctx(message, entry)
    ctx.bot.just_command_prefix = "."
    return ctx


def sent(ctx: Any) -> str:
    assert isinstance(ctx.send, (MagicMock, AsyncMock))
    ctx.send.assert_called_once()
    return ctx.send.call_args[0][0]


# --- The validator ---


@pytest.mark.parametrize(
    "code",
    [
        "print(1)",
        "return 5",  # top-level return
        "2 + 2",  # final expression
        "globalX = 1",  # global assignment
        "while (true) {}",  # never run, so never loops
        "$missing(); return $.cmd('also-missing')",  # dependencies need not exist
        "import { camelCase } from 'https://esm.sh/change-case@5.4.0'\ncamelCase('a')",
        "import x from 'https://esm.sh/x'\nimport * as y from 'https://esm.sh/y'\nimport 'https://esm.sh/z'",
        "const m = await import('https://esm.sh/x')",
        *COMMUNITY.values(),
    ],
)
async def test_validator_accepts(code: str):
    assert await validate_command_code(code) is None


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("let let = (", InvalidCode("Unexpected strict mode reserved word", 1, 5)),
        (
            "print(1)\nfunction f() { return }}",
            InvalidCode("Unexpected token: '}'", 2, 24),
        ),
        # Parses, but fails QuickJS compilation of the stored function
        (
            "let x = 1; let x = 2",
            InvalidCode("invalid redefinition of lexical identifier"),
        ),
    ],
)
async def test_validator_rejects(code: str, expected: InvalidCode):
    assert await validate_command_code(code) == expected


async def test_validator_makes_no_network_calls():
    # The validator runs without --allow-net; an import of an unreachable host still validates fast
    start = time.monotonic()
    assert (
        await validate_command_code("import x from 'https://esm.sh/does-not-exist-xyz'")
        is None
    )
    assert time.monotonic() - start < 5


# --- .set ---


async def test_invalid_code_keeps_entry_and_log(
    make_ctx: MakeCtx, db: DB, entry: Entry
):
    ctx = set_ctx(make_ctx, ".set foo.run let let = (", entry)
    await cmd_set(ctx, "foo.run", value="```js\nlet let = (\n```")
    message = sent(ctx)
    assert "`foo`" in message and "line 1, column 5" in message
    assert "not changed" in message
    stored = db.remember.get(entry.id)
    assert stored is not None and stored.run == OLD_CODE
    assert db.log.all() == []
    ctx.react_success.assert_not_called()  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize("name", sorted(COMMUNITY))
async def test_community_code_saves_and_runs_as_stored(
    make_ctx: MakeCtx, db: DB, entry: Entry, name: str
):
    ctx = set_ctx(make_ctx, ".set foo.run ...", entry)
    await cmd_set(ctx, "foo.run", value=COMMUNITY[name])
    ctx.react_success.assert_called_once()  # pyright: ignore[reportAttributeAccessIssue]
    stored = db.remember.get(entry.id)
    assert stored is not None and stored.run == extract_js_code(COMMUNITY[name])
    assert len(db.log.all()) == 1


async def test_saved_code_compiles_in_the_executor(
    make_ctx: MakeCtx, db: DB, entry: Entry
):
    ctx = set_ctx(make_ctx, ".set foo.run ...", entry)
    await cmd_set(ctx, "foo.run", value="```js\nreturn args.length * 2\n```")
    stored = db.remember.get(entry.id)
    assert stored is not None
    ok, _output, value = await JavaScriptExecutor().execute(
        "$foo(1, 2)",
        Context(
            message=CtxMessage(text=".foo"),
            reply_to=None,
            user=create_test_user(),
            server=None,
        ),
        [{"name": stored.name, "content": stored.content, "run": stored.run}],
    )
    assert (ok, value) == (True, "4")


async def test_validator_failure_keeps_old_code(
    make_ctx: MakeCtx, db: DB, entry: Entry, monkeypatch: pytest.MonkeyPatch
):
    async def broken(code: str) -> InvalidCode | None:
        raise ValidatorFailed("boom")

    monkeypatch.setattr(set_module, "validate_command_code", broken)
    ctx = set_ctx(make_ctx, ".set foo.run print(2)", entry)
    await cmd_set(ctx, "foo.run", value="print(2)")
    message = sent(ctx)
    assert "checking it failed" in message and "syntax" not in message
    stored = db.remember.get(entry.id)
    assert stored is not None and stored.run == OLD_CODE


# --- Edits and deletes while validation runs ---


@pytest.fixture
def paused_validator(monkeypatch: pytest.MonkeyPatch) -> asyncio.Event:
    release = asyncio.Event()

    async def paused(code: str) -> InvalidCode | None:
        await release.wait()
        return None

    monkeypatch.setattr(set_module, "validate_command_code", paused)
    return release


async def test_delete_during_validation_is_not_undone(
    make_ctx: MakeCtx, db: DB, entry: Entry, paused_validator: asyncio.Event
):
    ctx = set_ctx(make_ctx, ".set foo.run print(2)", entry)
    task = asyncio.create_task(cmd_set(ctx, "foo.run", value="print(2)"))
    await asyncio.sleep(0.01)
    db.remember.remove(entry.id)
    paused_validator.set()
    await task
    assert db.remember.get(entry.id) is None
    assert "deleted" in sent(ctx)
    assert db.log.all() == []


async def test_edit_during_validation_is_kept(
    make_ctx: MakeCtx, db: DB, entry: Entry, paused_validator: asyncio.Event
):
    ctx = set_ctx(make_ctx, ".set foo.run print(2)", entry)
    task = asyncio.create_task(cmd_set(ctx, "foo.run", value="print(2)"))
    await asyncio.sleep(0.01)
    current = db.remember.get(entry.id)
    assert current is not None
    db.remember.update(
        replace(current, content="edited meanwhile", run="print('concurrent')")
    )
    paused_validator.set()
    await task
    stored = db.remember.get(entry.id)
    assert stored is not None
    assert (stored.content, stored.run) == ("edited meanwhile", "print(2)")
    log = db.log.all()
    assert len(log) == 1
    action = log[0].action
    assert isinstance(action, ActionEdit)
    assert action.old_content == "run: print('concurrent')"


async def test_empty_code_skips_validation(
    make_ctx: MakeCtx, db: DB, entry: Entry, monkeypatch: pytest.MonkeyPatch
):
    async def must_not_run(code: str) -> InvalidCode | None:
        raise AssertionError("validator called")

    monkeypatch.setattr(set_module, "validate_command_code", must_not_run)
    ctx = set_ctx(make_ctx, ".set foo.run ``` ```", entry)
    await cmd_set(ctx, "foo.run", value="```js\n```")
    ctx.react_success.assert_called_once()  # pyright: ignore[reportAttributeAccessIssue]


async def test_failed_save_after_validation_sends_no_success(
    make_ctx: MakeCtx, db: DB, entry: Entry, monkeypatch: pytest.MonkeyPatch
):
    ctx = set_ctx(make_ctx, ".set foo.run print(2)", entry)

    def failing_update(item: Entry) -> Entry:
        raise DBSaveError(Path("remember.json"), "disk full", file_state="old")

    monkeypatch.setattr(db.remember, "update", failing_update)
    with pytest.raises(DBSaveError):
        await cmd_set(ctx, "foo.run", value="print(2)")
    ctx.react_success.assert_not_called()  # pyright: ignore[reportAttributeAccessIssue]
    assert db.log.all() == []
