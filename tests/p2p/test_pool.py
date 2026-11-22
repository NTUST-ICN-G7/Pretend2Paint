"""ConnectionPool 的整合測試：全部在 localhost 上跑，不依賴實體網路。"""

import asyncio
import socket
from collections.abc import Callable

import pytest

from pretend2paint.p2p import ConnectionPool, HandshakeError, PeerNotConnectedError
from pretend2paint.p2p.messages import (
    HANDSHAKE_HEADER_SIZE,
    Hello,
    encode_hello,
    parse_hello_header,
)

LOCALHOST = "127.0.0.1"


class Recorder:
    """收集某個 pool 的 callback。"""

    def __init__(self, pool: ConnectionPool) -> None:
        self.data: dict[str, bytearray] = {}
        self.joined: list[str] = []
        self.left: list[str] = []
        pool.add_data_handler(lambda pid, b: self.data.setdefault(pid, bytearray()).extend(b))
        pool.add_peer_joined_handler(self.joined.append)
        pool.add_peer_left_handler(self.left.append)


def make_pool(peer_id: str, **kwargs: object) -> ConnectionPool:
    kwargs.setdefault("discovery", False)
    return ConnectionPool(peer_id, host=LOCALHOST, **kwargs)  # type: ignore[arg-type]


async def wait_until(cond: Callable[[], bool], timeout: float = 3.0) -> None:
    async with asyncio.timeout(timeout):
        while not cond():
            await asyncio.sleep(0.01)


def free_udp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((LOCALHOST, 0))
        return s.getsockname()[1]


def test_connect_send_broadcast_and_leave() -> None:
    async def scenario() -> None:
        a, b, c = make_pool("a"), make_pool("b"), make_pool("c")
        ra, rb, rc = Recorder(a), Recorder(b), Recorder(c)
        for p in (a, b, c):
            await p.start()
        try:
            assert await a.connect(LOCALHOST, b.listen_port) == "b"
            assert await a.connect(LOCALHOST, c.listen_port) == "c"
            await wait_until(lambda: b.peers == {"a"} and c.peers == {"a"})
            assert a.peers == {"b", "c"}
            assert ra.joined == ["b", "c"] and rb.joined == ["a"]

            # 單播：只有 b 收到
            a.send("b", b"secret")
            # 廣播：b、c 都收到
            a.broadcast(b"|all")
            await wait_until(lambda: bytes(rc.data.get("a", b"")) == b"|all")
            await wait_until(lambda: bytes(rb.data.get("a", b"")) == b"secret|all")

            # 反方向
            b.send("a", b"hi")
            await wait_until(lambda: bytes(ra.data.get("b", b"")) == b"hi")

            # c 離開：a 收到 peer_left
            await c.stop()
            await wait_until(lambda: ra.left == ["c"])
            assert a.peers == {"b"}
            assert rc.left == []  # 自己關閉不觸發
        finally:
            for p in (a, b, c):
                await p.stop()

    asyncio.run(scenario())


def test_send_many_and_errors() -> None:
    async def scenario() -> None:
        a, b, c = make_pool("a"), make_pool("b"), make_pool("c")
        rb, rc = Recorder(b), Recorder(c)
        for p in (a, b, c):
            await p.start()
        try:
            await a.connect(LOCALHOST, b.listen_port)
            await a.connect(LOCALHOST, c.listen_port)
            a.send_many(["b", "c", "b"], b"x")
            await wait_until(lambda: rb.data.get("a") == b"x" and rc.data.get("a") == b"x")

            with pytest.raises(PeerNotConnectedError):
                a.send("zzz", b"x")
            with pytest.raises(ValueError):
                a.send_many([], b"x")
            with pytest.raises(TypeError):
                a.send_many("b", b"x")
            with pytest.raises(TypeError):
                a.send("b", "not bytes")  # type: ignore[arg-type]
            # 有任何一個不在線就整批不送
            with pytest.raises(PeerNotConnectedError):
                a.send_many(["b", "zzz"], b"y")
            await asyncio.sleep(0.05)
            assert rb.data["a"] == b"x"
        finally:
            for p in (a, b, c):
                await p.stop()

    asyncio.run(scenario())


def test_handshake_rejects_room_mismatch_and_self() -> None:
    async def scenario() -> None:
        a = make_pool("a", room="r1")
        b = make_pool("b", room="r2")
        await a.start()
        await b.start()
        try:
            with pytest.raises(HandshakeError):
                await a.connect(LOCALHOST, b.listen_port)
            with pytest.raises(HandshakeError):
                await a.connect(LOCALHOST, a.listen_port)
            await asyncio.sleep(0.05)
            assert a.peers == frozenset() and b.peers == frozenset()
        finally:
            await a.stop()
            await b.stop()

    asyncio.run(scenario())


def test_non_p2p_client_is_rejected() -> None:
    async def scenario() -> None:
        a = make_pool("a")
        await a.start()
        try:
            reader, writer = await asyncio.open_connection(LOCALHOST, a.listen_port)
            writer.write(b"GET / HTTP/1.1\r\n\r\n")
            await reader.read()  # pool 會把連線關掉
            writer.close()
            assert a.peers == frozenset()
        finally:
            await a.stop()

    asyncio.run(scenario())


