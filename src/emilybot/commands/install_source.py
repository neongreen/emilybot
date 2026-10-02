"""Credential-free, bounded downloads of installer Markdown."""

import asyncio
import zlib
import json
import re
from typing import cast
from urllib.parse import urljoin, urlsplit, urlunsplit

import aiohttp

MAX_BYTES = 256 * 1024
HOSTS = frozenset(
    {
        "api.github.com",
        "github.com",
        "raw.githubusercontent.com",
        "gist.github.com",
        "gist.githubusercontent.com",
        "cdn.discordapp.com",
        "media.discordapp.net",
    }
)


class InstallError(Exception):
    pass


def checked_url(url: str) -> str:
    try:
        parts = urlsplit(url)
        valid = (
            parts.scheme == "https"
            and parts.hostname in HOSTS
            and parts.port in (None, 443)
            and parts.username is None
            and parts.password is None
        )
        if parts.hostname == "api.github.com":
            valid = (
                valid
                and bool(re.fullmatch(r"/gists/[0-9a-fA-F]{1,64}", parts.path))
                and not parts.query
            )
    except ValueError:
        valid = False
    if not valid:
        raise InstallError(
            "Use an HTTPS GitHub file, raw Gist file, or Discord attachment link."
        )
    return url


def github_raw(url: str) -> str:
    checked_url(url)
    p = urlsplit(url)
    if p.hostname == "github.com":
        segments = p.path.split("/")
        if len(segments) < 6 or segments[3] != "blob":
            raise InstallError("Use a GitHub file link containing /blob/.")
        return urlunsplit(
            (
                "https",
                "raw.githubusercontent.com",
                "/".join(segments[:3] + segments[4:]),
                "",
                "",
            )
        )
    return url


def gist_api(url: str) -> str:
    """Resolve a Gist page via its bounded JSON metadata, without fetching HTML."""
    checked_url(url)
    parts = urlsplit(url)
    if parts.hostname != "gist.github.com" or parts.path.split("/")[3:4] == ["raw"]:
        return url
    match = re.fullmatch(r"/[^/]+/([0-9a-fA-F]{1,64})/?", parts.path)
    if not match:
        raise InstallError("Use a Gist file's raw link or a Gist page with one file.")
    return checked_url(f"https://api.github.com/gists/{match[1]}")


def gist_raw_url(body: bytes) -> str:
    try:
        metadata: object = json.loads(body)
    except (ValueError, UnicodeDecodeError) as e:
        raise InstallError(
            "The Gist returned invalid file metadata. Use the file's raw link."
        ) from e
    if not isinstance(metadata, dict):
        raise InstallError(
            "The Gist returned invalid file metadata. Use the file's raw link."
        )
    files = cast(dict[str, object], metadata).get("files")
    if not isinstance(files, dict) or len(cast(dict[str, object], files)) != 1:
        raise InstallError(
            "This Gist has no single unambiguous file. Use that file's raw link."
        )
    file = next(iter(cast(dict[str, object], files).values()))
    raw_url = (
        cast(dict[str, object], file).get("raw_url") if isinstance(file, dict) else None
    )
    if not isinstance(raw_url, str):
        raise InstallError("The Gist has no raw file link. Use the file's raw link.")
    # Always fetch raw bytes, even if the API includes (possibly truncated) content.
    return checked_url(raw_url)


async def _download(session: aiohttp.ClientSession, url: str) -> tuple[bytes, str]:
    for _ in range(6):
        url = gist_api(url)
        async with session.get(url, allow_redirects=False) as response:
            if response.status in (301, 302, 303, 307, 308):
                location = response.headers.get("Location")
                if not location:
                    raise InstallError(
                        "The source returned a redirect without a destination."
                    )
                url = checked_url(urljoin(url, location))
                continue
            if response.status != 200:
                raise InstallError(f"The source returned HTTP {response.status}.")
            chunks: list[bytes] = []
            size = 0
            wire_size = 0
            encoding = response.headers.get("Content-Encoding", "identity").lower()
            if encoding not in ("identity", "gzip", "deflate"):
                raise InstallError("The source uses an unsupported content encoding.")
            decoder = (
                zlib.decompressobj(31 if encoding == "gzip" else 15)
                if encoding != "identity"
                else None
            )
            async for chunk in response.content.iter_chunked(16384):
                wire_size += len(chunk)
                if wire_size > MAX_BYTES:
                    raise InstallError("The file exceeds 256 KiB.")
                if decoder:
                    chunk = decoder.decompress(chunk, MAX_BYTES - size + 1)
                size += len(chunk)
                if size > MAX_BYTES:
                    raise InstallError("The file exceeds 256 KiB.")
                chunks.append(chunk)
            if decoder and (not decoder.eof or decoder.unused_data):
                raise InstallError(
                    "The source returned an incomplete or concatenated compressed file."
                )
            return b"".join(chunks), url
    raise InstallError("The source returned too many redirects.")


async def fetch_source(url: str) -> bytes:
    url = github_raw(url)
    try:
        # One deadline covers redirects, Gist resolution, and the streamed decoded body.
        async with asyncio.timeout(10):
            async with aiohttp.ClientSession(
                trust_env=False,
                auto_decompress=False,
                headers={"Accept-Encoding": "identity"},
                cookie_jar=aiohttp.DummyCookieJar(),
            ) as session:
                body, final_url = await _download(session, url)
                if urlsplit(final_url).hostname == "api.github.com":
                    body, _ = await _download(session, gist_raw_url(body))
                return body
    except (TimeoutError, aiohttp.ClientError, UnicodeDecodeError, zlib.error) as e:
        raise InstallError(
            "Could not download the file within 10 seconds as UTF-8."
        ) from e
