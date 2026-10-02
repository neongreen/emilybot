"""Saved data (`this.store`) is refused when data/ would be lost on redeploy."""

import uuid
from collections.abc import Callable
from pathlib import Path

import pytest

from emilybot.conftest import MakeCtx
from emilybot.database import DB, Entry
from emilybot.execute.run_code import run_code
from emilybot import persistence
from emilybot.persistence import (
    Mount,
    covering_mount,
    ephemeral_reason,
    parse_mountinfo,
)
from emilybot.store import StoreDB, StoreTransaction, StoreUnavailable

FIXTURES = Path(__file__).parent / "fixtures" / "mountinfo"
APP_DATA = Path("/app/data")


@pytest.mark.parametrize(
    ("fixture", "path", "persistent"),
    [
        ("container-data-dir-bind.txt", APP_DATA, True),  # -v hostdir:/app/data
        (
            "container-file-bind.txt",
            APP_DATA,
            False,
        ),  # -v hostfile:/app/data/remember.json
        ("container-tmpfs-data.txt", APP_DATA, False),
        ("dev-ext4.txt", Path("/home/me/emilybot/data"), True),
        ("dev-ext4.txt", Path("/tmp/emilybot/data"), False),  # tmpfs /tmp
        ("spaces.txt", Path("/app/my data"), True),  # escaped mount point
        # The store file itself: a single-file bind of store.json is persistent
        ("container-file-binds-with-store.txt", APP_DATA / "store.json", True),
        ("container-file-bind.txt", APP_DATA / "store.json", False),
        ("container-data-dir-bind.txt", APP_DATA / "store.json", True),
        # Mount paths that are not UTF-8 do not stop the check
        ("non-utf8.txt", APP_DATA / "store.json", True),
    ],
)
def test_ephemeral_reason(fixture: str, path: Path, persistent: bool):
    reason = ephemeral_reason(path, FIXTURES / fixture)
    assert (reason is None) == persistent
    if reason:
        assert "not on persistent storage" in reason


def test_unreadable_mountinfo_allows(tmp_path: Path):
    assert ephemeral_reason(APP_DATA, tmp_path / "missing") is None


def test_any_error_in_the_check_allows(monkeypatch: pytest.MonkeyPatch):
    def broken(text: str) -> list[Mount]:
        raise RuntimeError("unexpected")

    monkeypatch.setattr(persistence, "parse_mountinfo", broken)
    path = APP_DATA / "store.json"
    assert ephemeral_reason(path, FIXTURES / "container-file-bind.txt") is None
    assert (
        StoreDB(path, mountinfo=FIXTURES / "container-file-bind.txt").unavailable
        is None
    )


def test_non_utf8_mountinfo_does_not_stop_startup():
    assert b"\xff" in (FIXTURES / "non-utf8.txt").read_bytes()
    store = StoreDB(APP_DATA / "store.json", mountinfo=FIXTURES / "non-utf8.txt")
    assert store.unavailable is None


def test_longest_prefix_and_later_mounts_win():
    mounts = parse_mountinfo(
        "1 0 0:1 / / rw - ext4 /dev/a rw\n"
        "2 1 0:2 / /app rw - tmpfs tmpfs rw\n"
        "3 1 0:3 / /app/data rw - ext4 /dev/b rw\n"
        "4 1 0:4 / /app/database rw - tmpfs tmpfs rw\n"
        "5 1 0:5 / /app/data rw - overlay overlay rw\n"
    )
    mount = covering_mount(Path("/app/data"), mounts)
    assert mount is not None and mount.fstype == "overlay"  # mounted on top
    mount = covering_mount(Path("/app/datastore"), mounts)
    assert (
        mount is not None and mount.mount_point == "/app"
    )  # not a path prefix of /app/data


def test_store_refuses_ephemeral_storage():
    store = StoreDB(
        APP_DATA / "store.json", mountinfo=FIXTURES / "container-file-bind.txt"
    )
    assert store.unavailable is not None
    assert "not on persistent storage" in store.unavailable
    access = store.access(1)
    assert (
        access.unavailable == store.unavailable
    )  # passed to the executor as --storesError
    alias = str(uuid.uuid4())
    with pytest.raises(StoreUnavailable):
        store.commit(
            1, StoreTransaction({alias: 0}, {alias: {"k": {"v": 1}}}), lambda _: True
        )


def test_store_allows_a_store_json_file_bind():
    fixture = FIXTURES / "container-file-binds-with-store.txt"
    assert StoreDB(APP_DATA / "store.json", mountinfo=fixture).unavailable is None


def test_store_allows_directory_bind():
    store = StoreDB(
        APP_DATA / "store.json", mountinfo=FIXTURES / "container-data-dir-bind.txt"
    )
    assert store.unavailable is None


async def test_commands_get_a_clear_error_and_nothing_else_changes(
    make_ctx: MakeCtx, db: DB, entry_factory: Callable[..., Entry]
):
    db.store = StoreDB(
        APP_DATA / "store.json", mountinfo=FIXTURES / "container-file-bind.txt"
    )
    run = "this.store.set('n', 1); print('saved')"
    db.remember.add(entry_factory(name="counter", server_id=12345, run=run))
    db.remember.add(entry_factory(name="plain", server_id=12345, run="print('fine')"))
    ok, output, _ = await run_code(make_ctx(".counter"), code="$counter()")
    assert not ok
    assert (
        "this.store is unavailable: this deployment's data folder is not on persistent storage"
        in output
    )
    assert await run_code(make_ctx(".plain"), code="$plain()") == (True, "fine", None)
