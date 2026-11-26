"""封包格式：encode / decode。格式的唯一來源是 docs/protocol.md。"""

import json
import logging
import struct
from enum import IntEnum

from pretend2paint.common.types import Phase

logger = logging.getLogger(__name__)

HEADER_SIZE = 7  # 2 (Magic) + 1 (Type) + 4 (Length)
MAX_PAYLOAD_SIZE = 4 * 1024 * 1024
"""payload 長度上限（bytes）。超過的 header 一律視為壞資料。"""


class PacketType(IntEnum):
    """封包類型。已發布的編號不可重新分配（見 docs/protocol.md）。

    是 ``IntEnum``，所以 log 與除錯時看得到名稱，也可以直接當整數比較或放進 header。
    """

    DRAW_STROKE = 0x01
    SPY_SELECT_REF = 0x02
    ROUND_STATE_SYNC = 0x03
    CANVAS_SNAPSHOT = 0x04
    DEAL_WORD = 0x05
    SPY_REFERENCE = 0x06
    VOTE = 0x07
    SPY_GUESS = 0x08
    ROUND_RESULT = 0x09


PACKET_TYPES = frozenset(PacketType)
"""所有已定義的封包類型。"""


def packet_name(packet_type: int) -> str:
    """給 log 用：已知類型回傳名稱，未知類型回傳十六進位。"""
    try:
        return PacketType(packet_type).name
    except ValueError:
        return f"0x{packet_type:02x}"


BROADCAST_TYPES = frozenset({PacketType.ROUND_STATE_SYNC, PacketType.ROUND_RESULT})
"""唯一允許廣播的類型。其餘一律單播（ADR 0005：機密資訊不可廣播）。"""

REQUIRED_FIELDS: dict[int, tuple[str, ...]] = {
    PacketType.DRAW_STROKE: (),
    PacketType.SPY_SELECT_REF: ("index",),
    PacketType.ROUND_STATE_SYNC: ("state",),
    PacketType.CANVAS_SNAPSHOT: ("image",),
    PacketType.DEAL_WORD: ("text",),
    PacketType.SPY_REFERENCE: ("image",),
    PacketType.VOTE: ("target",),
    PacketType.SPY_GUESS: ("guess",),
    PacketType.ROUND_RESULT: ("scores",),
}
"""各封包 payload 必備的欄位；收到缺欄位的封包會被丟棄，不會交給上層。"""

ROUND_RESULT_OUTCOMES = ("escaped", "caught", "tie", "void")
ROUND_RESULT_DETAILS = ("spy", "answer", "hint", "spy_guess", "guess_correct", "drawings")
ROUND_RESULT_PENALTIES = ("violations", "removed_players")


def _round_result_error(payload: dict) -> str | None:
    if "outcome" not in payload:
        if not all(key in payload for key in ("spy", "answer")):
            return "legacy round result requires spy and answer"
        if any(key in payload for key in ROUND_RESULT_DETAILS[2:] + ROUND_RESULT_PENALTIES):
            return "extended round result requires outcome"
        return None

    outcome = payload["outcome"]
    if outcome not in ROUND_RESULT_OUTCOMES:
        return "unknown round result outcome"
    if not all(isinstance(payload.get(key), list) for key in ROUND_RESULT_PENALTIES):
        return "round result requires violations and removed_players arrays"
    if outcome == "void":
        if payload.keys() - {"outcome", "scores", *ROUND_RESULT_PENALTIES}:
            return "void round result can only include scores and penalty details"
        return None

    if not all(key in payload for key in ROUND_RESULT_DETAILS):
        return "missing regular round result details"
    if not all(isinstance(payload[key], str) for key in ("spy", "answer", "hint")):
        return "spy, answer and hint must be strings"
    if not isinstance(payload["drawings"], list):
        return "drawings must be an array"
    if payload["spy_guess"] is not None and not isinstance(payload["spy_guess"], str):
        return "spy_guess must be a string or null"
    if payload["guess_correct"] is not None and not isinstance(payload["guess_correct"], bool):
        return "guess_correct must be a boolean or null"
    return None


