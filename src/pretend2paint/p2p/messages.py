"""p2p 自己的控制訊息：TCP handshake 與 UDP discovery announcement。

這些只在 p2p 內部使用，與 streaming 的封包格式（docs/protocol.md）無關。
Handshake 完成後，TCP 連線上只會傳 streaming 送下來的 raw bytes。
"""

import json
import struct
from dataclasses import dataclass

from pretend2paint.common.types import PlayerId

from .config import (
    APP_ID,
    DISCOVERY_MAX_SIZE,
    HANDSHAKE_MAGIC,
    HANDSHAKE_MAX_SIZE,
    PROTOCOL_VERSION,
)

_LENGTH = struct.Struct("!H")
HANDSHAKE_HEADER_SIZE = len(HANDSHAKE_MAGIC) + _LENGTH.size


class MessageError(ValueError):
    """控制訊息格式錯誤（magic、版本、JSON、欄位不符）。"""


@dataclass(frozen=True, slots=True)
class Hello:
    """TCP 連線建立後雙方互送的 handshake。"""

    peer_id: PlayerId
    room: str
    listen_port: int


@dataclass(frozen=True, slots=True)
class Announcement:
    """UDP discovery 廣播的內容。"""

    peer_id: PlayerId
    room: str
    tcp_port: int


def _dump(kind: str, peer_id: PlayerId, room: str, port: int) -> bytes:
    body = {
        "app": APP_ID,
        "v": PROTOCOL_VERSION,
        "kind": kind,
        "peer_id": peer_id,
        "room": room,
        "port": port,
    }
    return json.dumps(body, separators=(",", ":")).encode()


def _load(kind: str, data: bytes) -> tuple[PlayerId, str, int]:
    try:
        body = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MessageError(f"invalid JSON: {exc}") from exc
    if not isinstance(body, dict):
        raise MessageError("body must be a JSON object")
    if body.get("app") != APP_ID or body.get("kind") != kind:
        raise MessageError("not a pretend2paint message of the expected kind")
    if body.get("v") != PROTOCOL_VERSION:
        raise MessageError(f"unsupported protocol version: {body.get('v')!r}")
    peer_id, room, port = body.get("peer_id"), body.get("room"), body.get("port")
    if not isinstance(peer_id, str) or not peer_id:
        raise MessageError("peer_id must be a non-empty string")
    if not isinstance(room, str):
        raise MessageError("room must be a string")
    if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
        raise MessageError("port must be an integer in 0..65535")
    return peer_id, room, port


def encode_hello(hello: Hello) -> bytes:
    """把 handshake 編成 `magic + 2-byte length + JSON`。"""
    body = _dump("hello", hello.peer_id, hello.room, hello.listen_port)
    if len(body) > HANDSHAKE_MAX_SIZE:
        raise MessageError("handshake too large")
    return HANDSHAKE_MAGIC + _LENGTH.pack(len(body)) + body


def parse_hello_header(header: bytes) -> int:
    """驗證 handshake header，回傳後面 JSON 的長度。"""
    if len(header) != HANDSHAKE_HEADER_SIZE or not header.startswith(HANDSHAKE_MAGIC):
        raise MessageError("bad handshake magic")
    (length,) = _LENGTH.unpack(header[len(HANDSHAKE_MAGIC) :])
    if length > HANDSHAKE_MAX_SIZE:
        raise MessageError("handshake too large")
    return length


def decode_hello(body: bytes) -> Hello:
    """解析 handshake 的 JSON 部分。"""
    peer_id, room, port = _load("hello", body)
    return Hello(peer_id=peer_id, room=room, listen_port=port)


def encode_announcement(ann: Announcement) -> bytes:
    """把 discovery announcement 編成 JSON datagram。"""
    data = _dump("announce", ann.peer_id, ann.room, ann.tcp_port)
    if len(data) > DISCOVERY_MAX_SIZE:
        raise MessageError("announcement too large")
    return data


def decode_announcement(data: bytes) -> Announcement:
    """解析 discovery datagram；格式不符時丟 `MessageError`。"""
    if len(data) > DISCOVERY_MAX_SIZE:
        raise MessageError("announcement too large")
    peer_id, room, port = _load("announce", data)
    if port == 0:
        raise MessageError("announced tcp port must not be 0")
    return Announcement(peer_id=peer_id, room=room, tcp_port=port)
