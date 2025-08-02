"""Service for querying available commands from the database."""

import re
from typing import List, Optional
from emilybot.database import DB, Entry
from emilybot.execute.javascript_executor import CommandData


class CommandQueryService:
    """Service for querying available commands for a user/server context."""

    def __init__(self, db: DB):
        """Initialize the command query service.

        Args:
            db: Database instance to query commands from
        """
        self.db = db

    def get_available_commands(
        self, user_id: int, server_id: Optional[int]
    ) -> List[CommandData]:
        """Get all available commands for a user/server context.

        Args:
            user_id: ID of the user requesting commands
            server_id: ID of the server, or None for DM context

        Returns:
            List of CommandData objects
        """
        # Query all entries for the user/server context
        entries = self._query_entries(user_id, server_id)

        # Convert entries to command list
        commands: List[CommandData] = []
        for entry in entries:
            commands.append(
                {
                    "name": entry.name,
                    "content": entry.content,
                    "run": entry.run,
                }
            )

        return commands

    def _query_entries(self, user_id: int, server_id: Optional[int]) -> list[Entry]:
        """Query database entries for the given user/server context.

        Args:
            user_id: ID of the user requesting commands
            server_id: ID of the server, or None for DM context

        Returns:
            List of Entry objects matching the context
        """
        # Use regex to match all entries (equivalent to find_alias with .* pattern)
        all_entries_pattern = re.compile(".*")

        if server_id is not None:
            # Server context: find entries for this server, any user is ok
            return self.db.find_alias(all_entries_pattern, server_id=server_id)
        else:
            # DM context: find entries for this user in DM (server_id=None)
            return self.db.find_alias(all_entries_pattern, user_id=user_id)
