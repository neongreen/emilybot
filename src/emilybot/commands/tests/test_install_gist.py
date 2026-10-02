"""Gist pages resolve through bounded public API metadata, never page HTML."""

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

from emilybot.commands import install_source
from emilybot.commands.install_source import (
    InstallError,
    MAX_BYTES,
    checked_url,
    fetch_source,
)
from emilybot.commands.tests.test_install import GAME, Response, Session

PAGE = "https://gist.github.com/octocat/9257657"
API = "https://api.github.com/gists/9257657"
RAW = "https://gist.githubusercontent.com/octocat/9257657/raw/game.md"


def metadata(files: Any) -> Response:
    return Response(json.dumps({"files": files}).encode())


@pytest.mark.parametrize("truncated", [False, True])
async def test_single_file_gist(
    monkeypatch: pytest.MonkeyPatch, truncated: bool
) -> None:
    session = Session(
        [
            metadata(
                {
                    "game.md": {
                        "raw_url": RAW,
                        "truncated": truncated,
                        "content": "never trust inline content",
                    }
                }
            ),
            Response(GAME),
        ]
    )
    factory = MagicMock(return_value=session)
    monkeypatch.setattr(install_source.aiohttp, "ClientSession", factory)
    assert await fetch_source(PAGE) == GAME
    assert session.urls == [API, RAW]
    session.replies = [metadata({"game.md": {"raw_url": RAW}}), Response(GAME)]
    assert await fetch_source("https://gist.github.com/rawuser/9257657") == GAME
    assert factory.call_args.kwargs["trust_env"] is False
    assert "Authorization" not in factory.call_args.kwargs["headers"]


@pytest.mark.parametrize(
    "files", [{}, {"one.md": {"raw_url": RAW}, "two.md": {"raw_url": RAW}}]
)
async def test_ambiguous_gist(monkeypatch: pytest.MonkeyPatch, files: Any) -> None:
    session = Session([metadata(files)])
    monkeypatch.setattr(
        install_source.aiohttp, "ClientSession", MagicMock(return_value=session)
    )
    with pytest.raises(InstallError, match="raw link"):
        await fetch_source(PAGE)
    assert session.urls == [API]


@pytest.mark.parametrize(
    "url",
    [
        "https://api.github.com/user",
        "https://api.github.com/gists",
        "https://api.github.com/gists/id",
        API + "/comments",
        API + "/",
        API + "?page=2",
        "http://api.github.com/gists/9257657",
        "https://api.github.com:8443/gists/9257657",
    ],
)
def test_api_path_allowlist(url: str) -> None:
    with pytest.raises(InstallError):
        checked_url(url)
    assert checked_url(API) == API


@pytest.mark.parametrize(
    "response",
    [
        Response(b"not JSON"),
        metadata({"game.md": {"content": "no raw URL"}}),
        metadata({"game.md": {"raw_url": "https://evil.test/game.md"}}),
        Response(b"x" * (MAX_BYTES + 1)),
        Response(status=302, location="https://api.github.com/user"),
    ],
)
async def test_invalid_metadata(
    monkeypatch: pytest.MonkeyPatch, response: Response
) -> None:
    session = Session([response])
    monkeypatch.setattr(
        install_source.aiohttp, "ClientSession", MagicMock(return_value=session)
    )
    with pytest.raises(InstallError):
        await fetch_source(PAGE)
    assert session.urls == [API]


async def test_raw_file_cap_and_redirect_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Session(
        [
            Response(status=302, location=PAGE),
            metadata({"game.md": {"raw_url": RAW}}),
            Response(b"x" * (MAX_BYTES + 1)),
        ]
    )
    monkeypatch.setattr(
        install_source.aiohttp, "ClientSession", MagicMock(return_value=session)
    )
    with pytest.raises(InstallError, match="256 KiB"):
        await fetch_source("https://raw.githubusercontent.com/redirect")
    assert session.urls == ["https://raw.githubusercontent.com/redirect", API, RAW]
