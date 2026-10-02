import asyncio
import gzip
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from dataclasses import replace

import pytest

from emilybot.atomic_json_db import DBSaveError
from emilybot.commands import install as installer
from emilybot.commands import install_source
from emilybot.commands.install import InstallState, InstallView
from emilybot.commands.install_plan import apply_plan, compile_plan
from emilybot.commands.install_source import InstallError, MAX_BYTES, fetch_source
from emilybot.commands.tests.test_install import Response, Session, entry
from emilybot.database import DB


async def test_compressed_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    response = Response(gzip.compress(b"x" * (MAX_BYTES + 1)))
    response.headers["Content-Encoding"] = "gzip"
    session = Session([response])
    monkeypatch.setattr(
        install_source.aiohttp, "ClientSession", MagicMock(return_value=session)
    )
    with pytest.raises(InstallError, match="256 KiB"):
        await fetch_source("https://raw.githubusercontent.com/a")
    response = Response(gzip.compress(b"valid text"))
    response.headers["Content-Encoding"] = "gzip"
    session.replies = [response]
    assert await fetch_source("https://raw.githubusercontent.com/a") == b"valid text"


async def test_dm_scope_content_only_and_stores(db: DB) -> None:
    other_user = entry(server_id=None, user_id=999)
    own = entry(server_id=None)
    guild = entry()
    for row in (other_user, own, guild):
        db.remember.add(row)
    db.store.path.write_text('{"example":"unchanged"}')
    plan = await compile_plan(db, b"```\n.add aa replacement\n```", None, 456)
    apply_plan(db, plan)
    assert db.remember.get(own.id) == replace(own, content="replacement")
    assert db.remember.get(other_user.id) == other_user
    assert db.remember.get(guild.id) == guild
    assert db.store.path.read_text() == '{"example":"unchanged"}'


@pytest.mark.parametrize(
    "body",
    [
        b"```\n.run print(1)\n```",
        b"```\n.edit missing hi\n```",
        b"```\n.set missing.run print(1)\n```",
        b"```\n.add aa\n```",
        b'```\n.add "unclosed hi\n```',
    ],
)
async def test_invalid_definition_files(db: DB, body: bytes) -> None:
    with pytest.raises(InstallError):
        await compile_plan(db, body, 123, 456)
    assert not db.remember.data and not db.log.data


@pytest.mark.parametrize(
    "target,state,expected",
    [
        ("remember", "old", "Nothing was changed"),
        ("remember", "unknown", "contents are unknown"),
        ("remember", "new", "Definitions were written"),
        ("log", "old", "Definitions were saved"),
        ("log", "new", "Definitions and history were written"),
    ],
)
async def test_reporting_and_no_retry(
    make_ctx: Any,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    state: Any,
    expected: str,
) -> None:
    ctx = make_ctx(".install")
    plan = await compile_plan(
        ctx.bot.db, b"```\n.add aa text\n```", ctx.guild.id, ctx.author.id
    )
    view_state = InstallState()
    view = InstallView(ctx, plan, view_state)
    view_state.pending[ctx.author.id] = view
    table = getattr(ctx.bot.db, target)
    failure = MagicMock(
        side_effect=DBSaveError(table.file_path, "test", file_state=state)
    )
    monkeypatch.setattr(installer, "apply_plan", failure)
    interaction = MagicMock(user=ctx.author, guild_id=ctx.guild.id)
    interaction.response.edit_message = AsyncMock()
    interaction.response.send_message = AsyncMock()
    await asyncio.gather(
        view.install.callback(interaction), view.install.callback(interaction)
    )
    assert failure.call_count == 1
    assert expected in interaction.response.edit_message.call_args.kwargs["content"]


async def test_replace_pending_preview_and_input(
    make_ctx: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = make_ctx(".install")
    ctx.message.attachments = []
    fetch = AsyncMock(return_value=b"```\n.add aa text\n```")
    monkeypatch.setattr(installer, "fetch_source", fetch)
    await getattr(installer.cmd_install, "callback")(
        ctx, source="https://raw.githubusercontent.com/file"
    )
    first = ctx.send.call_args.kwargs["view"]
    await getattr(installer.cmd_install, "callback")(
        ctx, source="https://raw.githubusercontent.com/file"
    )
    second = ctx.send.call_args.kwargs["view"]
    assert first.finished and not second.finished
    second.finish()
    ctx.message.attachments = [MagicMock()]
    await getattr(installer.cmd_install, "callback")(
        ctx, source="https://raw.githubusercontent.com/file"
    )
    assert fetch.call_count == 2
