"""`this.store`: the store file, the commit contract, and the commands around it."""

import asyncio
import json
import uuid
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

import emilybot.store
from emilybot.atomic_json_db import DBSaveError
from emilybot.commands.delete import cmd_rm
from emilybot.commands.show import cmd_show
from emilybot.conftest import MakeCtx
from emilybot.database import DB, ActionDelete, Entry
from emilybot.execute.run_code import STORE_BUSY_MESSAGE, run_code
from emilybot.store import (
    StoreConflict,
    StoreDB,
    StoreQuotaExceeded,
    StoreTransaction,
    StoreUnavailable,
)
from emilybot.test_utils import AuthorConfig, ChannelConfig, GuildConfig

SERVER = 12345  # GuildConfig default


def txn(alias_id: uuid.UUID, version: int, **writes: Any) -> StoreTransaction:
    return StoreTransaction(
        reads={str(alias_id): version},
        writes={str(alias_id): {k: {"v": v} for k, v in writes.items()}},
    )


def always(_id: uuid.UUID) -> bool:
    return True


# --- StoreDB ---


def test_missing_file_is_empty(tmp_path: Path):
    store = StoreDB(tmp_path / "store.json")
    assert store.unavailable is None
    assert store.access(SERVER).unavailable is None


@pytest.mark.parametrize("text", ["", "  \n"])
def test_empty_file_is_empty(tmp_path: Path, text: str):
    (tmp_path / "store.json").write_text(text)
    store = StoreDB(tmp_path / "store.json")
    assert store.unavailable is None
    store.commit(SERVER, txn(uuid.uuid4(), 0, k=1), always)
    assert json.loads((tmp_path / "store.json").read_text(encoding="utf-8"))["stores"]


def test_commit_persists_and_bumps_version(tmp_path: Path):
    path = tmp_path / "store.json"
    alias = uuid.uuid4()
    StoreDB(path).commit(SERVER, txn(alias, 0, n=1, msg="héllo"), always)
    reloaded = StoreDB(path)
    rec = reloaded.get(alias)
    assert rec is not None
    assert (rec.server_id, rec.version, rec.data) == (
        SERVER,
        1,
        {"n": 1, "msg": "héllo"},
    )
    reloaded.commit(
        SERVER,
        StoreTransaction(
            reads={str(alias): 1}, writes={str(alias): {"n": {"d": True}}}
        ),
        always,
    )
    rec = StoreDB(path).get(alias)
    assert rec is not None and (rec.version, rec.data) == (2, {"msg": "héllo"})


def test_snapshot_is_per_server(tmp_path: Path):
    store = StoreDB(tmp_path / "store.json")
    a, b = uuid.uuid4(), uuid.uuid4()
    store.commit(SERVER, txn(a, 0, k=1), always)
    store.commit(999, txn(b, 0, k=2), always)
    saved = json.loads((tmp_path / "store.json").read_text(encoding="utf-8"))["stores"]
    assert saved[str(a)] == {"server_id": str(SERVER), "version": 1, "data": {"k": 1}}
    assert saved[str(b)]["server_id"] == "999"


def test_conflicts_commit_nothing(tmp_path: Path):
    store = StoreDB(tmp_path / "store.json")
    a, b = uuid.uuid4(), uuid.uuid4()
    store.commit(SERVER, txn(a, 0, k=1), always)
    with pytest.raises(StoreConflict):  # stale version
        store.commit(SERVER, txn(a, 0, k=2), always)
    with pytest.raises(StoreConflict):  # alias deleted or code changed
        store.commit(SERVER, txn(b, 0, k=2), lambda _id: False)
    both = StoreTransaction(
        reads={str(a): 1, str(b): 5},  # b is stale: nothing, not even a, is written
        writes={str(a): {"k": {"v": 3}}, str(b): {"k": {"v": 3}}},
    )
    with pytest.raises(StoreConflict):
        store.commit(SERVER, both, always)
    rec = StoreDB(tmp_path / "store.json").get(a)
    assert rec is not None and rec.data == {"k": 1}
    assert store.get(b) is None


def test_read_only_runs_never_conflict(tmp_path: Path):
    store = StoreDB(tmp_path / "store.json")
    a = uuid.uuid4()
    store.commit(
        SERVER, StoreTransaction(reads={str(a): 9}, writes={str(a): {}}), always
    )
    assert not (tmp_path / "store.json").exists()


