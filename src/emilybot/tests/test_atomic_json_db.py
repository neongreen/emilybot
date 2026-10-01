"""Tests for crash-safe database saves (emilybot.atomic_json_db)."""

import dataclasses
import json
import os
import signal
import subprocess
import sys
import textwrap
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typed_json_db import JsonDB

from emilybot.atomic_json_db import DBLoadError, DBSaveError
from emilybot.commands.delete import cmd_rm
from emilybot.commands.edit import cmd_edit
from emilybot.commands.promote import cmd_promote
from emilybot.commands.save import cmd_add
from emilybot.commands.set import cmd_set
from emilybot.conftest import MakeCtx
from emilybot.database import (
    DB,
    Action,
    ActionCreate,
    ActionDelete,
    ActionEdit,
    Entry,
)
from emilybot.discord.bot import format_save_error

# make_ctx's default author and guild
USER_ID = 67890
SERVER_ID = 12345


def make_entry(name: str = "nqueens", **kwargs: Any) -> Entry:
    fields: dict[str, Any] = dict(
        id=uuid.uuid4(),
        server_id=SERVER_ID,
        user_id=USER_ID,
        created_at=datetime(2025, 9, 1, 12, 30).isoformat(),
        name=name,
        content="placeholder ` with backticks and emoji 🎲",
        promoted=False,
        run='const n = 8;\nprint("```js\\n" + n)',
    )
    fields.update(kwargs)
    return Entry(**fields)


def sample_actions(entry: Entry) -> list[Action]:
    return [
        Action(
            timestamp=datetime(2025, 9, 1, 12, 30, 5),
            user_id=USER_ID,
            action=ActionCreate(
                kind="create",
                server_id=SERVER_ID,
                name=entry.name,
                content=entry.content,
                entry_id=entry.id,
            ),
        ),
        Action(
            timestamp=datetime(2025, 9, 2, 8, 0),
            user_id=USER_ID,
            action=ActionEdit(
                kind="edit",
                entry_id=entry.id,
                old_content="run: None",
                new_content=f"run: {entry.run}",
            ),
        ),
        Action(
            timestamp=datetime(2025, 9, 3, 9, 15),
            user_id=USER_ID,
            action=ActionDelete(kind="delete", entry_id=entry.id, entry=entry),
        ),
    ]


def read_bytes(path: Path) -> bytes:
    return path.read_bytes()


def temp_files(directory: Path) -> list[Path]:
    return [p for p in directory.iterdir() if p.name.endswith(".tmp")]


# --- format and reopen ---


def test_bytes_match_typed_json_db_format(tmp_path: Path) -> None:
    """The atomic writer produces the same file the library wrote, so no migration is needed."""
    entry = make_entry()
    actions = sample_actions(entry)

    old_remember = JsonDB[Entry](Entry, tmp_path / "old" / "remember.json", "id")
    old_log = JsonDB[Action](Action, tmp_path / "old" / "remember_log.json")
    new = DB(tmp_path / "new")
    old_remember.add(entry)
    new.remember.add(entry)
    for action in actions:
        old_log.add(action)
        new.log.add(action)

    for name in ["remember.json", "remember_log.json"]:
        assert read_bytes(tmp_path / "new" / name) == read_bytes(
            tmp_path / "old" / name
        )


def test_reopen_after_writes_restores_entries_and_log(tmp_path: Path) -> None:
    db = DB(tmp_path)
    entry = make_entry()
    other = make_entry("sudokudaily", server_id=None, run=None)
    db.remember.add(entry)
    db.remember.add(other)
    edited = dataclasses.replace(entry, run="return 42")
    db.remember.update(edited)
    db.remember.remove(other.id)
    for action in sample_actions(entry):
        db.log.add(action)

    reopened = DB(tmp_path)
    assert reopened.remember.all() == [edited]
    assert reopened.remember.get(entry.id) == edited
    # typed-json-db reloads the union-typed `action` field as a plain dict;
    # that is existing behavior, so compare the persisted values.
    log = reopened.log.all()
    assert [a.timestamp for a in log] == [a.timestamp for a in sample_actions(entry)]
    assert [a.action for a in log] == json.loads(
        json.dumps(
            [dataclasses.asdict(a.action) for a in sample_actions(entry)], default=str
        )
    )
    deleted: Any = log[2].action
    assert deleted["entry"]["run"] == entry.run
    assert deleted["entry"]["id"] == str(entry.id)
    assert temp_files(tmp_path) == []


def test_existing_file_mode_is_kept(tmp_path: Path) -> None:
    db = DB(tmp_path)
    path = tmp_path / "remember.json"
    os.chmod(path, 0o644)
    db.remember.add(make_entry())
    assert path.stat().st_mode & 0o777 == 0o644


def test_entries_are_frozen() -> None:
    entry = make_entry()
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.content = "x"  # pyright: ignore[reportAttributeAccessIssue]


