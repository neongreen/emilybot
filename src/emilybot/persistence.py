"""Detect whether a directory is on storage that survives a redeploy.

In a container, a directory that no volume or bind mount covers lives in the
container's writable layer (overlay) and is lost when the container is
replaced. Reading /proc/self/mountinfo tells which mount holds a directory.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

MOUNTINFO = Path("/proc/self/mountinfo")
EPHEMERAL_FSTYPES = {"overlay", "tmpfs"}


@dataclass(frozen=True)
class Mount:
    mount_point: str
    fstype: str
    source: str


def _unescape(field: str) -> str:
    # mountinfo escapes space, tab, newline and backslash as \\ooo octal
    out: list[str] = []
    i = 0
    while i < len(field):
        if (
            field[i] == "\\"
            and field[i + 1 : i + 4].isdigit()
            and len(field[i + 1 : i + 4]) == 3
        ):
            out.append(chr(int(field[i + 1 : i + 4], 8)))
            i += 4
        else:
            out.append(field[i])
            i += 1
    return "".join(out)


def parse_mountinfo(text: str) -> list[Mount]:
    """Mounts in file order (later entries are mounted on top of earlier ones)."""
    mounts: list[Mount] = []
    for line in text.splitlines():
        fields = line.split()
        if "-" not in fields or len(fields) < 5:
            continue
        sep = fields.index("-")
        if len(fields) < sep + 3:
            continue
        mounts.append(
            Mount(
                mount_point=_unescape(fields[4]),
                fstype=fields[sep + 1],
                source=_unescape(fields[sep + 2]),
            )
        )
    return mounts


def covering_mount(directory: Path, mounts: list[Mount]) -> Mount | None:
    """The mount that holds `directory`: the longest mount point that is a prefix of it."""
    path = str(directory)
    best: Mount | None = None
    for mount in mounts:
        mp = mount.mount_point
        covers = mp == "/" or path == mp or path.startswith(mp.rstrip("/") + "/")
        # `>=`: a later mount on the same point hides the earlier one
        if covers and (best is None or len(mp) >= len(best.mount_point)):
            best = mount
    return best


def ephemeral_reason(directory: Path, mountinfo: Path = MOUNTINFO) -> str | None:
    """Why `directory` would be lost on redeploy, or None if it looks persistent.

    Allows (returns None) when mountinfo cannot be read, e.g. not on Linux.
    """
    try:
        mounts = parse_mountinfo(mountinfo.read_text(encoding="utf-8"))
    except OSError as e:
        logging.info(
            f"Cannot read {mountinfo} ({e}); assuming {directory} is persistent"
        )
        return None
    directory = directory.resolve()
    mount = covering_mount(directory, mounts)
    if mount is None:
        logging.info(
            f"No mount covers {directory} in {mountinfo}; assuming it is persistent"
        )
        return None
    persistent = mount.fstype not in EPHEMERAL_FSTYPES
    logging.info(
        f"{directory} is on mount {mount.mount_point} "
        f"(fstype {mount.fstype}, source {mount.source}): "
        f"{'persistent' if persistent else 'NOT persistent'}"
    )
    if persistent:
        return None
    return (
        "this deployment's data folder is not on persistent storage, "
        "so saved data would be lost on redeploy"
    )
