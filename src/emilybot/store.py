"""Per-alias persistent stores (`this.store` in a stored command's code).

A store belongs to one alias record, keyed by the alias's Entry UUID, within the
alias's server. All stores live in one file, `data/store.json`:

    {"stores": {"<entry uuid>": {"server_id": "123", "version": 4, "data": {...}}}}

A run reads the file itself, lazily, on first `this.store` use (see
storeLoaderFromFile in js-executor/main.ts), and returns its buffered writes; `commit`
applies them only if every store the run read is still at the version it read and
the owning aliases still exist with the same code. Everything a commit touches is
written in one atomic save (see `emilybot.atomic_json_db.write_json_atomic`).

Stores are disabled when the file's directory is on a container's writable
layer or tmpfs (see emilybot.persistence), so saved data is never silently lost
on redeploy.

A missing or empty file is an empty set of stores. A file that cannot be parsed is left as
it is and logged; store features then fail with a clear message, and everything
else keeps working.
"""

import json
import logging
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TypedDict, cast

from emilybot.atomic_json_db import DBSaveError, write_json_atomic
from emilybot import persistence
from emilybot.persistence import ephemeral_reason

STORE_LIMIT_BYTES = 64 * 1024
STORE_MAX_KEYS = 256
KEY_MAX_LENGTH = 100
SERVER_LIMIT_BYTES = 2 * 1024 * 1024

JSONValue = Any
"""null, boolean, finite number, string, list, or str-keyed dict of these"""


class StoreWrite(TypedDict, total=False):
    """One buffered write: `{"v": value}` sets the key, `{"d": true}` deletes it."""

    v: JSONValue
    d: Literal[True]


@dataclass(frozen=True)
class StoreTransaction:
    """What a successful run did to stores."""

    reads: dict[str, int]
    """Alias id → store version the run saw on first use"""
    writes: dict[str, dict[str, StoreWrite]]
    """Alias id → key → write"""


@dataclass(frozen=True)
class StoreAccess:
    """What the executor needs to give a run `this.store`."""

    server_id: int
    path: Path
    """store.json; read by the executor only if the run uses `this.store`"""
    unavailable: str | None = None
    """Why stores cannot be used, if they cannot"""


@dataclass(frozen=True)
class StoreRecord:
    server_id: int
    version: int
    data: dict[str, JSONValue]


class StoreUnavailable(Exception):
    """store.json exists but could not be read; stores cannot be used until it is repaired."""


class StoreConflict(Exception):
    """A store the run read changed, or its alias was deleted or its code changed, during the run."""


class StoreQuotaExceeded(Exception):
    """The run's writes would exceed a store or server limit. The message is user-facing."""


def json_size(value: JSONValue) -> int:
    """Size in UTF-8 bytes of the compact JSON encoding."""
    return len(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )


