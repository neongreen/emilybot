from dataclasses import dataclass
from typing import List


@dataclass
class Command:
    """Represents a parsed command"""

    cmd: str
    args: List[str]


@dataclass
class JS:
    """Represents JavaScript code to execute"""

    code: str


@dataclass
class ListChildren:
    """Represents a request to list children of a command"""

    parent: str
