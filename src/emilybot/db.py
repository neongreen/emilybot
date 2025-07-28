from dataclasses import dataclass
from datetime import datetime
import uuid
from pathlib import Path
from typing import Optional, overload, Literal
import re
from typed_json_db import JsonDB


@dataclass
class Entry:
    """Rows in the `remember` table"""

    id: uuid.UUID
    """Unique ID"""

    server_id: Optional[int]
    """In which server was this entry added. `None` means it was in DMs with the bot"""

    user_id: int
    """Which user added this entry"""

    created_at: str  # ISO format datetime string
    """When"""

    name: str
    """E.g. "manual", will be normalized to lowercase"""

    content: str
    """E.g. link to that manual"""


@dataclass
class ActionEdit:
    """Represents an edit action on a remember entry."""

    kind: Literal["edit"]
    entry_id: uuid.UUID
    old_content: str
    new_content: str


@dataclass
class ActionCreate:
    """Represents a create action on a remember entry."""

    kind: Literal["create"]
    server_id: Optional[int]
    name: str
    content: str
    entry_id: uuid.UUID


@dataclass
class ActionDelete:
    """Represents a delete action on a remember entry."""

    kind: Literal["delete"]
    entry_id: uuid.UUID
    entry: Entry


@dataclass
class Action:
    timestamp: datetime
    user_id: int
    action: ActionCreate | ActionEdit | ActionDelete


class DB:
    def __init__(self) -> None:
        # Ensure data directory exists with proper permissions
        data_dir = Path("data")
        data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize JsonDB with type annotation
        self.remember = JsonDB[Entry](
            Entry, data_dir / "remember.json", primary_key="id"
        )
        self.log = JsonDB[Action](Action, data_dir / "remember_log.json")

    @overload
    def find_alias(
        self,
        alias: str | re.Pattern[str],
        *,
        server_id: int,
        user_id: int | None = None,
    ) -> list[Entry]: ...

    @overload
    def find_alias(
        self,
        alias: str | re.Pattern[str],
        *,
        user_id: int,
        server_id: int | None = None,
    ) -> list[Entry]: ...

    def find_alias(
        self,
        alias: str | re.Pattern[str],
        *,
        server_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> list[Entry]:
        """Find an alias in the database."""
        if server_id is not None:
            if isinstance(alias, str):
                results = self.remember.find(  # type: ignore
                    server_id=server_id, name=alias.lower()
                )
            else:
                results = self.remember.find(  # type: ignore
                    server_id=server_id
                )
                results = [entry for entry in results if alias.match(entry.name)]

        elif user_id is not None:
            if isinstance(alias, str):
                results = self.remember.find(  # type: ignore
                    user_id=user_id, server_id=None, name=alias.lower()
                )
            else:
                results = self.remember.find(  # type: ignore
                    user_id=user_id, server_id=None
                )
                results = [entry for entry in results if alias.match(entry.name)]
        else:
            raise ValueError("Either server_id or user_id must be provided")

        return results