def payload_error(packet_type: int, payload: dict) -> str | None:
    """檢查 payload 是否合法；合法回傳 ``None``，否則回傳原因。"""
    missing = [k for k in REQUIRED_FIELDS.get(packet_type, ()) if k not in payload]
    if missing:
        return f"missing fields {missing}"

    if packet_type == PacketType.ROUND_RESULT:
        return _round_result_error(payload)

    if packet_type == PacketType.ROUND_STATE_SYNC:
        try:
            Phase(payload["state"])
        except ValueError, TypeError:
            return f"unknown phase {payload['state']!r}"

    return None


class StreamPacket:
    MAGIC = b"\x49\x43"  # "IC" 代表 ICN-G7

    @staticmethod
    def encode(packet_type: int, payload_dict: dict) -> bytes:
        """將字典編碼為帶有 7-byte Header 的二進位封包。

        :raises ValueError: 未知的封包類型，或 payload 超過 ``MAX_PAYLOAD_SIZE``
        :raises TypeError: payload 不是 dict，或內容無法轉成 JSON
        """
        if packet_type not in PACKET_TYPES:
            raise ValueError(f"unknown packet type: {packet_type!r}")
        if not isinstance(payload_dict, dict):
            raise TypeError("payload must be a dict")

        payload_bytes = json.dumps(payload_dict, ensure_ascii=False).encode("utf-8")
        if len(payload_bytes) > MAX_PAYLOAD_SIZE:
            raise ValueError(f"payload too large: {len(payload_bytes)} > {MAX_PAYLOAD_SIZE}")

        # 格式：2 bytes Magic, 1 byte Type, 4 bytes Length（network byte order, big-endian）
        header = struct.pack("!2sBI", StreamPacket.MAGIC, packet_type, len(payload_bytes))
        return header + payload_bytes


class StreamPacketDecoder:
    """處理 TCP 串流的累加與解包器（每個 peer 一個）。

    - 黏包、半包：正常處理。
    - 壞資料：只丟掉壞的部分並重新對齊到下一個 Magic，不會丟例外，也不會清空整個 buffer。
    """

    def __init__(self) -> None:
        self.buffer = bytearray()

    def feed_data(self, data: bytes) -> None:
        self.buffer.extend(data)

    def parse_packets(self) -> list[tuple[PacketType, dict]]:
        """解出 buffer 裡所有完整且合法的封包，回傳 ``(packet_type, payload)`` 串列。"""
        packets: list[tuple[PacketType, dict]] = []

        while self._sync() and len(self.buffer) >= HEADER_SIZE:
            packet_type = self.buffer[2]
            payload_len = struct.unpack("!I", self.buffer[3:7])[0]

            if payload_len > MAX_PAYLOAD_SIZE:
                logger.error("Payload length %d exceeds limit; resyncing.", payload_len)
                del self.buffer[:1]  # 這個 Magic 是假的，往後找下一個
                continue

            total_size = HEADER_SIZE + payload_len
            if len(self.buffer) < total_size:
                break  # 半包：等更多資料

            payload_bytes = bytes(self.buffer[HEADER_SIZE:total_size])
            del self.buffer[:total_size]

            if packet_type not in PACKET_TYPES:
                logger.warning("Unknown packet type 0x%02x; dropped.", packet_type)
                continue

            payload = self._decode_payload(payload_bytes)
            if payload is not None:
                packets.append((PacketType(packet_type), payload))

        return packets

    def _sync(self) -> bool:
        """丟掉 Magic 之前的垃圾 bytes。回傳 buffer 開頭是否已對齊到 Magic。"""
        magic = StreamPacket.MAGIC
        if self.buffer.startswith(magic):
            return True

        index = self.buffer.find(magic)
        if index == -1:
            # 保留最後 1 byte：它可能是下一個 Magic 的第一個 byte
            keep = 1 if self.buffer.endswith(magic[:1]) else 0
            dropped = len(self.buffer) - keep
            if dropped:
                logger.error("No Magic found; dropped %d bytes.", dropped)
                del self.buffer[:dropped]
            return False

        logger.error("Magic mismatch; skipped %d bytes to resync.", index)
        del self.buffer[:index]
        return True

    @staticmethod
    def _decode_payload(payload_bytes: bytes) -> dict | None:
        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except (ValueError, RecursionError) as e:  # 含 UnicodeDecodeError / JSONDecodeError
            logger.error("Failed to decode payload: %s", e)
            return None
        if not isinstance(payload, dict):
            logger.error("Payload is not a JSON object; dropped.")
            return None
        return payload