class StoreDB:
    def __init__(self, path: Path, *, mountinfo: Path | None = None) -> None:
        self.path = path
        self._stores: dict[str, StoreRecord] = {}
        self._unavailable: str | None = None
        # Saved data on a container's writable layer would vanish on the next
        # redeploy; refuse it rather than lose it silently.
        ephemeral = ephemeral_reason(path.parent, mountinfo or persistence.MOUNTINFO)
        if ephemeral:
            self._unavailable = ephemeral
            logging.error(f"Stores are disabled: {ephemeral} ({path.parent})")
            return
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return
        except OSError as e:
            self._fail_load(str(e))
            return
        if not text.strip():
            return  # Empty, e.g. a freshly created file mount: no stores yet
        try:
            raw = cast(dict[str, Any], json.loads(text))
            for alias_id, rec in cast(dict[str, Any], raw["stores"]).items():
                self._stores[str(uuid.UUID(alias_id))] = StoreRecord(
                    server_id=int(rec["server_id"]),
                    version=int(rec["version"]),
                    data=dict(rec["data"]),
                )
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            self._stores = {}
            self._fail_load(f"{type(e).__name__}: {e}")

    def _fail_load(self, reason: str) -> None:
        self._unavailable = (
            f"the bot could not read its stored data ({self.path.name}); "
            "an administrator needs to repair the file"
        )
        logging.error(
            f"Could not load {self.path}: {reason}. The file was left as it is; "
            "stores are unavailable until it is repaired."
        )

    @property
    def unavailable(self) -> str | None:
        """Why stores cannot be used, or None if they can."""
        return self._unavailable

    def get(self, alias_id: uuid.UUID) -> StoreRecord | None:
        return self._stores.get(str(alias_id))

    def access(self, server_id: int) -> StoreAccess:
        return StoreAccess(server_id, self.path.resolve(), self._unavailable)

    def commit(
        self,
        server_id: int,
        txn: StoreTransaction,
        alias_unchanged: Callable[[uuid.UUID], bool],
    ) -> None:
        """Apply a run's writes, all or nothing.

        `alias_unchanged(id)` says whether the alias still exists in this server
        with the code the run used.

        Raises:
            StoreConflict: a touched store or alias changed during the run.
            StoreQuotaExceeded: the writes would exceed a limit.
            StoreUnavailable: store.json could not be read at startup.
            DBSaveError: writing store.json failed. With file_state "old" or
                "unknown" nothing was applied.
        """
        if not any(txn.writes.values()):
            return  # Nothing to save; a read-only run never conflicts
        if self._unavailable:
            raise StoreUnavailable(self._unavailable)

        for alias_id, version in txn.reads.items():
            current = self._stores.get(alias_id)
            if (current.version if current else 0) != version:
                raise StoreConflict()
            if current is not None and current.server_id != server_id:
                raise StoreConflict()
            try:
                parsed_id = uuid.UUID(alias_id)
            except ValueError:
                raise StoreConflict() from None
            if not alias_unchanged(parsed_id):
                raise StoreConflict()

        candidate = dict(self._stores)
        for alias_id, writes in txn.writes.items():
            if not writes:
                continue
            if alias_id not in txn.reads:
                raise StoreConflict()  # Writes always follow a load; refuse anything else
            old = candidate.get(alias_id)
            data = dict(old.data) if old else {}
            for key, write in writes.items():
                if write.get("d"):
                    data.pop(key, None)
                else:
                    data[key] = write.get("v")
            check_store_limits(data)
            candidate[alias_id] = StoreRecord(
                server_id=server_id,
                version=(old.version if old else 0) + 1,
                data=data,
            )

        server_total = sum(
            json_size(rec.data)
            for rec in candidate.values()
            if rec.server_id == server_id
        )
        if server_total > SERVER_LIMIT_BYTES:
            raise StoreQuotaExceeded(
                f"This server's stored data would be {server_total} bytes, over the "
                f"{SERVER_LIMIT_BYTES // 1024 // 1024} MiB limit. Nothing was saved."
            )
        self._save(candidate)

    def delete(self, alias_id: uuid.UUID) -> StoreRecord | None:
        """Delete an alias's store and return what it held, or None if it had none."""
        old = self._stores.get(str(alias_id))
        if old is None:
            return None
        if self._unavailable:
            raise StoreUnavailable(self._unavailable)
        candidate = dict(self._stores)
        del candidate[str(alias_id)]
        self._save(candidate)
        return old

    def _save(self, candidate: dict[str, StoreRecord]) -> None:
        text = json.dumps(
            {
                "stores": {
                    alias_id: {
                        # A string: Discord ids do not fit in a JavaScript number
                        "server_id": str(rec.server_id),
                        "version": rec.version,
                        "data": rec.data,
                    }
                    for alias_id, rec in candidate.items()
                }
            },
            ensure_ascii=False,
        )
        try:
            write_json_atomic(self.path, text)
        except DBSaveError as e:
            if e.file_state == "new":
                self._stores = (
                    candidate  # On disk already; only the directory fsync failed
                )
            raise
        self._stores = candidate


def check_store_limits(data: Mapping[str, JSONValue]) -> None:
    if len(data) > STORE_MAX_KEYS:
        raise StoreQuotaExceeded(
            f"A store can hold at most {STORE_MAX_KEYS} keys; this run would leave "
            f"{len(data)}. Nothing was saved."
        )
    for key in data:
        if not key or len(key) > KEY_MAX_LENGTH:
            raise StoreQuotaExceeded(
                f"Store keys must be 1 to {KEY_MAX_LENGTH} characters. Nothing was saved."
            )
    size = json_size(dict(data))
    if size > STORE_LIMIT_BYTES:
        raise StoreQuotaExceeded(
            f"A store can hold at most {STORE_LIMIT_BYTES // 1024} KiB; this run would "
            f"leave {size} bytes. Nothing was saved."
        )
