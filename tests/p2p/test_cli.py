"""`python -m pretend2paint.p2p` 實機測試工具的單元測試。"""

import asyncio

import pytest

from pretend2paint.p2p import ConnectionPool
from pretend2paint.p2p.__main__ import _handle, _LineChat


def test_line_chat_splits_stream(capsys: pytest.CaptureFixture[str]) -> None:
    chat = _LineChat(ConnectionPool("me", discovery=False))
    chat.on_data("peer1234567", b"hel")
    chat.on_data("peer1234567", b"lo\nwor")
    chat.on_data("peer1234567", b"ld\n" + b"x" * 500 + b"\n")
    out = capsys.readouterr().out.splitlines()
    assert out == ["[peer1234] hello", "[peer1234] world", "[peer1234] <500 bytes>"]


def test_handle_commands(capsys: pytest.CaptureFixture[str]) -> None:
    async def scenario() -> None:
        a = ConnectionPool("a", host="127.0.0.1", discovery=False)
        b = ConnectionPool("b", host="127.0.0.1", discovery=False)
        got = bytearray()
        b.add_data_handler(lambda _pid, data: got.extend(data))
        await a.start()
        await b.start()
        try:
            assert await _handle(a, f"/connect 127.0.0.1 {b.listen_port}")
            assert await _handle(a, "/to b hi")
            assert await _handle(a, "everyone")
            assert await _handle(a, "/big 0.01")
            assert await _handle(a, "/to zzz nope")
            assert await _handle(a, "/connect bad")
            assert await _handle(a, "/peers")
            assert not await _handle(a, "/quit")
            async with asyncio.timeout(3):
                while got.count(b"\n") < 3:
                    await asyncio.sleep(0.01)
            assert got.startswith(b"hi\neveryone\n")
        finally:
            await a.stop()
            await b.stop()

    asyncio.run(scenario())
    out = capsys.readouterr().out
    assert "connected: b" in out
    assert "not found" in out
    assert "ValueError" in out
    assert "peers (1): b" in out
