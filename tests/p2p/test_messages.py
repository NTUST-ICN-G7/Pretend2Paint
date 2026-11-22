import json

import pytest

from pretend2paint.p2p.messages import (
    HANDSHAKE_HEADER_SIZE,
    Announcement,
    Hello,
    MessageError,
    decode_announcement,
    decode_hello,
    encode_announcement,
    encode_hello,
    parse_hello_header,
)


def test_hello_roundtrip() -> None:
    raw = encode_hello(Hello("abc", "room1", 1234))
    length = parse_hello_header(raw[:HANDSHAKE_HEADER_SIZE])
    body = raw[HANDSHAKE_HEADER_SIZE:]
    assert length == len(body)
    assert decode_hello(body) == Hello("abc", "room1", 1234)


def test_hello_bad_magic() -> None:
    with pytest.raises(MessageError):
        parse_hello_header(b"XXXX\x00\x10")


def test_hello_too_large() -> None:
    with pytest.raises(MessageError):
        parse_hello_header(b"P2PH\xff\xff")


def test_announcement_roundtrip() -> None:
    ann = Announcement("abc", "default", 5000)
    assert decode_announcement(encode_announcement(ann)) == ann


@pytest.mark.parametrize(
    "data",
    [
        b"not json",
        b"[]",
        json.dumps({"app": "other", "v": 1, "kind": "announce"}).encode(),
        json.dumps(
            {"app": "pretend2paint", "v": 99, "kind": "announce", "peer_id": "a", "room": "r"}
        ).encode(),
        json.dumps(
            {
                "app": "pretend2paint",
                "v": 1,
                "kind": "announce",
                "peer_id": "a",
                "room": "r",
                "port": 0,
            }
        ).encode(),
        json.dumps(
            {
                "app": "pretend2paint",
                "v": 1,
                "kind": "hello",
                "peer_id": "a",
                "room": "r",
                "port": 1,
            }
        ).encode(),
        b"x" * 5000,
    ],
)
def test_announcement_rejects_invalid(data: bytes) -> None:
    with pytest.raises(MessageError):
        decode_announcement(data)
