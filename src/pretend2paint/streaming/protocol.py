"""封包格式：encode / decode。格式的唯一來源是 docs/protocol.md。"""

import json
import logging
import struct

logger = logging.getLogger(__name__)

HEADER_SIZE = 7  # 2 (Magic) + 1 (Type) + 4 (Length)
MAX_PAYLOAD_SIZE = 4 * 1024 * 1024
"""payload 長度上限（bytes）。超過的 header 一律視為壞資料。"""


class PacketType:
    """封包類型。已發布的編號不可重新分配（見 docs/protocol.md）。"""

    DRAW_STROKE = 0x01
    SPY_SELECT_REF = 0x02
    ROUND_STATE_SYNC = 0x03
    CANVAS_SNAPSHOT = 0x04
    DEAL_WORD = 0x05
    SPY_REFERENCE = 0x06
    VOTE = 0x07
    SPY_GUESS = 0x08
    ROUND_RESULT = 0x09

    ALL = frozenset(
        {
            DRAW_STROKE,
            SPY_SELECT_REF,
            ROUND_STATE_SYNC,
            CANVAS_SNAPSHOT,
            DEAL_WORD,
            SPY_REFERENCE,
            VOTE,
            SPY_GUESS,
            ROUND_RESULT,
        }
    )


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
    PacketType.ROUND_RESULT: ("spy", "answer", "scores"),
}
"""各封包 payload 必備的欄位；收到缺欄位的封包會被丟棄，不會交給上層。"""


class StreamPacket:
    MAGIC = b"\x49\x43"  # "IC" 代表 ICN-G7

    @staticmethod
    def encode(packet_type: int, payload_dict: dict) -> bytes:
        """將字典編碼為帶有 7-byte Header 的二進位封包。

        :raises ValueError: 未知的封包類型，或 payload 超過 ``MAX_PAYLOAD_SIZE``
        :raises TypeError: payload 不是 dict，或內容無法轉成 JSON
        """
        if packet_type not in PacketType.ALL:
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

    def parse_packets(self) -> list[tuple[int, dict]]:
        """解出 buffer 裡所有完整且合法的封包，回傳 ``(packet_type, payload)`` 串列。"""
        packets: list[tuple[int, dict]] = []

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

            if packet_type not in PacketType.ALL:
                logger.warning("Unknown packet type 0x%02x; dropped.", packet_type)
                continue

            payload = self._decode_payload(payload_bytes)
            if payload is not None:
                packets.append((packet_type, payload))

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
