"""The server's address when the system's resolver has none. The final must not stop because a resolver did:
on Saturday the laptop's resolver refused the server's name for hours while the server itself answered."""
from __future__ import annotations

import json
import os
import socket

SERVERS = ("1.1.1.1", "8.8.8.8")  # public name servers, asked directly when the system's resolver fails
MEMORY = "journal-hosts.json"  # the last addresses of each host we kept, for a desk that starts while the resolver is down

system = socket.getaddrinfo
kept: dict[str, list[str]] = {}


def keep(host: str) -> None:
    """From now on this host resolves as long as anyone ever told us its address: the system, a public name server, or our memory."""
    if not kept:
        socket.getaddrinfo = resolve
        try:
            with open(MEMORY) as file:
                kept.update(json.load(file))
        except (OSError, ValueError):
            pass
    kept.setdefault(host, [])


def resolve(host, port, *args, **kwargs):
    """The system's answer; when it has none for a host we keep, a public name server's; when they are silent too, the last answer anyone gave."""
    if host not in kept:
        return system(host, port, *args, **kwargs)
    try:
        found = system(host, port, *args, **kwargs)
        remember(host, sorted({item[4][0] for item in found}))
        return found
    except socket.gaierror:
        addresses = next(filter(None, (ask(server, host) for server in SERVERS)), kept[host])
        if not addresses:
            raise
        remember(host, addresses)
        return [item for address in addresses for item in system(address, port, *args, **kwargs)]


def remember(host: str, addresses: list[str]) -> None:
    """Keeps a host's addresses, also on disk for a desk that starts while the resolver is down."""
    if addresses != kept[host]:
        kept[host] = addresses
        try:
            with open(MEMORY, "w") as file:
                json.dump(kept, file)
        except OSError:
            pass


def ask(server: str, host: str) -> list[str]:
    """The IPv4 addresses of a host from one name server, by a plain DNS query (RFC 1035); [] when it does not answer."""
    name = b"".join(bytes([len(part)]) + part.encode() for part in host.split(".")) + b"\0"
    query = os.urandom(2) + b"\1\0\0\1\0\0\0\0\0\0" + name + b"\0\1\0\1"  # one question, recursion wanted: the A records, class IN
    addresses, at = [], len(query)  # the answer repeats the question, then holds one record per answer
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(1)
            sock.sendto(query, (server, 53))
            answer = sock.recv(512)
        for _ in range(int.from_bytes(answer[6:8], "big") if answer[:2] == query[:2] else 0):
            while answer[at] and answer[at] < 0xC0:  # the record's name: labels, ended by a zero or by a pointer
                at += answer[at] + 1
            at += 2 if answer[at] >= 0xC0 else 1
            kind, size = int.from_bytes(answer[at:at + 2], "big"), int.from_bytes(answer[at + 8:at + 10], "big")
            if kind == 1 and size == 4:
                addresses.append(".".join(str(byte) for byte in answer[at + 10:at + 14]))
            at += 10 + size
    except (OSError, IndexError):  # no route to the name server, or an answer that is not one
        pass
    return addresses
