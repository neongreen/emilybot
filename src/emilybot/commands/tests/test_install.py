from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock
import uuid
import json

import pytest

from emilybot.atomic_json_db import DBSaveError
from emilybot.commands import install_plan, install_source
from emilybot.commands.install import InstallState, InstallView, cmd_install
from emilybot.commands.install_plan import (
    apply_plan,
    compile_plan,
    definition_blocks,
    review_text,
)
from emilybot.commands.install_source import (
    InstallError,
    MAX_BYTES,
    checked_url,
    fetch_source,
)
from emilybot.database import DB, Entry, ActionInstall
from emilybot.discord import EmilyContext
from emilybot.execute.code_validation import InvalidCode

GAME = Path("docs/examples/guess-the-member.md").read_bytes()


def entry(name: str = "aa", **kwargs: Any) -> Entry:
    return replace(
        Entry(uuid.uuid4(), 123, 456, "then", name, "old", True, "print('old')"),
        **kwargs,
    )


@pytest.mark.timeout(20)
async def test_game_acceptance(db: DB) -> None:
    plan = await compile_plan(db, GAME, 123, 456)
    assert len(plan.changes) == 5
    assert plan.skipped == (".gcm",)
    assert all(c.after.run for c in plan.changes)
    apply_plan(db, plan)
    stored = list(db.remember.data)
    history = list(db.log.data)
    again = await compile_plan(db, GAME, 123, 456)
    assert not again.changed
    apply_plan(db, again)
    assert db.remember.data == stored
    assert db.log.data == history
    reloaded = DB(db.remember.file_path.parent)
    assert reloaded.remember.data == stored
    # typed-json-db reloads union actions as dicts, as it does existing edits.
    persisted = json.loads(db.log.file_path.read_text())
    assert [row["action"]["new_entry"]["run"] for row in persisted] == [
        c.after.run for c in plan.changes
    ]
    assert all(row["action"]["old_entry"] is None for row in persisted)


async def test_order_preservation_diff_and_batch(
    db: DB, monkeypatch: pytest.MonkeyPatch
) -> None:
    old = entry()
    db.remember.add(old)
    body = b'```\n.add aa first\n```\n```\n.edit aa final\n```\n````\n.set aa.run\n```js\nprint("new");\n```\n````'
    plan = await compile_plan(db, body, 123, 456)
    text = review_text(plan)
    assert "old/aa/content" in text and "new/aa/run" in text
    assert "'old'" in text and "'final'" in text
    unrelated = entry("other")
    db.remember.add(unrelated)
    save = MagicMock(wraps=getattr(db.remember, "_save"))
    monkeypatch.setattr(db.remember, "_save", save)
    db.store.path.write_text("{}")
    store_before = db.store.path.read_bytes()
    apply_plan(db, plan)
    assert save.call_count == 1
    new = db.remember.get(old.id)
    assert new == replace(old, content="final", run='print("new");')
    assert db.remember.get(unrelated.id) == unrelated
    action = db.log.data[-1].action
    assert isinstance(action, ActionInstall)
    assert action.old_entry == old and action.new_entry == new
    assert db.store.path.read_bytes() == store_before


@pytest.mark.parametrize("kind", ["edit", "recreate", "new", "unchanged"])
async def test_stale_plan(db: DB, kind: str) -> None:
    if kind != "new":
        db.remember.add(entry())
    plan = await compile_plan(
        db, b"```\n.add aa old\n```\n```\n.add bb other\n```", 123, 456
    )
    old = db.find_alias("aa", server_id=123)[0] if kind != "new" else None
    if kind == "edit" or kind == "unchanged":
        assert old
        db.remember.update(replace(old, promoted=False))
    else:
        if old:
            db.remember.remove(old.id)
        db.remember.add(entry())
    with pytest.raises(InstallError, match="changed since"):
        apply_plan(db, plan)
    assert not db.find_alias("bb", server_id=123)
    assert not db.log.data


async def test_invalid_and_large_code(db: DB, monkeypatch: pytest.MonkeyPatch) -> None:
    validate = AsyncMock(return_value=InvalidCode("bad"))
    monkeypatch.setattr(install_plan, "validate_command_code", validate)
    with pytest.raises(InstallError, match="Invalid JavaScript"):
        await compile_plan(
            db, b"```\n.add aa text\n```\n```\n.set aa.run bad\n```", 123, 456
        )
    assert not db.remember.data
    validate.return_value = None
    code = "//" + "x" * 2100
    plan = await compile_plan(
        db, f"```\n.add aa text\n```\n```\n.set aa.run {code}\n```".encode(), 123, 456
    )
    assert plan.changes[0].after.run == code


def test_markdown_blocks() -> None:
    assert definition_blocks(
        b"prose .add no text\n\n> ```\n> .add quote text\n> ```\n\n- example\n\n  ```\n  .add nested text\n  ```\n\n````ignored\n.set aa.run\n```js\nprint(1);\n```\n````"
    ) == [".set aa.run\n```js\nprint(1);\n```"]
    with pytest.raises(InstallError):
        definition_blocks(b"\xff")


