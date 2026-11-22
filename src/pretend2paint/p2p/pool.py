"""TCP full-mesh connection pool。

每兩個節點之間維持一條 TCP 連線。連線建立後先互送 `Hello`（handshake）確認
peer_id 與 room，之後連線上只傳上層（streaming）送下來的 raw bytes。
"""

import asyncio
import logging
import uuid
from collections.abc import Callable, Coroutine, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from pretend2paint.common.types import PlayerId

from .config import (
    CONNECT_TIMEOUT,
    DEFAULT_DISCOVERY_PORT,
    DEFAULT_LISTEN_HOST,
    DEFAULT_ROOM,
    DEFAULT_TCP_PORT,
    DISCOVERY_INTERVAL,
    HANDSHAKE_TIMEOUT,
    READ_CHUNK_SIZE,
)
from .discovery import Discovery
from .messages import (
    HANDSHAKE_HEADER_SIZE,
    Announcement,
    Hello,
    MessageError,
    decode_hello,
    encode_hello,
    parse_hello_header,
)

logger = logging.getLogger(__name__)

type DataHandler = Callable[[PlayerId, bytes], None]
"""`handler(peer_id, raw_bytes)`：收到某個 peer 的資料。"""

type PeerHandler = Callable[[PlayerId], None]
"""`handler(peer_id)`：peer 加入或離開。"""


class P2PError(Exception):
    """p2p 模組錯誤的基底類別。"""


class PeerNotConnectedError(P2PError, LookupError):
    """指定的 peer 目前沒有連線。"""


class HandshakeError(P2PError):
    """連線建立後 handshake 失敗（格式錯誤、room 不同、連到自己、逾時）。"""


@dataclass(eq=False)
class _Connection:
    peer_id: PlayerId
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    outbound: bool
    task: asyncio.Task[None] | None = field(default=None)


