"""Context data classes for JavaScript execution."""

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class CtxUser:
    id: str  # instead of 'int' because in JS it overflows 'number'

    handle: str
    """Discord username, e.g. `availablegreen`"""

    name: str
    """Display name as shown in the server"""

    global_name: str | None
    """Global display name as shown in the user's profile. Not sure when it might be None."""

    avatar_url: str
    """User's avatar URL as shown in the server"""

    def as_json(self) -> dict[str, Any]:
        return asdict(self)


def create_test_user(**kwargs: Any) -> CtxUser:
    return CtxUser(
        **{
            "id": "1",
            "handle": "Test user",
            "name": "Test user",
            "global_name": "Test user",
            "avatar_url": "https://cdn.discordapp.com/avatars/1/1234567890.png",
            **kwargs,
        },
    )


@dataclass
class CtxServer:
    id: str

    def as_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CtxReplyTo:
    user: CtxUser
    text: str

    def as_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CtxMessage:
    text: str


@dataclass
class Context:
    message: CtxMessage
    reply_to: CtxReplyTo | None
    user: CtxUser
    server: CtxServer | None

    def as_json(self) -> dict[str, Any]:
        """Serialize Context to JSON string."""
        return {
            "message": asdict(self.message),
            "reply_to": self.reply_to.as_json() if self.reply_to else None,
            "user": asdict(self.user),
            "server": asdict(self.server) if self.server else None,
        }


def run_code_context(code: str) -> Context:
    return Context(
        message=CtxMessage(text=f".run {code}"),
        reply_to=None,
        user=CtxUser(
            id="1",
            handle="Test user",
            name="Test user",
            global_name="Test user",
            avatar_url="https://cdn.discordapp.com/avatars/1/1234567890.png",
        ),
        server=None,
    )
