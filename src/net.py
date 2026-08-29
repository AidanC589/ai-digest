"""Guarded outbound HTTP for URLs this pipeline does not control.

Two paths fetch attacker-influenceable URLs: feeds.fetch_article_text follows the
<link> of an RSS entry (on the HN feeds that is the submitter's URL, so it is
arbitrary), and output.check_links HEADs every link the model wrote. Without a
guard either one will happily fetch http://127.0.0.1:11434 or an internal
192.168.x.x address — services that answer to anything local and are invisible
from the internet — and fetch_article_text publishes what comes back.

safe_urlopen resolves the host and rejects loopback, private, link-local and
other non-public addresses, then re-runs the same check on every redirect hop, so
a public host cannot bounce the request inward.

Not airtight: DNS is resolved once here and again by the socket layer, so a
record that changes between the two calls slips through. Closing that needs
pinning the connection to the vetted IP, which is more machinery than this
threat deserves here.
"""

import ipaddress
import socket
import urllib.request
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}
MAX_RESPONSE_BYTES = 10 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (compatible; ai-digest/1.0)"


class BlockedURL(Exception):
    """Raised when a URL, or a redirect target, resolves somewhere non-public."""


def _is_public_ip(addr):
    ip = ipaddress.ip_address(addr)
    return not (
        ip.is_private or ip.is_loopback or ip.is_link_local
        or ip.is_multicast or ip.is_reserved or ip.is_unspecified
    )


def is_public_http(url):
    """True if url is http(s) and every address its host resolves to is public."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False

    host = parsed.hostname
    if not host:
        return False

    try:
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError, ValueError, OSError):
        return False

    addrs = {info[4][0] for info in infos}
    if not addrs:
        return False

    try:
        # A host with any non-public address is rejected outright — a mixed
        # result means we cannot predict which one the socket layer will pick.
        return all(_is_public_ip(a) for a in addrs)
    except ValueError:
        return False


class _GuardedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-check every redirect target; urllib otherwise follows them blindly."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_public_http(newurl):
            raise BlockedURL(f"redirect to non-public URL: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_GuardedRedirectHandler())


def safe_urlopen(url, method="GET", timeout=15):
    """Open url with the redirect guard applied. Raises BlockedURL if non-public.

    The caller owns the response object and must close it.
    """
    if not is_public_http(url):
        raise BlockedURL(f"refusing to fetch non-public URL: {url}")
    req = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    return _opener.open(req, timeout=timeout)


def safe_fetch_bytes(url, timeout=15, max_bytes=MAX_RESPONSE_BYTES):
    """GET url and return the body, capped so a hostile server cannot stream forever.

    Returns bytes (not str) so trafilatura keeps doing its own charset detection.
    """
    with safe_urlopen(url, timeout=timeout) as resp:
        return resp.read(max_bytes)