@pytest.mark.parametrize(
    ("writes", "message"),
    [
        ({"big": "x" * (64 * 1024)}, "at most 64 KiB"),
        ({f"k{i}": i for i in range(257)}, "at most 256 keys"),
        ({"k" * 101: 1}, "1 to 100 characters"),
    ],
)
def test_store_quotas(tmp_path: Path, writes: dict[str, Any], message: str):
    store = StoreDB(tmp_path / "store.json")
    a = uuid.uuid4()
    with pytest.raises(StoreQuotaExceeded, match=message):
        store.commit(SERVER, txn(a, 0, **writes), always)
    assert store.get(a) is None and not (tmp_path / "store.json").exists()


def test_quota_counts_utf8_bytes(tmp_path: Path):
    store = StoreDB(tmp_path / "store.json")
    # 30,000 three-byte characters: 90,000 bytes, though only 30,000 characters
    with pytest.raises(StoreQuotaExceeded):
        store.commit(SERVER, txn(uuid.uuid4(), 0, s="€" * 30000), always)


def test_server_quota(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(emilybot.store, "SERVER_LIMIT_BYTES", 100)
    store = StoreDB(tmp_path / "store.json")
    store.commit(SERVER, txn(uuid.uuid4(), 0, s="x" * 60), always)
    store.commit(999, txn(uuid.uuid4(), 0, s="x" * 60), always)  # other server
    with pytest.raises(StoreQuotaExceeded, match="This server's stored data"):
        store.commit(SERVER, txn(uuid.uuid4(), 0, s="x" * 60), always)


def test_malformed_file_is_kept_and_stores_fail_clearly(tmp_path: Path):
    path = tmp_path / "store.json"
    path.write_text('{"stores": ')
    store = StoreDB(path)
    assert store.unavailable is not None
    assert store.access(SERVER).unavailable is not None
    with pytest.raises(StoreUnavailable):
        store.commit(SERVER, txn(uuid.uuid4(), 0, k=1), always)
    assert path.read_text() == '{"stores": '


def test_failed_save_changes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store = StoreDB(tmp_path / "store.json")
    a = uuid.uuid4()

    def failing(destination: Path, text: str) -> None:
        raise DBSaveError(destination, "disk full", file_state="old")

    monkeypatch.setattr(emilybot.store, "write_json_atomic", failing)
    with pytest.raises(DBSaveError):
        store.commit(SERVER, txn(a, 0, k=1), always)
    assert store.get(a) is None


# --- Through run_code ---


@pytest.fixture
def add_alias(db: DB, entry_factory: Callable[..., Entry]) -> Callable[..., Entry]:
    def _add(name: str, run: str, server_id: int | None = SERVER) -> Entry:
        entry = entry_factory(name=name, content=name, server_id=server_id, run=run)
        db.remember.add(entry)
        return entry

    return _add


COUNTER = "const n = this.store.get('n', 0) + 1; this.store.set('n', n); print(n)"


async def test_counter_persists_across_runs(
    make_ctx: MakeCtx, db: DB, add_alias: Callable[..., Entry]
):
    entry = add_alias("counter", COUNTER)
    for expected in ["1", "2", "3"]:
        assert await run_code(make_ctx(".counter"), code="$counter()") == (
            True,
            expected,
            None,
        )
    rec = db.store.get(entry.id)
    assert rec is not None and (rec.version, rec.data) == (3, {"n": 3})


async def test_real_discord_ids_keep_full_precision(
    make_ctx: MakeCtx, db: DB, entry_factory: Callable[..., Entry]
):
    guild = 1363717601859207340  # larger than 2**53
    entry = entry_factory(name="counter", content="c", server_id=guild, run=COUNTER)
    db.remember.add(entry)
    for expected in ["1", "2"]:
        ctx = make_ctx(".counter", guild=GuildConfig(id=guild))
        assert await run_code(ctx, code="$counter()") == (True, expected, None)


async def test_dm_aliases_have_no_store(
    make_ctx: MakeCtx, db: DB, add_alias: Callable[..., Entry]
):
    add_alias("probe", "print(typeof this.store)", server_id=None)
    ctx = make_ctx(".probe", is_dm=True, author=AuthorConfig(id=12345))
    assert await run_code(ctx, code="$probe()") == (True, "undefined", None)


async def test_inline_code_has_no_store(
    make_ctx: MakeCtx, add_alias: Callable[..., Entry]
):
    add_alias("counter", COUNTER)
    ok, output, _ = await run_code(
        make_ctx(".run"), code="print(typeof $.commands.counter.store, typeof this)"
    )
    assert (ok, output) == (True, "undefined undefined")


@pytest.mark.parametrize(
    "tail",
    [
        "throw new Error('after write')",
        "while (true) {}",
        "for (;;) print('x'.repeat(10000))",
    ],
)
@pytest.mark.timeout(20)
async def test_failed_runs_commit_nothing(
    make_ctx: MakeCtx, db: DB, add_alias: Callable[..., Entry], tail: str
):
    entry = add_alias("w", f"this.store.set('k', 1); {tail}")
    ok, _output, _ = await run_code(make_ctx(".w"), code="$w()")
    assert not ok
    assert db.store.get(entry.id) is None


async def test_quota_overflow_fails_the_run_and_hides_output(
    make_ctx: MakeCtx, db: DB, add_alias: Callable[..., Entry]
):
    entry = add_alias(
        "big", "print('secret output'); this.store.set('k', 'x'.repeat(70000))"
    )
    ok, output, _ = await run_code(make_ctx(".big"), code="$big()")
    assert not ok
    assert "64 KiB" in output and "secret output" not in output
    assert db.store.get(entry.id) is None


@pytest.mark.timeout(20)
async def test_concurrent_runs_one_commits_one_is_busy(
    make_ctx: MakeCtx, db: DB, add_alias: Callable[..., Entry]
):
    entry = add_alias(
        "slow",
        "const n = this.store.get('n', 0); const end = Date.now() + 1500; "
        "while (Date.now() < end) {} this.store.set('n', n + 1); print(n + 1)",
    )
    results = await asyncio.gather(
        run_code(make_ctx(".slow", author=AuthorConfig(id=1)), code="$slow()"),
        run_code(make_ctx(".slow", author=AuthorConfig(id=2)), code="$slow()"),
    )
    assert sorted(results, key=str) == sorted(
        [(True, "1", None), (False, STORE_BUSY_MESSAGE, None)], key=str
    )
    rec = db.store.get(entry.id)
    assert rec is not None and rec.data == {"n": 1}


@pytest.mark.timeout(20)
async def test_alias_deleted_during_run_is_not_resurrected(
    make_ctx: MakeCtx, db: DB, add_alias: Callable[..., Entry]
):
    entry = add_alias(
        "slow",
        "const end = Date.now() + 1500; while (Date.now() < end) {} "
        "this.store.set('n', 1); print('done')",
    )
    task = asyncio.create_task(run_code(make_ctx(".slow"), code="$slow()"))
    await asyncio.sleep(0.8)
    rm_ctx = make_ctx(".rm slow")
    await cmd_rm(rm_ctx, "slow")
    assert await task == (False, STORE_BUSY_MESSAGE, None)
    assert db.store.get(entry.id) is None
    assert db.remember.get(entry.id) is None


@pytest.mark.timeout(20)
async def test_code_changed_during_run_commits_nothing(
    make_ctx: MakeCtx, db: DB, add_alias: Callable[..., Entry]
):
    code = (
        "const end = Date.now() + 1500; while (Date.now() < end) {} "
        "this.store.set('n', 1); print('done')"
    )
    entry = add_alias("slow", code)
    task = asyncio.create_task(run_code(make_ctx(".slow"), code="$slow()"))
    await asyncio.sleep(0.8)
    db.remember.update(replace(entry, run=code + " // edited"))
    assert await task == (False, STORE_BUSY_MESSAGE, None)
    assert db.store.get(entry.id) is None


@pytest.mark.parametrize(
    "code", [COUNTER, "try { this.store.get('n') } catch {}\nprint('after')"]
)
async def test_half_written_store_file_makes_the_run_busy(
    make_ctx: MakeCtx, db: DB, add_alias: Callable[..., Entry], code: str
):
    entry = add_alias("counter", COUNTER)
    await run_code(make_ctx(".counter"), code="$counter()")
    # An in-place save caught halfway: the executor reads the file, not memory
    db.store.path.write_text(
        '{"stores": {"' + str(entry.id) + '": {"serv', encoding="utf-8"
    )
    add_alias("probe", code)
    assert await run_code(make_ctx(".probe"), code="$probe()") == (
        False,
        STORE_BUSY_MESSAGE,
        None,
    )
    rec = db.store.get(entry.id)
    assert rec is not None and rec.data == {"n": 1}


async def test_runs_without_a_store_file_and_without_using_it(
    make_ctx: MakeCtx, db: DB, add_alias: Callable[..., Entry]
):
    assert not db.store.path.exists()
    add_alias("plain", "print('fine')")
    assert await run_code(make_ctx(".plain"), code="$plain()") == (True, "fine", None)
    assert not db.store.path.exists()


async def test_unreadable_store_file(
    make_ctx: MakeCtx, entry_factory: Callable[..., Entry], tmp_path: Path
):
    (tmp_path / "store.json").write_text("not json")
    db = DB(data_dir=tmp_path)
    ctx = make_ctx(".x")
    ctx.bot.db = db
    db.remember.add(entry_factory(name="counter", server_id=SERVER, run=COUNTER))
    db.remember.add(entry_factory(name="plain", server_id=SERVER, run="print('fine')"))
    ok, output, _ = await run_code(ctx, code="$counter()")
    assert not ok and "this.store is unavailable" in output
    assert await run_code(ctx, code="$plain()") == (True, "fine", None)
    assert (tmp_path / "store.json").read_text() == "not json"


# --- .rm and .show ---


async def test_rm_snapshots_and_deletes_the_store(
    make_ctx: MakeCtx, db: DB, add_alias: Callable[..., Entry]
):
    entry = add_alias("counter", COUNTER)
    await run_code(make_ctx(".counter"), code="$counter()")
    await cmd_rm(make_ctx(".rm counter"), "counter")
    assert db.store.get(entry.id) is None
    [action] = [a.action for a in db.log.all()]
    assert isinstance(action, ActionDelete) and action.store == {"n": 1}
    # The saved log keeps it (typed-json-db reloads union-typed actions as plain dicts)
    reloaded = DB(data_dir=db.store.path.parent)
    [action] = [a.action for a in reloaded.log.all()]
    assert cast(dict[str, Any], action)["store"] == {"n": 1}


def test_old_delete_log_entries_still_load(
    tmp_path: Path, entry_factory: Callable[..., Entry]
):
    entry = entry_factory(name="old")
    log = [
        {
            "timestamp": "2025-01-01T00:00:00",
            "user_id": 1,
            "action": {
                "kind": "delete",
                "entry_id": str(entry.id),
                "entry": {
                    "id": str(entry.id),
                    "server_id": None,
                    "user_id": 1,
                    "created_at": entry.created_at,
                    "name": "old",
                    "content": "c",
                    "promoted": False,
                    "run": None,
                },
            },
        }
    ]
    (tmp_path / "remember_log.json").write_text(json.dumps(log))
    [action] = [a.action for a in DB(data_dir=tmp_path).log.all()]
    assert "store" not in cast(dict[str, Any], action)


async def test_show_lists_keys_and_size_not_values(
    make_ctx: MakeCtx, db: DB, add_alias: Callable[..., Entry]
):
    add_alias("game", "this.store.set('answer', 'swordfish'); this.store.set('n', 1)")
    await run_code(make_ctx(".game"), code="$game()")
    ctx = make_ctx(".show game")
    ctx.bot.just_command_prefix = "."
    await cmd_show(ctx, "game")
    assert isinstance(ctx.send, (MagicMock, AsyncMock))
    shown = ctx.send.call_args[0][0]
    assert "2 keys" in shown and "`answer`" in shown and "`n`" in shown
    assert "swordfish" not in shown.split("JavaScript")[0] + shown.split("```")[-1]


# --- channel ---


async def test_channel_in_context(make_ctx: MakeCtx):
    code = "print(JSON.stringify([channel, ctx.channel]))"
    ok, output, _ = await run_code(
        make_ctx(".run", channel=ChannelConfig(id=7, name="games")), code=code
    )
    channel = {"id": "7", "name": "games", "parent_id": None}
    assert (ok, json.loads(output)) == (True, [channel, channel])

    _, output, _ = await run_code(
        make_ctx(".run", channel=ChannelConfig(id=8, name="round 2", parent_id=7)),
        code=code,
    )
    assert json.loads(output)[0] == {"id": "8", "name": "round 2", "parent_id": "7"}

    _, output, _ = await run_code(
        make_ctx(".run", channel=ChannelConfig(id=9), is_dm=True), code=code
    )
    assert json.loads(output)[0] == {"id": "9", "name": None, "parent_id": None}
