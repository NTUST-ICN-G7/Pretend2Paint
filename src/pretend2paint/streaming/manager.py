"""StreamManager：封包的收發與分發。

- 收：p2p 呼叫 ``handle_incoming_data``，解出封包後依類型分發給上層註冊的 handler。
- 送：提供各封包的送出方法。streaming 只負責「照指定的對象送出」，不決定誰該收。
"""

import logging
from collections.abc import Callable, Iterable
from typing import Protocol

from pretend2paint.common.types import Phase, PlayerId

from .protocol import (
    BROADCAST_TYPES,
    PACKET_TYPES,
    PacketType,
    StreamPacket,
    StreamPacketDecoder,
    packet_name,
    payload_error,
)

logger = logging.getLogger(__name__)

type Handler = Callable[[PlayerId, dict], None]
"""上層的 handler：``handler(peer_id, payload)``。"""


class ConnectionPool(Protocol):
    """streaming 用到的 p2p 介面（p2p 的連線池另外還有 ``send`` 與 ``drain``，這裡用不到）。"""

    def send_many(self, peer_ids: Iterable[PlayerId], data: bytes) -> None:
        """把 bytes 送給多個指定的 peer；空清單會丟 ``ValueError``，不會被當成「全部」。"""
        ...

    def broadcast(self, data: bytes) -> None:
        """把 bytes 送給房間內所有 peer。"""
        ...


class StreamManager:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool
        self._decoders: dict[PlayerId, StreamPacketDecoder] = {}
        self._handlers: dict[int, list[Handler]] = {}

    # ------------------------------------------------------------------ 接收
    def register_handler(self, packet_type: int, handler: Handler) -> None:
        """註冊某類封包的 handler，同一類型可以註冊多個（依註冊順序呼叫）。

        :raises ValueError: 未知的封包類型
        """
        if packet_type not in PACKET_TYPES:
            raise ValueError(f"unknown packet type: {packet_type!r}")
        self._handlers.setdefault(PacketType(packet_type), []).append(handler)

    def handle_incoming_data(self, peer_id: PlayerId, raw_data: bytes) -> None:
        """p2p 收到某個 peer 的 bytes 時呼叫。壞資料只會被記錄並丟棄，不會丟例外。"""
        decoder = self._decoders.setdefault(peer_id, StreamPacketDecoder())
        decoder.feed_data(raw_data)

        try:
            packets = decoder.parse_packets()
        except Exception:
            logger.exception("Decoder failed for peer %s; resetting its buffer.", peer_id)
            self._decoders[peer_id] = StreamPacketDecoder()
            return

        for packet_type, payload in packets:
            self._dispatch_packet(peer_id, packet_type, payload)

    def remove_peer(self, peer_id: PlayerId) -> None:
        """peer 斷線時呼叫，清掉它的 decoder（避免重連後殘留半包）。"""
        self._decoders.pop(peer_id, None)

    def _dispatch_packet(self, peer_id: PlayerId, packet_type: int, payload: dict) -> None:
        error = payload_error(packet_type, payload)
        if error:
            logger.error(
                "Packet %s from %s invalid (%s); dropped.", packet_name(packet_type), peer_id, error
            )
            return

        handlers = self._handlers.get(packet_type, [])
        if not handlers:
            logger.debug("No handler for packet %s from %s.", packet_name(packet_type), peer_id)
            return

        for handler in handlers:
            try:
                handler(peer_id, payload)
            except Exception:
                logger.exception("Handler for packet %s raised.", packet_name(packet_type))

    # ------------------------------------------------------------------ 送出（單播）
    def send_draw_stroke(self, target_peers: Iterable[PlayerId], stroke_data: dict) -> None:
        """送出畫筆資料。畫圖階段畫作不公開，所以只能指定對象，不能廣播。"""
        self._send_to(PacketType.DRAW_STROKE, stroke_data, target_peers)

    def send_spy_selection(self, target_peers: Iterable[PlayerId], index: int) -> None:
        """間諜 → 房主：盲選第 ``index`` 張參考圖（間諜不知道作者）。"""
        self._send_to(PacketType.SPY_SELECT_REF, {"index": index}, target_peers)

    def send_canvas_snapshot(
        self,
        target_peers: Iterable[PlayerId],
        image: str,
        author: PlayerId | None = None,
        index: int | None = None,
        marked: bool | None = None,
    ) -> None:
        """送出畫作。``image`` 為 base64 編碼的 PNG；後三個欄位只在公開階段由房主填入。"""
        payload: dict = {"image": image}
        if author is not None:
            payload["author"] = author
        if index is not None:
            payload["index"] = index
        if marked is not None:
            payload["marked"] = marked
        self._send_to(PacketType.CANVAS_SNAPSHOT, payload, target_peers)

    def send_deal_word(self, target_peers: Iterable[PlayerId], text: str) -> None:
        """房主 → 單一玩家：發題（一般玩家是答案，間諜是提示）。只允許一個對象。"""
        self._send_to(PacketType.DEAL_WORD, {"text": text}, target_peers, single=True)

    def send_spy_reference(self, target_peers: Iterable[PlayerId], image: str) -> None:
        """房主 → 間諜：把盲選到的參考圖（不含作者）發給間諜。只允許一個對象。"""
        self._send_to(PacketType.SPY_REFERENCE, {"image": image}, target_peers, single=True)

    def send_vote(self, target_peers: Iterable[PlayerId], target: PlayerId) -> None:
        """玩家 → 房主：投給 ``target``。"""
        self._send_to(PacketType.VOTE, {"target": target}, target_peers)

    def send_spy_guess(self, target_peers: Iterable[PlayerId], guess: str) -> None:
        """間諜 → 房主：猜答案。"""
        self._send_to(PacketType.SPY_GUESS, {"guess": guess}, target_peers)

    # ------------------------------------------------------------------ 送出（廣播）
    def broadcast_round_state(self, state: Phase | str) -> None:
        """房主 → 所有人：同步目前的回合階段。

        :raises ValueError: ``state`` 不是合法的 ``Phase``（打錯字會在送出前就被擋下）
        """
        self._broadcast(PacketType.ROUND_STATE_SYNC, {"state": Phase(state).value})

    def broadcast_round_result(
        self, spy: PlayerId, answer: str, scores: dict[PlayerId, int]
    ) -> None:
        """房主 → 所有人：公布間諜、答案、得分（答案只有此時才公開）。"""
        payload = {"spy": spy, "answer": answer, "scores": scores}
        self._broadcast(PacketType.ROUND_RESULT, payload)

    # ------------------------------------------------------------------ 內部
    def _send_to(
        self,
        packet_type: int,
        payload: dict,
        target_peers: Iterable[PlayerId],
        *,
        single: bool = False,
    ) -> None:
        if isinstance(target_peers, str):
            raise TypeError("target_peers must be a list of peer ids, not a str")
        peers = list(target_peers)
        if not peers:
            raise ValueError("target_peers must not be empty (unicast needs explicit targets)")
        if single and len(peers) != 1:
            raise ValueError("this packet must be sent to exactly one peer")

        self.pool.send_many(peers, StreamPacket.encode(packet_type, payload))

    def _broadcast(self, packet_type: int, payload: dict) -> None:
        if packet_type not in BROADCAST_TYPES:
            raise ValueError(f"packet {packet_name(packet_type)} must not be broadcast (ADR 0005)")
        self.pool.broadcast(StreamPacket.encode(packet_type, payload))