@pytest.mark.parametrize("first", ["a", "b"])
def test_duplicate_connection_keeps_single_link(first: str) -> None:
    async def scenario() -> None:
        a, b = make_pool("a"), make_pool("b")
        ra, rb = Recorder(a), Recorder(b)
        await a.start()
        await b.start()
        x, y = (a, b) if first == "a" else (b, a)
        try:
            await x.connect(LOCALHOST, y.listen_port)
            # 另一方也主動連：雙方應該只保留一條，且不重複觸發 joined / left
            assert await y.connect(LOCALHOST, x.listen_port) == x.peer_id
            await asyncio.sleep(0.1)
            assert a.peers == {"b"} and b.peers == {"a"}
            assert ra.joined == ["b"] and rb.joined == ["a"]
            assert ra.left == [] and rb.left == []
            a.send("b", b"ok")
            await wait_until(lambda: rb.data.get("a") == b"ok")
        finally:
            await a.stop()
            await b.stop()

    asyncio.run(scenario())


def test_handler_exception_does_not_break_pool() -> None:
    async def scenario() -> None:
        a, b = make_pool("a"), make_pool("b")

        def boom(peer_id: str, data: bytes) -> None:
            raise RuntimeError("handler bug")

        b.add_data_handler(boom)
        rb = Recorder(b)
        await a.start()
        await b.start()
        try:
            await a.connect(LOCALHOST, b.listen_port)
            a.send("b", b"1")
            a.send("b", b"2")
            await wait_until(lambda: rb.data.get("a") == b"12")
            assert b.peers == {"a"}
        finally:
            await a.stop()
            await b.stop()

    asyncio.run(scenario())


def test_discovery_auto_connects() -> None:
    """兩個節點各自監聽不同 UDP port，互相把 announcement 單播給對方（模擬廣播）。"""

    async def scenario() -> None:
        port_a, port_b = free_udp_port(), free_udp_port()
        a = make_pool(
            "a",
            discovery=True,
            discovery_port=port_a,
            discovery_targets=[(LOCALHOST, port_b)],
            discovery_interval=0.05,
        )
        b = make_pool(
            "b",
            discovery=True,
            discovery_port=port_b,
            discovery_targets=[(LOCALHOST, port_a)],
            discovery_interval=0.05,
        )
        await a.start()
        await b.start()
        try:
            await wait_until(lambda: a.peers == {"b"} and b.peers == {"a"})
        finally:
            await a.stop()
            await b.stop()

    asyncio.run(scenario())


def test_start_twice_and_connect_before_start() -> None:
    async def scenario() -> None:
        a = make_pool("a")
        with pytest.raises(RuntimeError):
            await a.connect(LOCALHOST, 1)
        await a.start()
        try:
            assert a.is_running and a.listen_port > 0
            with pytest.raises(RuntimeError):
                await a.start()
        finally:
            await a.stop()
            await a.stop()  # 可重複呼叫
        assert not a.is_running

    asyncio.run(scenario())


def test_drain_large_payload() -> None:
    async def scenario() -> None:
        a, b = make_pool("a"), make_pool("b")
        rb = Recorder(b)
        await a.start()
        await b.start()
        try:
            await a.connect(LOCALHOST, b.listen_port)
            payload = bytes(range(256)) * (4 * 1024 * 4)  # 4 MiB
            a.send("b", payload)
            await asyncio.wait_for(a.drain("b"), timeout=5)
            await asyncio.wait_for(a.drain(), timeout=5)
            await wait_until(lambda: len(rb.data.get("a", b"")) == len(payload))
            assert bytes(rb.data["a"]) == payload
            with pytest.raises(PeerNotConnectedError):
                await a.drain("zzz")
        finally:
            await a.stop()
            await b.stop()

    asyncio.run(scenario())


def test_write_buffer_overflow_disconnects_slow_peer() -> None:
    """對方完成 handshake 後就不再讀資料：超過上限要斷線並觸發 peer_left。"""

    async def scenario() -> None:
        stalled = asyncio.Event()

        async def slow_peer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            header = await reader.readexactly(HANDSHAKE_HEADER_SIZE)
            await reader.readexactly(parse_hello_header(header))
            writer.write(encode_hello(Hello("z", "default", 0)))
            await stalled.wait()  # 之後完全不讀
            writer.close()

        server = await asyncio.start_server(slow_peer, LOCALHOST, 0)
        port = server.sockets[0].getsockname()[1]
        a = make_pool("a", max_write_buffer=256 * 1024)
        ra = Recorder(a)
        await a.start()
        try:
            assert await a.connect(LOCALHOST, port) == "z"
            chunk = b"x" * (1024 * 1024)
            for _ in range(256):  # 最多 256 MiB，遠超過 kernel buffer
                if "z" not in a.peers:
                    break
                a.send("z", chunk)
                await asyncio.sleep(0)
            await wait_until(lambda: ra.left == ["z"])
            assert a.peers == frozenset()
        finally:
            stalled.set()
            await a.stop()
            server.close()

    asyncio.run(scenario())
