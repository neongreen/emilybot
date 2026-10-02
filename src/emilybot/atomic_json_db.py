"""Crash-safe saves for `typed_json_db.JsonDB`.

The pinned typed-json-db (0.2.2) saves by opening the destination with mode "w"
and dumping JSON into it. A crash or a failed write in the middle leaves a
truncated file, and the in-memory list is changed before the save runs, so a
failed save still becomes the in-memory truth.

`AtomicJsonDB` keeps the library's load path, serialization format and query
methods, and replaces every write:

- add/update/remove build a candidate list and publish it in memory only after
  the file write succeeds;
- the candidate is written to a temporary file in the same directory, flushed
  and fsynced, then moved over the destination with `os.replace`, and the
  directory is fsynced so the rename itself is durable;
- writers are serialized with a lock;
- if the destination cannot be replaced by rename (for example a single-file
  bind mount, where `os.replace` fails with EBUSY or EXDEV) or no temp file can
  be created next to it, the fully serialized bytes are written into the
  destination in place and fsynced. That is the old non-atomic behavior, so it
  is never worse than before; a warning is logged once per file;
- a file that exists but cannot be parsed raises `DBLoadError` and is never
  overwritten.

Enforcement limit: each file is replaced atomically, but two files (for
example the alias table and its history log) are not one transaction. A crash
or a failure between two saves can leave one file updated and the other not.
"""

import errno
import json
import logging
import os
import tempfile
import threading
from dataclasses import asdict
from pathlib import Path
from collections.abc import Callable
from typing import Any, List, Literal, Optional, Type, TypeVar

from typed_json_db import JsonDB, JsonDBException, JsonSerializer

T = TypeVar("T")

FileState = Literal["old", "new", "unknown"]

# os.replace errors that mean "this destination cannot be swapped by rename",
# as opposed to a failed disk or a full filesystem.
_REPLACE_UNSUPPORTED = {errno.EBUSY, errno.EXDEV, errno.EPERM, errno.EINVAL}
# mkstemp errors that mean "no temp file can be created in this directory",
# while the destination file itself may still be writable.
_TEMP_UNSUPPORTED = {errno.EACCES, errno.EPERM, errno.EROFS}

# Destinations that fell back to in-place writes. Each is warned about once.
_in_place_paths: set[Path] = set()


class DBLoadError(JsonDBException):
    """A database file exists but could not be read. The file was left untouched."""

    def __init__(self, path: Path, reason: str) -> None:
        super().__init__(
            f"Could not load {path}: {reason}. The file was left as it is; "
            "repair or restore it before starting the bot."
        )
        self.path = path


class DBSaveError(JsonDBException):
    """Writing a database file failed.

    `file_state` says what the destination holds afterwards:
    - "old": the previous complete contents; memory was not changed.
    - "new": the new contents were moved into place, but making the directory
      entry durable failed; memory matches the new file.
    - "unknown": an in-place write failed partway; memory was not changed, and
      the next successful save rewrites the whole file from memory.
    """

    def __init__(self, path: Path, reason: str, *, file_state: FileState) -> None:
        super().__init__(f"Could not save {path}: {reason}")
        self.path = path
        self.file_state: FileState = file_state


def _serialize(items: List[Any]) -> str:
    # Same call shape as typed_json_db's `_save`, so the bytes on disk match the
    # previous format exactly.
    return json.dumps(
        [asdict(item) for item in items], indent=2, default=JsonSerializer.default
    )


def _fsync_dir(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _new_file_mode(destination: Path) -> int:
    try:
        return destination.stat().st_mode & 0o7777
    except FileNotFoundError:
        umask = os.umask(0)
        os.umask(umask)
        return 0o666 & ~umask


def _write_in_place(destination: Path, data: bytes) -> None:
    """Overwrite `destination` with `data` without a rename. Not atomic.

    The bytes are fully serialized before the file is touched; they are written
    over the old contents, then the file is truncated to their length and
    fsynced. Raises `DBSaveError`.
    """
    try:
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT, 0o666)
    except OSError as e:
        raise DBSaveError(destination, str(e), file_state="old") from e
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.ftruncate(fd, len(data))
        os.fsync(fd)
    except OSError as e:
        raise DBSaveError(destination, str(e), file_state="unknown") from e
    finally:
        os.close(fd)


def _fall_back_to_in_place(destination: Path, error: OSError) -> None:
    if destination not in _in_place_paths:
        _in_place_paths.add(destination)
        logging.warning(
            "Cannot replace %s atomically (%s); writing it in place from now on. "
            "Saves to this file are not crash-safe.",
            destination,
            error,
        )


def _remove_temp(tmp_path: Path) -> None:
    try:
        tmp_path.unlink()
    except FileNotFoundError:
        pass