# --- load failures ---


@pytest.mark.parametrize("contents", [b"", b'[{"id": "abc", "name": "x"', b"[1, 2]"])
def test_malformed_file_is_reported_and_preserved(
    tmp_path: Path, contents: bytes
) -> None:
    path = tmp_path / "remember.json"
    path.write_bytes(contents)
    with pytest.raises(DBLoadError) as info:
        DB(tmp_path)
    assert info.value.path == path
    assert read_bytes(path) == contents


# --- injected write failures ---

FAILURE_POINTS = [
    ("emilybot.atomic_json_db.tempfile.mkstemp", "mkstemp"),
    ("emilybot.atomic_json_db.os.fsync", "flush"),
    ("emilybot.atomic_json_db.os.replace", "replace"),
]


def mutations(db: DB, entry: Entry) -> list[Callable[[], object]]:
    return [
        lambda: db.remember.add(make_entry("new")),
        lambda: db.remember.update(dataclasses.replace(entry, run="return 1")),
        lambda: db.remember.remove(entry.id),
        lambda: db.log.add(sample_actions(entry)[0]),
    ]


@pytest.mark.parametrize("target,label", FAILURE_POINTS)
@pytest.mark.parametrize("which", range(4))
def test_failed_write_keeps_file_and_memory(
    tmp_path: Path, target: str, label: str, which: int
) -> None:
    db = DB(tmp_path)
    entry = make_entry()
    db.remember.add(entry)
    db.log.add(sample_actions(entry)[1])
    files = {p: read_bytes(p) for p in tmp_path.iterdir()}
    remember_before = db.remember.all()
    log_before = db.log.all()

    with patch(target, side_effect=OSError(f"injected {label} failure")):
        with pytest.raises(DBSaveError) as info:
            mutations(db, entry)[which]()

    assert info.value.replaced is False
    assert {p: read_bytes(p) for p in tmp_path.iterdir()} == files
    assert temp_files(tmp_path) == []
    assert db.remember.all() == remember_before
    assert db.remember.get(entry.id) == entry
    assert db.log.all() == log_before
    # The database stays usable after the failure.
    db.remember.update(dataclasses.replace(entry, content="later"))
    assert DB(tmp_path).remember.get(entry.id) == dataclasses.replace(
        entry, content="later"
    )