@pytest.mark.parametrize(
    "target,state",
    [
        ("aliases", "old"),
        ("aliases", "new"),
        ("aliases", "unknown"),
        ("history", "old"),
    ],
)
async def test_save_failures(
    db: DB, monkeypatch: pytest.MonkeyPatch, target: str, state: Any
) -> None:
    plan = await compile_plan(db, b"```\n.add aa text\n```", 123, 456)
    table = db.log if target == "history" else db.remember

    def fail(rows: Any) -> None:
        raise DBSaveError(table.file_path, "injected", file_state=state)

    monkeypatch.setattr(table, "_save", fail)
    with pytest.raises(DBSaveError):
        apply_plan(db, plan)
    assert bool(db.remember.data) == (target == "history" or state == "new")
    assert not db.log.data


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/a/b/blob/main/a.md",
        "https://evil.test/a",
        "https://github.com:444/a",
        "https://u:p@github.com/a",
        "https://github.com.evil.test/a",
    ],
)
def test_hosts(url: str) -> None:
    with pytest.raises(InstallError):
        checked_url(url)


class Response:
    def __init__(
        self, body: bytes = GAME, status: int = 200, location: str = ""
    ) -> None:
        self.status = status
        self.headers = {"Location": location}
        self.body = body
        self.content = self

    async def __aenter__(self) -> "Response":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    async def iter_chunked(self, size: int):
        for offset in range(0, len(self.body), size):
            yield self.body[offset : offset + size]


class Session:
    def __init__(self, replies: list[Response]) -> None:
        self.replies = replies
        self.urls: list[str] = []

    async def __aenter__(self) -> "Session":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    def get(self, url: str, *, allow_redirects: bool) -> Response:
        assert not allow_redirects
        self.urls.append(url)
        return self.replies.pop(0)


@pytest.mark.timeout(20)
async def test_blob_and_attachment(
    make_ctx: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    for attachment in (False, True):
        session = Session([Response()])
        monkeypatch.setattr(
            install_source.aiohttp, "ClientSession", MagicMock(return_value=session)
        )
        ctx = make_ctx(".install")
        ctx.message.attachments = (
            [
                MagicMock(
                    filename="game.md",
                    size=len(GAME),
                    url="https://cdn.discordapp.com/attachments/game.md",
                )
            ]
            if attachment
            else []
        )
        await getattr(cmd_install, "callback")(
            ctx,
            source=""
            if attachment
            else "https://github.com/neongreen/emilybot/blob/main/docs/examples/guess-the-member.md",
        )
        view = ctx.send.call_args.kwargs["view"]
        assert len(view.plan.changed) == 5
        assert session.urls == (
            ["https://cdn.discordapp.com/attachments/game.md"]
            if attachment
            else [
                "https://raw.githubusercontent.com/neongreen/emilybot/main/docs/examples/guess-the-member.md"
            ]
        )
        view.finish()


async def test_redirect_stream_and_gist(monkeypatch: pytest.MonkeyPatch) -> None:
    session = Session([Response(status=302, location="https://evil.test/foo")])
    monkeypatch.setattr(
        install_source.aiohttp, "ClientSession", MagicMock(return_value=session)
    )
    with pytest.raises(InstallError):
        await fetch_source("https://raw.githubusercontent.com/a")
    assert len(session.urls) == 1
    session.replies = [Response(b"x" * (MAX_BYTES + 1))]
    with pytest.raises(InstallError, match="256 KiB"):
        await fetch_source("https://raw.githubusercontent.com/a")
    session.replies = [
        Response(b'<a href="https://gist.githubusercontent.com/u/id/raw/a.md">Raw</a>'),
        Response(),
    ]
    assert await fetch_source("https://gist.github.com/u/id") == GAME
    session.replies = [
        Response(b'<a href="/u/id/raw/a.md">Raw</a><a href="/u/id/raw/b.md">Raw</a>')
    ]
    with pytest.raises(InstallError, match="unambiguous"):
        await fetch_source("https://gist.github.com/u/id")


async def test_view_click_cancel_expire(make_ctx: Any) -> None:
    for outcome in ("install", "cancel", "expire"):
        ctx: EmilyContext = make_ctx(".install")
        baseline = len(ctx.bot.db.log.data)
        plan = await compile_plan(
            ctx.bot.db,
            f"```\n.add {outcome} text\n```".encode(),
            ctx.guild.id if ctx.guild else None,
            ctx.author.id,
        )
        state = InstallState()
        view = InstallView(ctx, plan, state)
        state.pending[ctx.author.id] = view
        interaction = MagicMock(user=ctx.author, guild_id=plan.server_id)
        interaction.response.edit_message = AsyncMock()
        interaction.response.send_message = AsyncMock()
        outsider = MagicMock(user=MagicMock(id=999), guild_id=plan.server_id)
        outsider.response.send_message = AsyncMock()
        assert not await view.interaction_check(outsider)
        if outcome == "expire":
            await view.on_timeout()
        else:
            button = view.install if outcome == "install" else view.cancel
            await button.callback(interaction)
        await view.install.callback(interaction)
        assert len(ctx.bot.db.log.data) == baseline + (1 if outcome == "install" else 0)
        assert view.finished and not state.pending
