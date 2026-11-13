"""A small WebSocket reader for the event stream, on the standard library only, so
the kit installs without a package registry. It reads JSON messages, answers
pings, and ends when the server closes the stream normally."""
from __future__ import annotations

import base64
import json
import os
import socket
import ssl
from typing import Any, Iterator, Optional
from urllib.parse import urlsplit

PING, PONG, CLOSE = 0x9, 0xA, 0x8
QUIET_LIMIT = 300  # seconds without a byte before the connection counts as dead


def websocket(url: str, path: str, key: str, idle: Optional[float]) -> Iterator[Optional[Any]]:
    """Yields each message, parsed, and None after `idle` seconds without one."""
    from .client import failure

    parts = urlsplit(url)
    secure = parts.scheme == "https"
    host, port = parts.hostname or "127.0.0.1", parts.port or (443 if secure else 80)
    sock = socket.create_connection((host, port), timeout=QUIET_LIMIT)
    if secure:
        sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
    try:
        nonce = base64.b64encode(os.urandom(16)).decode()
        upgrade = f"Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {nonce}\r\nSec-WebSocket-Version: 13\r\n"
        sock.sendall(f"GET {parts.path}{path} HTTP/1.1\r\nHost: {parts.netloc}\r\n{upgrade}Authorization: Bearer {key}\r\n\r\n".encode())
        reader = _Reader(sock)
        head = reader.until(b"\r\n\r\n").decode("latin-1")
        status = int(head.split(" ", 2)[1])
        if status != 101:
            length = next((int(line.split(":")[1]) for line in head.split("\r\n") if line.lower().startswith("content-length:")), 0)
            raise failure(status, reader.take(length), path.split("?")[0])
        message = bytearray()
        while True:
            if idle is not None and not message and not reader.wait(idle):
                yield None
                continue
            # A server never masks its frames (RFC 6455, section 5.1).
            first, second = reader.take(2)
            opcode, length = first & 0x0F, second & 0x7F
            if length >= 126:  # the length follows, in 2 bytes for 126 and in 8 for 127
                length = int.from_bytes(reader.take(2 if length == 126 else 8), "big")
            payload = reader.take(length)
            if opcode == PING:
                _send(sock, PONG, payload)
            elif opcode == CLOSE:
                code = int.from_bytes(payload[:2], "big") if len(payload) >= 2 else 1005
                if code == 1000:  # the world was deleted
                    return
                raise ConnectionError(f"the server closed the stream with code {code}")
            elif opcode in (0x0, 0x1, 0x2):
                message += payload
                if first & 0x80:
                    yield json.loads(message)
                    message = bytearray()
    finally:
        sock.close()


def _send(sock: socket.socket, opcode: int, payload: bytes) -> None:
    # A client masks every frame it sends (RFC 6455, section 5.3); control frames hold at most 125 bytes.
    mask = os.urandom(4)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload[:125]))
    sock.sendall(bytes([0x80 | opcode, 0x80 | len(masked)]) + mask + masked)


class _Reader:
    """Buffered reads that survive a timeout: bytes already read stay in the buffer."""

    def __init__(self, sock: socket.socket):
        self.sock, self.buffer = sock, bytearray()

    def _fill(self) -> None:
        chunk = self.sock.recv(65536)
        if not chunk:
            raise ConnectionError("the server closed the stream")
        self.buffer += chunk

    def wait(self, seconds: float) -> bool:
        """True when a byte is ready within `seconds`."""
        if self.buffer:
            return True
        self.sock.settimeout(seconds)
        try:
            self._fill()
            return True
        except socket.timeout:
            return False
        finally:
            self.sock.settimeout(QUIET_LIMIT)

    def take(self, n: int) -> bytes:
        while len(self.buffer) < n:
            self._fill()
        data, self.buffer = bytes(self.buffer[:n]), self.buffer[n:]
        return data

    def until(self, marker: bytes) -> bytes:
        while marker not in self.buffer:
            self._fill()
        return self.take(self.buffer.index(marker) + len(marker))