def test_failed_write_mid_file_keeps_old_contents(tmp_path: Path) -> None:
    db = DB(tmp_path)
    entry = make_entry()
    db.remember.add(entry)
    before = read_bytes(tmp_path / "remember.json")

    real_fdopen: Any = os.fdopen

    def partial_fdopen(fd: int, *args: Any, **kwargs: Any) -> Any:
        f: Any = real_fdopen(fd, *args, **kwargs)
        real_write: Callable[[str], int] = f.write

        def write(text: str) -> int:
            real_write(text[: len(text) // 2])
            raise OSError("injected: disk full")

        f.write = write
        return f

    with patch("emilybot.atomic_json_db.os.fdopen", side_effect=partial_fdopen):
        with pytest.raises(DBSaveError):
            db.remember.update(dataclasses.replace(entry, content="new"))

    assert read_bytes(tmp_path / "remember.json") == before
    assert temp_files(tmp_path) == []
    assert db.remember.get(entry.id) == entry


def test_unserializable_item_keeps_file_and_memory(tmp_path: Path) -> None:
    db = DB(tmp_path)
    entry = make_entry()
    db.remember.add(entry)
    before = read_bytes(tmp_path / "remember.json")
    bad = dataclasses.replace(entry, content=object())  # pyright: ignore[reportArgumentType]

    with pytest.raises(DBSaveError):
        db.remember.update(bad)

    assert read_bytes(tmp_path / "remember.json") == before
    assert db.remember.get(entry.id) == entry


def test_directory_sync_failure_reports_after_replacement(tmp_path: Path) -> None:
    db = DB(tmp_path)
    entry = make_entry()
    with patch(
        "emilybot.atomic_json_db._fsync_dir", side_effect=OSError("injected dir sync")
    ):
        with pytest.raises(DBSaveError) as info:
            db.remember.add(entry)
    assert info.value.replaced is True
    # The new file is in place, and memory matches it.
    assert db.remember.get(entry.id) == entry
    assert DB(tmp_path).remember.get(entry.id) == entry


# --- interrupted writer process ---

CHILD = textwrap.dedent(
    """
    import os, signal, sys, uuid
    from pathlib import Path
    import emilybot.atomic_json_db as m
    from emilybot.database import DB, Entry

    data_dir, stage = Path(sys.argv[1]), sys.argv[2]
    real_replace = os.replace

    def replace(src, dst):
        if stage == "before":
            os.kill(os.getpid(), signal.SIGKILL)
        real_replace(src, dst)
        if stage == "after":
            os.kill(os.getpid(), signal.SIGKILL)

    m.os.replace = replace
    db = DB(data_dir)
    db.remember.add(Entry(
        id=uuid.UUID(int=2), server_id=1, user_id=1, created_at="2025-09-02",
        name="second", content="x" * 200_000, promoted=False,
    ))
    """
)


@pytest.mark.parametrize("stage,expect_new", [("before", False), ("after", True)])
def test_killed_writer_leaves_complete_old_or_new_file(
    tmp_path: Path, stage: str, expect_new: bool
) -> None:
    db = DB(tmp_path)
    first = make_entry("first", id=uuid.UUID(int=1))
    db.remember.add(first)

    result = subprocess.run(
        [sys.executable, "-c", CHILD, str(tmp_path), stage], capture_output=True
    )
    assert result.returncode == -signal.SIGKILL, result.stderr.decode()

    data = json.loads((tmp_path / "remember.json").read_text())
    names = [item["name"] for item in data]
    assert names == (["first", "second"] if expect_new else ["first"])
    assert [e.name for e in DB(tmp_path).remember.all()] == names


# --- commands ---


def failing_save(db: DB, which: str) -> Any:
    target = db.remember if which == "remember" else db.log
    return patch.object(
        target,
        "_save",
        side_effect=DBSaveError(target.file_path, "injected", replaced=False),
    )


def command_cases(entry: Entry) -> list[tuple[str, Callable[[Any], Any]]]:
    return [
        ("add-append", lambda ctx: cmd_add(ctx, entry.name, content="more")),
        ("add-create", lambda ctx: cmd_add(ctx, "brand-new", content="hello")),
        ("edit", lambda ctx: cmd_edit(ctx, entry.name, new_content="replaced")),
        ("set", lambda ctx: cmd_set(ctx, f"{entry.name}.run", value="return 2")),
        ("promote", lambda ctx: cmd_promote(ctx, entry.name)),
        ("rm", lambda ctx: cmd_rm(ctx, entry.name)),
    ]


@pytest.mark.parametrize("case", range(6))
async def test_command_with_failed_alias_save_changes_nothing(
    make_ctx: MakeCtx, db: DB, case: int
) -> None:
    entry = make_entry()
    ctx = make_ctx(".cmd", entry)
    cast(Any, ctx).bot.just_command_prefix = "."
    name, run = command_cases(entry)[case]
    remember_file = read_bytes(db.remember.file_path)
    log_file = read_bytes(db.log.file_path)

    with failing_save(db, "remember"):
        with pytest.raises(DBSaveError):
            await run(ctx)

    assert isinstance(ctx.react_success, (MagicMock, AsyncMock))
    ctx.react_success.assert_not_called()
    assert db.remember.all() == [entry], name
    assert db.log.all() == [], name
    assert read_bytes(db.remember.file_path) == remember_file
    assert read_bytes(db.log.file_path) == log_file


@pytest.mark.parametrize("case", range(6))
async def test_command_with_failed_log_save_keeps_alias_change(
    make_ctx: MakeCtx, db: DB, case: int
) -> None:
    entry = make_entry()
    ctx = make_ctx(".cmd", entry)
    cast(Any, ctx).bot.just_command_prefix = "."
    name, run = command_cases(entry)[case]

    with failing_save(db, "log"):
        with pytest.raises(DBSaveError) as info:
            await run(ctx)

    assert isinstance(ctx.react_success, (MagicMock, AsyncMock))
    ctx.react_success.assert_not_called()
    assert db.log.all() == [], name
    assert db.remember.all() != [entry], name
    assert DB(db.remember.file_path.parent).remember.all() == db.remember.all()
    assert "history" in format_save_error(db, info.value)


async def test_successful_set_still_reacts(make_ctx: MakeCtx, db: DB) -> None:
    entry = make_entry()
    ctx = make_ctx(".set", entry)
    cast(Any, ctx).bot.just_command_prefix = "."
    await cmd_set(ctx, f"{entry.name}.run", value="```js\nreturn 3\n```")
    assert isinstance(ctx.react_success, (MagicMock, AsyncMock))
    ctx.react_success.assert_called_once()
    assert DB(db.remember.file_path.parent).remember.get(entry.id) == (
        dataclasses.replace(entry, run="return 3")
    )
    assert len(db.log.all()) == 1


def test_save_error_messages(tmp_path: Path) -> None:
    db = DB(tmp_path)
    remember_error = DBSaveError(db.remember.file_path, "x", replaced=False)
    assert format_save_error(db, remember_error).startswith("❌")
    assert "nothing was changed" in format_save_error(db, remember_error)
    unconfirmed = DBSaveError(db.remember.file_path, "x", replaced=True)
    assert "did not confirm" in format_save_error(db, unconfirmed)
    log_error = DBSaveError(db.log.file_path, "x", replaced=False)
    assert "history" in format_save_error(db, log_error)