class ConnectionPool:
    """P2P 節點：UDP discovery + TCP full-mesh 連線池。

    所有方法都必須在背景 asyncio 執行緒（event loop 所在的執行緒）呼叫，
    見 docs/decisions/0004-threading-model.md。

    Args:
        peer_id: 自己的 id；省略時自動產生（uuid4 hex）。
        room: 網路分區名稱，只會和同一個 room 的節點互連。
        host: TCP 監聽位址。
        port: TCP 監聽 port，0 表示由系統挑選。
        discovery: 是否啟用 UDP broadcast discovery。
        discovery_port: UDP discovery 使用的 port。
        discovery_targets: announcement 送往的 `(host, port)`；預設為區網廣播。
        discovery_interval: 廣播間隔（秒）。
    """

    def __init__(
        self,
        peer_id: PlayerId | None = None,
        *,
        room: str = DEFAULT_ROOM,
        host: str = DEFAULT_LISTEN_HOST,
        port: int = DEFAULT_TCP_PORT,
        discovery: bool = True,
        discovery_port: int = DEFAULT_DISCOVERY_PORT,
        discovery_targets: Sequence[tuple[str, int]] | None = None,
        discovery_interval: float = DISCOVERY_INTERVAL,
    ) -> None:
        self._peer_id: PlayerId = peer_id or uuid.uuid4().hex
        self._room = room
        self._host = host
        self._port = port
        self._server: asyncio.Server | None = None
        self._listen_port = 0
        self._conns: dict[PlayerId, _Connection] = {}
        self._dialing: set[tuple[str, int]] = set()
        self._background: set[asyncio.Task[None]] = set()
        self._data_handlers: list[DataHandler] = []
        self._joined_handlers: list[PeerHandler] = []
        self._left_handlers: list[PeerHandler] = []
        self._discovery: Discovery | None = None
        if discovery:
            targets = discovery_targets or Discovery.default_targets(discovery_port)
            self._discovery = Discovery(
                peer_id=self._peer_id,
                room=room,
                listen_port=discovery_port,
                targets=targets,
                on_found=self._on_discovered,
                interval=discovery_interval,
            )

    # ------------------------------------------------------------ properties
    @property
    def peer_id(self) -> PlayerId:
        """自己的 peer id。"""
        return self._peer_id

    @property
    def room(self) -> str:
        """所在的 room 名稱。"""
        return self._room

    @property
    def listen_port(self) -> int:
        """實際監聽的 TCP port（`start()` 之前為 0）。"""
        return self._listen_port

    @property
    def peers(self) -> frozenset[PlayerId]:
        """目前已完成 handshake 的 peer id（不含自己）。"""
        return frozenset(self._conns)

    @property
    def is_running(self) -> bool:
        """`start()` 之後、`stop()` 之前為 True。"""
        return self._server is not None

    # ------------------------------------------------------------ callbacks
    def add_data_handler(self, handler: DataHandler) -> None:
        """註冊「收到資料」的 callback：`handler(peer_id, raw_bytes)`。"""
        self._data_handlers.append(handler)

    def add_peer_joined_handler(self, handler: PeerHandler) -> None:
        """註冊「peer 連上（handshake 完成）」的 callback：`handler(peer_id)`。"""
        self._joined_handlers.append(handler)

    def add_peer_left_handler(self, handler: PeerHandler) -> None:
        """註冊「peer 斷線」的 callback：`handler(peer_id)`。"""
        self._left_handlers.append(handler)

    # ------------------------------------------------------------ lifecycle
    async def start(self) -> None:
        """開始監聽 TCP，並啟動 discovery（若有啟用）。

        Raises:
            RuntimeError: 已經在執行。
            OSError: port 被占用等 socket 錯誤。
        """
        if self._server is not None:
            raise RuntimeError("ConnectionPool already started")
        self._server = await asyncio.start_server(self._on_inbound, self._host, self._port)
        self._listen_port = self._server.sockets[0].getsockname()[1]
        logger.info("p2p %s listening on TCP %d", self._peer_id, self._listen_port)
        if self._discovery is not None:
            try:
                await self._discovery.start(self._listen_port)
            except OSError:
                await self.stop()
                raise

    async def stop(self) -> None:
        """關閉所有連線、server 與 discovery。可重複呼叫。

        自己關閉時**不會**觸發 `peer_left` callback。
        """
        if self._discovery is not None:
            await self._discovery.stop()
        if self._server is not None:
            self._server.close()
            self._server = None
        conns = list(self._conns.values())
        self._conns.clear()
        for conn in conns:
            conn.writer.close()
        tasks = [c.task for c in conns if c.task is not None] + list(self._background)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self._background.clear()
        self._listen_port = 0

    # ------------------------------------------------------------ connect
    async def connect(self, host: str, port: int) -> PlayerId:
        """主動連到 `host:port` 的節點（例如 discovery 被擋時手動輸入 IP）。

        Returns:
            對方的 peer id。已經連線過的話直接回傳既有的 id。

        Raises:
            RuntimeError: 尚未 `start()`。
            OSError / TimeoutError: 連不上。
            HandshakeError: handshake 失敗。
        """
        if self._server is None:
            raise RuntimeError("ConnectionPool is not running")
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=CONNECT_TIMEOUT
        )
        return await self._setup(reader, writer, outbound=True)

    # ------------------------------------------------------------ send
    def send(self, peer_id: PlayerId, data: bytes) -> None:
        """把 bytes 送給**單一**指定的 peer（單播）。

        Raises:
            TypeError: `data` 不是 bytes-like。
            PeerNotConnectedError: 該 peer 沒有連線。
        """
        _check_bytes(data)
        conn = self._conns.get(peer_id)
        if conn is None:
            raise PeerNotConnectedError(peer_id)
        self._write(conn, data)

    def send_many(self, peer_ids: Iterable[PlayerId], data: bytes) -> None:
        """把 bytes 送給多個指定的 peer。

        會先檢查全部 peer 都在線才開始送，避免只送出一部分。

        Raises:
            TypeError: `peer_ids` 是字串，或 `data` 不是 bytes-like。
            ValueError: `peer_ids` 為空（避免誤當成「全部」）。
            PeerNotConnectedError: 任一 peer 沒有連線。
        """
        if isinstance(peer_ids, str):
            raise TypeError("peer_ids must be an iterable of ids, not a str")
        _check_bytes(data)
        targets = list(dict.fromkeys(peer_ids))
        if not targets:
            raise ValueError("peer_ids must not be empty; use broadcast() to send to everyone")
        missing = [p for p in targets if p not in self._conns]
        if missing:
            raise PeerNotConnectedError(", ".join(missing))
        for pid in targets:
            self._write(self._conns[pid], data)

    def broadcast(self, data: bytes) -> None:
        """把 bytes 送給**所有**已連線的 peer（不含自己）。

        **機密資訊不可使用**，見 docs/decisions/0005-secret-information.md。

        Raises:
            TypeError: `data` 不是 bytes-like。
        """
        _check_bytes(data)
        for conn in list(self._conns.values()):
            self._write(conn, data)

    # ------------------------------------------------------------ internals
    def _write(self, conn: _Connection, data: bytes) -> None:
        if conn.writer.is_closing():
            logger.warning("drop %d bytes to %s: connection closing", len(data), conn.peer_id)
            return
        conn.writer.write(data)

    def _on_discovered(self, ann: Announcement, host: str) -> None:
        # 只有 id 較小的一方主動連線，避免雙方同時連造成重複連線
        if self._server is None or ann.peer_id in self._conns or self._peer_id > ann.peer_id:
            return
        addr = (host, ann.tcp_port)
        if addr in self._dialing:
            return
        self._dialing.add(addr)
        self._spawn(self._dial_discovered(addr))

    async def _dial_discovered(self, addr: tuple[str, int]) -> None:
        try:
            await self.connect(*addr)
        except (OSError, TimeoutError, HandshakeError) as exc:
            logger.info("dial %s:%d failed: %s", *addr, exc)
        finally:
            self._dialing.discard(addr)

    def _spawn(self, coro: Coroutine[Any, Any, None]) -> None:
        task = asyncio.create_task(coro)
        self._background.add(task)
        task.add_done_callback(self._background.discard)

    async def _on_inbound(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            await self._setup(reader, writer, outbound=False)
        except (OSError, TimeoutError, HandshakeError) as exc:
            logger.info("inbound connection rejected: %s", exc)

    async def _setup(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, *, outbound: bool
    ) -> PlayerId:
        try:
            writer.write(encode_hello(Hello(self._peer_id, self._room, self._listen_port)))
            hello = await asyncio.wait_for(_read_hello(reader), timeout=HANDSHAKE_TIMEOUT)
            if hello.peer_id == self._peer_id:
                raise HandshakeError("connected to self")
            if hello.room != self._room:
                raise HandshakeError(f"room mismatch: {hello.room!r} != {self._room!r}")
        except BaseException:
            writer.close()
            raise
        return self._register(_Connection(hello.peer_id, reader, writer, outbound))

    def _register(self, conn: _Connection) -> PlayerId:
        pid = conn.peer_id
        if self._server is None:
            conn.writer.close()
            raise HandshakeError("pool stopped during handshake")
        existing = self._conns.get(pid)
        if existing is not None:
            # 重複連線：雙方都保留「由 id 較小一方發起」的那條，結果一致
            dialer_new = self._peer_id if conn.outbound else pid
            if dialer_new != min(self._peer_id, pid):
                conn.writer.close()
                return pid
            logger.debug("replace duplicate connection to %s", pid)
            self._conns[pid] = conn
            existing.writer.close()
            conn.task = asyncio.create_task(self._read_loop(conn), name=f"p2p-read-{pid}")
            return pid
        self._conns[pid] = conn
        conn.task = asyncio.create_task(self._read_loop(conn), name=f"p2p-read-{pid}")
        logger.info("peer joined: %s (%s)", pid, "outbound" if conn.outbound else "inbound")
        self._emit(self._joined_handlers, pid)
        return pid

    async def _read_loop(self, conn: _Connection) -> None:
        try:
            while True:
                chunk = await conn.reader.read(READ_CHUNK_SIZE)
                if not chunk:
                    break
                for handler in list(self._data_handlers):
                    try:
                        handler(conn.peer_id, chunk)
                    except Exception:
                        logger.exception("data handler failed for peer %s", conn.peer_id)
        except (OSError, asyncio.IncompleteReadError) as exc:
            logger.info("connection to %s lost: %s", conn.peer_id, exc)
        finally:
            conn.writer.close()
            # 只有仍是目前那條連線時才算離開（被重複連線取代的不算）
            if self._conns.get(conn.peer_id) is conn:
                del self._conns[conn.peer_id]
                logger.info("peer left: %s", conn.peer_id)
                self._emit(self._left_handlers, conn.peer_id)

    def _emit(self, handlers: list[PeerHandler], peer_id: PlayerId) -> None:
        for handler in list(handlers):
            try:
                handler(peer_id)
            except Exception:
                logger.exception("peer handler failed for %s", peer_id)


async def _read_hello(reader: asyncio.StreamReader) -> Hello:
    try:
        header = await reader.readexactly(HANDSHAKE_HEADER_SIZE)
        length = parse_hello_header(header)
        return decode_hello(await reader.readexactly(length))
    except asyncio.IncompleteReadError as exc:
        raise HandshakeError("connection closed during handshake") from exc
    except MessageError as exc:
        raise HandshakeError(str(exc)) from exc


def _check_bytes(data: object) -> None:
    if not isinstance(data, bytes | bytearray | memoryview):
        raise TypeError(f"data must be bytes-like, got {type(data).__name__}")