def write_json_atomic(destination: Path, text: str) -> None:
    """Replace `destination` with `text` so readers see either the old or the new file.

    Falls back to an in-place write when the destination cannot be replaced by
    rename (see module docstring). Raises `DBSaveError`.
    """
    data = text.encode("utf-8")
    if destination in _in_place_paths:
        _write_in_place(destination, data)
        return
    directory = destination.parent
    try:
        fd, tmp_name = tempfile.mkstemp(
            dir=directory, prefix=f".{destination.name}.", suffix=".tmp"
        )
    except OSError as e:
        if e.errno in _TEMP_UNSUPPORTED and destination.exists():
            _fall_back_to_in_place(destination, e)
            _write_in_place(destination, data)
            return
        raise DBSaveError(destination, str(e), file_state="old") from e
    tmp_path = Path(tmp_name)
    replace_error: Optional[OSError] = None
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp_path, _new_file_mode(destination))
        try:
            os.replace(tmp_path, destination)
        except OSError as e:
            if e.errno not in _REPLACE_UNSUPPORTED:
                raise
            replace_error = e
    except BaseException as e:
        _remove_temp(tmp_path)
        if isinstance(e, Exception):
            raise DBSaveError(destination, str(e), file_state="old") from e
        raise
    if replace_error is not None:
        _remove_temp(tmp_path)
        _fall_back_to_in_place(destination, replace_error)
        _write_in_place(destination, data)
        return
    try:
        _fsync_dir(directory)
    except OSError as e:
        raise DBSaveError(destination, str(e), file_state="new") from e


class AtomicJsonDB(JsonDB[T]):
    """`JsonDB` whose writes are atomic and publish to memory only after success."""

    def __init__(
        self, data_class: Type[T], file_path: Path, primary_key: Optional[str] = None
    ):
        self._write_lock = threading.RLock()
        super().__init__(data_class, file_path, primary_key)

    def _load(self) -> None:
        try:
            super()._load()
        except DBSaveError:
            raise
        except Exception as e:
            raise DBLoadError(self.file_path, str(e)) from e

    def _save(self, items: List[T]) -> None:
        try:
            text = _serialize(items)
        except (TypeError, ValueError, OverflowError) as e:
            raise DBSaveError(self.file_path, str(e), file_state="old") from e
        write_json_atomic(self.file_path, text)

    def _commit(self, candidate: List[T]) -> None:
        """Write `candidate`, then make it the in-memory state."""
        try:
            self._save(candidate)
        except DBSaveError as e:
            if e.file_state == "new":
                self._publish(candidate)
            raise
        self._publish(candidate)

    def _publish(self, candidate: List[T]) -> None:
        self.data = candidate
        self._rebuild_primary_key_index()

    def _key(self, item: T) -> Any:
        assert self.primary_key is not None
        if not hasattr(item, self.primary_key):
            raise JsonDBException(f"Item must have a '{self.primary_key}' attribute")
        return getattr(item, self.primary_key)

    def _check_type(self, item: T) -> None:
        if not isinstance(item, self.data_class):
            raise JsonDBException(
                f"Item must be of type {self.data_class.__name__}, got {type(item).__name__}"
            )

    def batch(self, transform: Callable[[List[T]], List[T]]) -> None:
        """Re-check and transform current rows under the ordinary writer lock.

        The callback must be synchronous. An exception leaves the rows untouched.
        """
        with self._write_lock:
            candidate = transform(list(self.data))
            for item in candidate:
                self._check_type(item)
            if self.primary_key is not None:
                keys = [self._key(item) for item in candidate]
                if len(set(keys)) != len(keys):
                    raise JsonDBException("Duplicate primary key in batch")
            self._commit(candidate)

    def save(self) -> None:
        with self._write_lock:
            self._commit(list(self.data))

    def add(self, item: T) -> T:
        self._check_type(item)
        with self._write_lock:
            if self.primary_key is not None and self.get(self._key(item)) is not None:
                raise JsonDBException(
                    f"Item with {self.primary_key}='{self._key(item)}' already exists"
                )
            self._commit([*self.data, item])
        return item

    def update(self, item: T) -> T:
        if self.primary_key is None:
            raise JsonDBException(
                "Cannot use update() without a primary key configured"
            )
        self._check_type(item)
        with self._write_lock:
            key = self._key(item)
            index = self._primary_key_index.get(key)
            if index is None:
                raise JsonDBException(f"Item with {self.primary_key}='{key}' not found")
            candidate = list(self.data)
            candidate[index] = item
            self._commit(candidate)
        return item

    def remove(self, key_value: Any) -> bool:
        if self.primary_key is None:
            raise JsonDBException(
                "Cannot use remove() without a primary key configured"
            )
        with self._write_lock:
            index = self._primary_key_index.get(key_value)
            if index is None:
                return False
            candidate = [*self.data[:index], *self.data[index + 1 :]]
            self._commit(candidate)
        return True
