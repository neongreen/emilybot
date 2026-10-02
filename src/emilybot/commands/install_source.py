"""Credential-free, bounded downloads of installer Markdown."""

import asyncio
import zlib
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit

import aiohttp

MAX_BYTES = 256 * 1024
HOSTS = frozenset(
    {
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


class GistLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value and "/raw/" in value:
                    self.links.add(value)


async def _download(session: aiohttp.ClientSession, url: str) -> tuple[bytes, str]:
    for _ in range(6):
        checked_url(url)
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
                if (
                    urlsplit(final_url).hostname == "gist.github.com"
                    and "/raw" not in urlsplit(final_url).path
                ):
                    parser = GistLinks()
                    parser.feed(body.decode("utf-8"))
                    links = {
                        checked_url(urljoin(final_url, link)) for link in parser.links
                    }
                    if len(links) != 1:
                        raise InstallError(
                            "This Gist has no single unambiguous file. Use that file's raw link."
                        )
                    body, _ = await _download(session, links.pop())
                return body
    except (TimeoutError, aiohttp.ClientError, UnicodeDecodeError, zlib.error) as e:
        raise InstallError(
            "Could not download the file within 10 seconds as UTF-8."
        ) from e
