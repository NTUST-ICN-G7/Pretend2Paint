"""P2P 實機測試工具：`uv run python -m pretend2paint.p2p`。

在多台電腦上各開一個，確認 UDP discovery、單播、廣播與大量傳輸在真實網路上可以用。
這只是測試用的小聊天程式，不是遊戲本體；訊息以換行分隔，與 streaming 的封包格式無關。

指令：
    <文字>                 廣播給所有 peer
    /to <peer_id> <文字>   只送給一個 peer（可以只打 id 開頭幾個字）
    /connect <host> <port> 手動連線（discovery 被擋時用）
    /peers                 列出已連線的 peer
    /big <MiB>             對所有 peer 送一筆大資料並量測速度
    /quit                  離開
"""

import argparse
import asyncio
import contextlib
import logging
import socket
import sys
import threading
import time

from pretend2paint.common.types import PlayerId

from . import ConnectionPool, P2PError
from .config import DEFAULT_DISCOVERY_PORT, DEFAULT_ROOM

_PREVIEW = 80


def _out(text: str) -> None:
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def _local_ips() -> list[str]:
    """盡量找出本機的區網 IP，方便別人手動連線。"""
    ips: set[str] = set()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))  # 不會真的送封包，只是讓系統選網卡
            ips.add(s.getsockname()[0])
        except OSError:
            pass
    with contextlib.suppress(OSError):
        ips.update(socket.gethostbyname_ex(socket.gethostname())[2])
    return sorted(ip for ip in ips if not ip.startswith("127."))


class _LineChat:
    """把每個 peer 的 bytes 串流切成一行一行的訊息。"""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool
        self._buffers: dict[PlayerId, bytearray] = {}

    def on_data(self, peer_id: PlayerId, data: bytes) -> None:
        buf = self._buffers.setdefault(peer_id, bytearray())
        buf.extend(data)
        while (idx := buf.find(b"\n")) >= 0:
            line = bytes(buf[:idx])
            del buf[: idx + 1]
            if len(line) > _PREVIEW:
                _out(f"[{peer_id[:8]}] <{len(line):,} bytes>")
            else:
                _out(f"[{peer_id[:8]}] {line.decode(errors='replace')}")

    def on_joined(self, peer_id: PlayerId) -> None:
        _out(f"* joined: {peer_id}  (peers: {len(self._pool.peers)})")

    def on_left(self, peer_id: PlayerId) -> None:
        self._buffers.pop(peer_id, None)
        _out(f"* left:   {peer_id}  (peers: {len(self._pool.peers)})")


def _resolve(pool: ConnectionPool, prefix: str) -> PlayerId | None:
    matches = [p for p in pool.peers if p.startswith(prefix)]
    if len(matches) == 1:
        return matches[0]
    _out(f"! peer '{prefix}' {'not found' if not matches else 'is ambiguous'}")
    return None


async def _handle(pool: ConnectionPool, line: str) -> bool:
    """處理一行輸入；回傳 False 表示要離開。"""
    cmd, _, rest = line.partition(" ")
    try:
        match cmd:
            case "/quit":
                return False
            case "/peers":
                _out(f"peers ({len(pool.peers)}): " + ", ".join(sorted(pool.peers)))
            case "/connect":
                host, port = rest.split()
                _out(f"* connected: {await pool.connect(host, int(port))}")
            case "/to":
                prefix, _, text = rest.partition(" ")
                if (pid := _resolve(pool, prefix)) is not None:
                    pool.send(pid, text.encode() + b"\n")
            case "/big":
                size = int(float(rest or "1") * 1024 * 1024)
                if not pool.peers:
                    _out("! no peers")
                    return True
                start = time.perf_counter()
                pool.broadcast(b"x" * size + b"\n")
                await pool.drain()
                secs = time.perf_counter() - start
                _out(f"* sent {size:,} bytes to {len(pool.peers)} peer(s) in {secs:.2f}s")
            case _ if cmd.startswith("/"):
                _out("! unknown command (see module docstring)")
            case _:
                pool.broadcast(line.encode() + b"\n")
    except (ValueError, OSError, TimeoutError, P2PError) as exc:
        _out(f"! {type(exc).__name__}: {exc}")
    return True


def _start_stdin_thread(loop: asyncio.AbstractEventLoop, queue: asyncio.Queue[str | None]) -> None:
    """在另一條執行緒讀 stdin，再交給 event loop（Windows 也能用）。"""

    def reader() -> None:
        for line in sys.stdin:
            loop.call_soon_threadsafe(queue.put_nowait, line.rstrip("\r\n"))
        loop.call_soon_threadsafe(queue.put_nowait, None)

    threading.Thread(target=reader, name="stdin", daemon=True).start()


async def _run(args: argparse.Namespace) -> None:
    pool = ConnectionPool(
        args.id,
        room=args.room,
        port=args.port,
        discovery=not args.no_discovery,
        discovery_port=args.discovery_port,
    )
    chat = _LineChat(pool)
    pool.add_data_handler(chat.on_data)
    pool.add_peer_joined_handler(chat.on_joined)
    pool.add_peer_left_handler(chat.on_left)
    await pool.start()
    ips = ", ".join(_local_ips()) or "?"
    _out(f"peer_id: {pool.peer_id}")
    _out(f"room:    {pool.room}")
    _out(f"listen:  TCP {pool.listen_port}  (IP: {ips})")
    _out(f"手動連線：/connect <IP> {pool.listen_port}    說明：/quit 離開")
    for target in args.connect:
        await _handle(pool, f"/connect {target.replace(':', ' ')}")

    queue: asyncio.Queue[str | None] = asyncio.Queue()
    _start_stdin_thread(asyncio.get_running_loop(), queue)
    try:
        while (line := await queue.get()) is not None:
            if line and not await _handle(pool, line):
                break
    finally:
        await pool.stop()


def main(argv: list[str] | None = None) -> None:
    """命令列進入點。"""
    parser = argparse.ArgumentParser(
        prog="python -m pretend2paint.p2p", description="P2P 實機測試工具"
    )
    parser.add_argument("--id", help="自己的 peer id（預設自動產生）")
    parser.add_argument("--room", default=DEFAULT_ROOM, help="room 名稱")
    parser.add_argument("--port", type=int, default=0, help="TCP port（預設由系統挑）")
    parser.add_argument("--discovery-port", type=int, default=DEFAULT_DISCOVERY_PORT)
    parser.add_argument("--no-discovery", action="store_true", help="關閉 UDP discovery")
    parser.add_argument(
        "--connect", action="append", default=[], metavar="HOST:PORT", help="啟動後手動連線"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="顯示 debug log")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(_run(args))


if __name__ == "__main__":
    main()
