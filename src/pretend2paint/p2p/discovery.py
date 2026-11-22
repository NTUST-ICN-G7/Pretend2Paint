"""UDP broadcast node discovery。

每個節點定期廣播 `Announcement`（peer_id、room、TCP port），
並監聽同一個 port 收別人的 announcement，收到時呼叫 `on_found`。
"""

import asyncio
import logging
import socket
from collections.abc import Callable, Sequence

from pretend2paint.common.types import PlayerId

from .config import DISCOVERY_BROADCAST_ADDR, DISCOVERY_INTERVAL
from .messages import Announcement, MessageError, decode_announcement, encode_announcement

logger = logging.getLogger(__name__)

type FoundHandler = Callable[[Announcement, str], None]
"""`on_found(announcement, sender_host)`。"""


class _DiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_datagram: Callable[[bytes, tuple[str, int]], None]) -> None:
        self._on_datagram = on_datagram

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self._on_datagram(data, addr)

    def error_received(self, exc: Exception) -> None:
        logger.warning("discovery socket error: %s", exc)


class Discovery:
    """定期廣播自己、監聽別人的 UDP discovery 服務（p2p 內部使用）。

    Args:
        peer_id: 自己的 id；收到自己的 announcement 會被忽略。
        room: 只回報同一個 room 的節點。
        listen_port: 監聽的 UDP port。
        targets: announcement 要送到的 `(host, port)` 清單；預設為區網廣播。
        on_found: 發現其他節點時呼叫。
        interval: 廣播間隔（秒）。
    """

    def __init__(
        self,
        peer_id: PlayerId,
        room: str,
        listen_port: int,
        targets: Sequence[tuple[str, int]],
        on_found: FoundHandler,
        interval: float = DISCOVERY_INTERVAL,
    ) -> None:
        self._peer_id = peer_id
        self._room = room
        self._listen_port = listen_port
        self._targets = list(targets)
        self._on_found = on_found
        self._interval = interval
        self._tcp_port = 0
        self._transport: asyncio.DatagramTransport | None = None
        self._task: asyncio.Task[None] | None = None

    @staticmethod
    def default_targets(port: int) -> list[tuple[str, int]]:
        """預設的廣播目標：`255.255.255.255:port`。"""
        return [(DISCOVERY_BROADCAST_ADDR, port)]

    async def start(self, tcp_port: int) -> None:
        """開始監聽並定期廣播 `tcp_port`。"""
        self._tcp_port = tcp_port
        loop = asyncio.get_running_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            # 讓同一台電腦能開多個節點（例如本機測試）
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", self._listen_port))
        sock.setblocking(False)
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _DiscoveryProtocol(self._handle_datagram), sock=sock
        )
        self._transport = transport
        self._task = asyncio.create_task(self._announce_loop(), name="p2p-discovery")
        logger.info("discovery listening on UDP %d", self._listen_port)

    async def stop(self) -> None:
        """停止廣播並關閉 socket。可重複呼叫。"""
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        if self._transport is not None:
            self._transport.close()
            self._transport = None

    def announce_now(self) -> None:
        """立刻送出一次 announcement。"""
        if self._transport is None:
            return
        data = encode_announcement(
            Announcement(peer_id=self._peer_id, room=self._room, tcp_port=self._tcp_port)
        )
        for target in self._targets:
            try:
                self._transport.sendto(data, target)
            except OSError as exc:
                logger.warning("discovery send to %s failed: %s", target, exc)

    async def _announce_loop(self) -> None:
        while True:
            self.announce_now()
            await asyncio.sleep(self._interval)

    def _handle_datagram(self, data: bytes, addr: tuple[str, int]) -> None:
        try:
            ann = decode_announcement(data)
        except MessageError as exc:
            logger.debug("ignore datagram from %s: %s", addr, exc)
            return
        if ann.peer_id == self._peer_id or ann.room != self._room:
            return
        try:
            self._on_found(ann, addr[0])
        except Exception:
            logger.exception("discovery on_found handler failed")
