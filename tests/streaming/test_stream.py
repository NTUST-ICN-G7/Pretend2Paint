import json
import struct
import unittest

from pretend2paint.common.types import Phase
from pretend2paint.streaming import (
    MAX_PAYLOAD_SIZE,
    PacketType,
    StreamManager,
    StreamPacket,
    StreamPacketDecoder,
)
from pretend2paint.streaming.protocol import (
    BROADCAST_TYPES,
    PACKET_TYPES,
    REQUIRED_FIELDS,
    packet_name,
)


class MockConnectionPool:
    """模擬 P2P Infra 的連線池，用於攔截測試發送出去的封包。"""

    def __init__(self):
        self.sent = []  # (peer_id, bytes)
        self.broadcasted = []  # bytes

    def send(self, peer_id, data):
        self.sent.append((peer_id, data))

    def send_many(self, peer_ids, data):
        peer_ids = list(peer_ids)
        if not peer_ids:
            raise ValueError("peer_ids must not be empty")
        for peer_id in peer_ids:
            self.send(peer_id, data)

    def broadcast(self, data):
        self.broadcasted.append(data)


def decode_one(data: bytes):
    decoder = StreamPacketDecoder()
    decoder.feed_data(data)
    packets = decoder.parse_packets()
    assert len(packets) == 1, packets
    return packets[0]


def raw_packet(packet_type: int, payload_bytes: bytes) -> bytes:
    """不經過 encode 直接組封包，用來製造壞資料。"""
    header = struct.pack("!2sBI", StreamPacket.MAGIC, packet_type, len(payload_bytes))
    return header + payload_bytes


class TestEncodeDecode(unittest.TestCase):
    def test_roundtrip_every_packet_type(self):
        for packet_type in sorted(PACKET_TYPES):
            with self.subTest(packet_type=packet_type):
                payload = {"k": "值", "n": 1}
                ptype, pdata = decode_one(StreamPacket.encode(packet_type, payload))
                self.assertEqual(ptype, packet_type)
                self.assertEqual(pdata, payload)

    def test_header_layout(self):
        data = StreamPacket.encode(PacketType.DRAW_STROKE, {"a": 1})
        self.assertEqual(data[:2], b"IC")
        self.assertEqual(data[2], PacketType.DRAW_STROKE)
        self.assertEqual(struct.unpack("!I", data[3:7])[0], len(data) - 7)

    def test_encode_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            StreamPacket.encode(0x7F, {})
        with self.assertRaises(ValueError):
            StreamPacket.encode(300, {})
        with self.assertRaises(TypeError):
            StreamPacket.encode(PacketType.DRAW_STROKE, [1, 2])  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            StreamPacket.encode(PacketType.DRAW_STROKE, {"a": {1, 2}})
        with self.assertRaises(ValueError):
            StreamPacket.encode(PacketType.CANVAS_SNAPSHOT, {"image": "x" * (MAX_PAYLOAD_SIZE + 1)})

    def test_packet_type_numbers_are_stable(self):
        """已發布的編號不可重新分配。"""
        self.assertEqual(
            {
                "DRAW_STROKE": 0x01,
                "SPY_SELECT_REF": 0x02,
                "ROUND_STATE_SYNC": 0x03,
                "CANVAS_SNAPSHOT": 0x04,
                "DEAL_WORD": 0x05,
                "SPY_REFERENCE": 0x06,
                "VOTE": 0x07,
                "SPY_GUESS": 0x08,
                "ROUND_RESULT": 0x09,
            },
            {member.name: member.value for member in PacketType},
        )

    def test_packet_type_is_int_enum_with_readable_names(self):
        packet_type, _ = decode_one(StreamPacket.encode(PacketType.VOTE, {"target": "x"}))
        self.assertIsInstance(packet_type, PacketType)
        self.assertEqual(packet_type, 7)  # 仍可當整數比較
        self.assertEqual(packet_name(7), "VOTE")
        self.assertEqual(packet_name(0x7F), "0x7f")

    def test_every_type_has_required_fields_entry(self):
        self.assertEqual(set(REQUIRED_FIELDS), set(PACKET_TYPES))


class TestFraming(unittest.TestCase):
    def test_sticky_packets(self):
        p1 = StreamPacket.encode(PacketType.DRAW_STROKE, {"id": 1})
        p2 = StreamPacket.encode(PacketType.ROUND_STATE_SYNC, {"state": "drawing"})

        decoder = StreamPacketDecoder()
        decoder.feed_data(p1 + p2)
        packets = decoder.parse_packets()

        self.assertEqual([p[0] for p in packets], [PacketType.DRAW_STROKE, 3])

    def test_half_packets(self):
        p = StreamPacket.encode(PacketType.SPY_SELECT_REF, {"index": 2})
        decoder = StreamPacketDecoder()

        decoder.feed_data(p[:5])
        self.assertEqual(decoder.parse_packets(), [])

        decoder.feed_data(p[5:])
        self.assertEqual(decoder.parse_packets(), [(PacketType.SPY_SELECT_REF, {"index": 2})])

    def test_byte_by_byte(self):
        p1 = StreamPacket.encode(PacketType.DEAL_WORD, {"text": "西瓜"})
        p2 = StreamPacket.encode(PacketType.VOTE, {"target": "bob"})
        decoder = StreamPacketDecoder()
        packets = []
        for byte in p1 + p2:
            decoder.feed_data(bytes([byte]))
            packets += decoder.parse_packets()
        self.assertEqual(
            packets,
            [(PacketType.DEAL_WORD, {"text": "西瓜"}), (PacketType.VOTE, {"target": "bob"})],
        )

    def test_large_payload_in_chunks(self):
        image = "A" * 200_000
        p = StreamPacket.encode(PacketType.CANVAS_SNAPSHOT, {"image": image})
        decoder = StreamPacketDecoder()
        packets = []
        for i in range(0, len(p), 1400):
            decoder.feed_data(p[i : i + 1400])
            packets += decoder.parse_packets()
        self.assertEqual(packets, [(PacketType.CANVAS_SNAPSHOT, {"image": image})])


class TestBadData(unittest.TestCase):
    """壞資料不可丟例外，也不可害後面的好封包被丟掉。"""

    def setUp(self):
        self.good = StreamPacket.encode(PacketType.VOTE, {"target": "bob"})
        self.expected = [(PacketType.VOTE, {"target": "bob"})]

    def parse(self, data: bytes):
        decoder = StreamPacketDecoder()
        decoder.feed_data(data)
        return decoder.parse_packets(), decoder

    def test_garbage_before_packet_resyncs(self):
        packets, _ = self.parse(b"\x00\xffgarbage" + self.good)
        self.assertEqual(packets, self.expected)

    def test_garbage_between_packets_resyncs(self):
        packets, _ = self.parse(self.good + b"\x01\x02\x03" + self.good)
        self.assertEqual(packets, self.expected * 2)

    def test_pure_garbage_does_not_grow_buffer(self):
        decoder = StreamPacketDecoder()
        for _ in range(1000):
            decoder.feed_data(b"\x00" * 1024)
            self.assertEqual(decoder.parse_packets(), [])
        self.assertLessEqual(len(decoder.buffer), 1)

    def test_partial_magic_at_end_is_kept(self):
        decoder = StreamPacketDecoder()
        decoder.feed_data(b"junk" + self.good[:1])
        self.assertEqual(decoder.parse_packets(), [])
        decoder.feed_data(self.good[1:])
        self.assertEqual(decoder.parse_packets(), self.expected)

    def test_invalid_utf8_is_dropped(self):
        bad = raw_packet(PacketType.VOTE, b"\xff\xfe")
        packets, _ = self.parse(bad + self.good)
        self.assertEqual(packets, self.expected)

    def test_invalid_json_is_dropped(self):
        bad = raw_packet(PacketType.VOTE, b"{not json")
        packets, _ = self.parse(bad + self.good)
        self.assertEqual(packets, self.expected)

    def test_non_object_payload_is_dropped(self):
        for body in (b"[1, 2]", b'"str"', b"42", b"null"):
            with self.subTest(body=body):
                packets, _ = self.parse(raw_packet(PacketType.VOTE, body) + self.good)
                self.assertEqual(packets, self.expected)

    def test_deeply_nested_json_is_dropped(self):
        bad = raw_packet(PacketType.VOTE, b"[" * 100_000)
        packets, _ = self.parse(bad + self.good)
        self.assertEqual(packets, self.expected)

    def test_unknown_type_is_skipped(self):
        unknown = raw_packet(0x7F, json.dumps({"a": 1}).encode())
        packets, _ = self.parse(unknown + self.good)
        self.assertEqual(packets, self.expected)

    def test_oversized_length_does_not_block_stream(self):
        fake = StreamPacket.MAGIC + bytes([PacketType.VOTE]) + struct.pack("!I", 4_000_000_000)
        packets, decoder = self.parse(fake + self.good)
        self.assertEqual(packets, self.expected)
        self.assertLess(len(decoder.buffer), 64)


class TestManagerReceive(unittest.TestCase):
    def setUp(self):
        self.pool = MockConnectionPool()
        self.manager = StreamManager(self.pool)
        self.received = []
        self.manager.register_handler(
            PacketType.SPY_SELECT_REF, lambda peer, payload: self.received.append((peer, payload))
        )

    def test_dispatches_to_registered_handler(self):
        data = StreamPacket.encode(PacketType.SPY_SELECT_REF, {"index": 1})
        self.manager.handle_incoming_data("peer_001", data)
        self.assertEqual(self.received, [("peer_001", {"index": 1})])

    def test_multiple_handlers_all_called(self):
        second = []
        self.manager.register_handler(PacketType.SPY_SELECT_REF, lambda p, d: second.append(d))
        self.manager.handle_incoming_data(
            "p", StreamPacket.encode(PacketType.SPY_SELECT_REF, {"index": 0})
        )
        self.assertEqual(len(self.received), 1)
        self.assertEqual(second, [{"index": 0}])

    def test_unregistered_type_is_ignored(self):
        data = StreamPacket.encode(PacketType.VOTE, {"target": "x"})
        self.manager.handle_incoming_data("p", data)
        self.assertEqual(self.received, [])

    def test_register_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            self.manager.register_handler(0x7F, lambda p, d: None)

    def test_missing_required_field_is_dropped(self):
        self.manager.handle_incoming_data(
            "p", StreamPacket.encode(PacketType.SPY_SELECT_REF, {"target_author": "alice"})
        )
        self.assertEqual(self.received, [])

    def test_unknown_phase_in_round_state_is_dropped(self):
        got = []
        self.manager.register_handler(PacketType.ROUND_STATE_SYNC, lambda p, d: got.append(d))
        for state in ("dawing", 5, ["drawing"], {"a": 1}):
            with self.subTest(state=state):
                data = StreamPacket.encode(PacketType.ROUND_STATE_SYNC, {"state": state})
                self.manager.handle_incoming_data("host", data)
        self.manager.handle_incoming_data(
            "host", StreamPacket.encode(PacketType.ROUND_STATE_SYNC, {"state": "drawing"})
        )
        self.assertEqual(got, [{"state": "drawing"}])

    def test_handler_exception_does_not_break_others(self):
        def boom(peer, payload):
            raise RuntimeError("boom")

        manager = StreamManager(self.pool)
        got = []
        manager.register_handler(PacketType.VOTE, boom)
        manager.register_handler(PacketType.VOTE, lambda p, d: got.append(d))
        with self.assertLogs("pretend2paint.streaming.manager", level="ERROR"):
            manager.handle_incoming_data("p", StreamPacket.encode(PacketType.VOTE, {"target": "x"}))
        self.assertEqual(got, [{"target": "x"}])

    def test_bad_data_does_not_raise_and_connection_recovers(self):
        bad = raw_packet(PacketType.SPY_SELECT_REF, b"\xff")
        good = StreamPacket.encode(PacketType.SPY_SELECT_REF, {"index": 3})
        self.manager.handle_incoming_data("p", bad + b"junk" + good)
        self.assertEqual(self.received, [("p", {"index": 3})])

    def test_peers_have_independent_buffers(self):
        p = StreamPacket.encode(PacketType.SPY_SELECT_REF, {"index": 1})
        self.manager.handle_incoming_data("a", p[:6])
        self.manager.handle_incoming_data("b", p)
        self.manager.handle_incoming_data("a", p[6:])
        self.assertEqual(self.received, [("b", {"index": 1}), ("a", {"index": 1})])

    def test_remove_peer_discards_partial_packet(self):
        p = StreamPacket.encode(PacketType.SPY_SELECT_REF, {"index": 1})
        self.manager.handle_incoming_data("a", p[:6])
        self.manager.remove_peer("a")
        self.manager.handle_incoming_data("a", p)  # 重連後從乾淨的 buffer 開始
        self.assertEqual(self.received, [("a", {"index": 1})])
        self.manager.remove_peer("never-seen")  # 不存在的 peer 不可出錯


class TestManagerSend(unittest.TestCase):
    def setUp(self):
        self.pool = MockConnectionPool()
        self.manager = StreamManager(self.pool)

    def sent_to(self, peer_id):
        return [decode_one(data) for p, data in self.pool.sent if p == peer_id]

    def test_unicast_goes_to_each_target_only(self):
        self.manager.send_draw_stroke(["a", "b"], {"x": 1, "y": 2, "color": "red"})
        self.assertEqual([p for p, _ in self.pool.sent], ["a", "b"])
        self.assertEqual(self.pool.broadcasted, [])
        self.assertEqual(
            self.sent_to("a"), [(PacketType.DRAW_STROKE, {"x": 1, "y": 2, "color": "red"})]
        )

    def test_unicast_requires_explicit_targets(self):
        calls = [
            lambda t: self.manager.send_draw_stroke(t, {}),
            lambda t: self.manager.send_spy_selection(t, 0),
            lambda t: self.manager.send_canvas_snapshot(t, "img"),
            lambda t: self.manager.send_deal_word(t, "西瓜"),
            lambda t: self.manager.send_spy_reference(t, "img"),
            lambda t: self.manager.send_vote(t, "bob"),
            lambda t: self.manager.send_spy_guess(t, "西瓜"),
        ]
        for call in calls:
            with self.subTest(call=call):
                with self.assertRaises(ValueError):
                    call([])
                with self.assertRaises(TypeError):
                    call("host")  # 不可把字串當成 peer 清單
        self.assertEqual(self.pool.sent, [])

    def test_deal_word_and_spy_reference_need_exactly_one_target(self):
        with self.assertRaises(ValueError):
            self.manager.send_deal_word(["a", "b"], "西瓜")
        with self.assertRaises(ValueError):
            self.manager.send_spy_reference(["a", "b"], "img")
        self.assertEqual(self.pool.sent, [])

    def test_spy_selection_payload_is_index_not_author(self):
        self.manager.send_spy_selection(["host"], 2)
        self.assertEqual(self.sent_to("host"), [(PacketType.SPY_SELECT_REF, {"index": 2})])

    def test_deal_word_payload_has_no_role_fields(self):
        self.manager.send_deal_word(["a"], "兩個字的水果")
        self.assertEqual(self.sent_to("a"), [(PacketType.DEAL_WORD, {"text": "兩個字的水果"})])

    def test_spy_reference_payload_has_no_author(self):
        self.manager.send_spy_reference(["spy"], "img")
        self.assertEqual(self.sent_to("spy"), [(PacketType.SPY_REFERENCE, {"image": "img"})])

    def test_canvas_snapshot_optional_fields(self):
        self.manager.send_canvas_snapshot(["host"], "img")
        self.manager.send_canvas_snapshot(["a"], "img", author="bob", index=1, marked=True)
        self.assertEqual(self.sent_to("host")[0][1], {"image": "img"})
        self.assertEqual(
            self.sent_to("a")[0][1], {"image": "img", "author": "bob", "index": 1, "marked": True}
        )

    def test_vote_and_spy_guess(self):
        self.manager.send_vote(["host"], "bob")
        self.manager.send_spy_guess(["host"], "西瓜")
        self.assertEqual(
            self.sent_to("host"),
            [(PacketType.VOTE, {"target": "bob"}), (PacketType.SPY_GUESS, {"guess": "西瓜"})],
        )

    def test_broadcast_round_state_accepts_phase_enum(self):
        self.manager.broadcast_round_state(Phase.DRAWING)
        self.assertEqual(self.pool.sent, [])
        (data,) = self.pool.broadcasted
        self.assertEqual(decode_one(data), (PacketType.ROUND_STATE_SYNC, {"state": "drawing"}))

    def test_broadcast_round_state_rejects_unknown_phase(self):
        for bad in ("dawing", "", "DRAWING", 5, None):
            with self.subTest(state=bad), self.assertRaises(ValueError):
                self.manager.broadcast_round_state(bad)  # type: ignore[arg-type]
        self.assertEqual(self.pool.broadcasted, [])

    def test_broadcast_round_state_accepts_phase_value_string(self):
        self.manager.broadcast_round_state("voting")
        (data,) = self.pool.broadcasted
        self.assertEqual(decode_one(data), (PacketType.ROUND_STATE_SYNC, {"state": "voting"}))

    def test_broadcast_round_result(self):
        self.manager.broadcast_round_result("bob", "西瓜", {"alice": 1, "bob": -1})
        (data,) = self.pool.broadcasted
        self.assertEqual(
            decode_one(data),
            (
                PacketType.ROUND_RESULT,
                {"spy": "bob", "answer": "西瓜", "scores": {"alice": 1, "bob": -1}},
            ),
        )

    def test_secret_packets_cannot_be_broadcast(self):
        """ADR 0005：只有 BROADCAST_TYPES 可以廣播。"""
        self.assertEqual(BROADCAST_TYPES, {PacketType.ROUND_STATE_SYNC, PacketType.ROUND_RESULT})
        for packet_type in PACKET_TYPES - BROADCAST_TYPES:
            with self.subTest(packet_type=packet_type), self.assertRaises(ValueError):
                self.manager._broadcast(packet_type, {})
        self.assertEqual(self.pool.broadcasted, [])


class TestEndToEnd(unittest.TestCase):
    def test_round_result_reaches_player_handler(self):
        pool = MockConnectionPool()
        host, player = StreamManager(pool), StreamManager(MockConnectionPool())
        got = []
        player.register_handler(
            PacketType.ROUND_RESULT, lambda peer, data: got.append((peer, data))
        )
        scores = {"alice": 8, "bob": -3}
        drawings = [{"drawing_index": 1, "author_name": "Bob", "votes": 2, "marked": False}]
        violations = [{"player_id": "eve", "name": "Eve", "strikes": 2, "penalty": -15}]

        host.broadcast_round_result(
            "bob",
            "西瓜",
            scores,
            outcome="caught",
            hint="兩個字的水果",
            spy_guess="哈密瓜",
            guess_correct=False,
            drawings=drawings,
            violations=violations,
            removed_players=["eve"],
        )
        host.broadcast_round_result(
            "bob", "西瓜", scores, outcome="escaped", hint="兩個字的水果", drawings=[]
        )
        host.broadcast_round_result(
            None, None, scores, outcome="void", violations=violations, removed_players=["eve"]
        )
        host.broadcast_round_result("bob", "西瓜", scores)

        self.assertEqual(pool.sent, [])
        for data in pool.broadcasted:
            player.handle_incoming_data("host", data)
        caught = {
            "spy": "bob",
            "answer": "西瓜",
            "scores": scores,
            "outcome": "caught",
            "hint": "兩個字的水果",
            "spy_guess": "哈密瓜",
            "guess_correct": False,
            "drawings": drawings,
            "violations": violations,
            "removed_players": ["eve"],
        }
        self.assertEqual(
            got,
            [
                ("host", caught),
                (
                    "host",
                    caught
                    | {
                        "outcome": "escaped",
                        "spy_guess": None,
                        "guess_correct": None,
                        "drawings": [],
                        "violations": [],
                        "removed_players": [],
                    },
                ),
                (
                    "host",
                    {
                        "outcome": "void",
                        "scores": scores,
                        "violations": violations,
                        "removed_players": ["eve"],
                    },
                ),
                ("host", {"spy": "bob", "answer": "西瓜", "scores": scores}),
            ],
        )

    def test_round_result_rejects_invalid_extensions(self):
        pool = MockConnectionPool()
        manager = StreamManager(pool)
        got = []
        manager.register_handler(PacketType.ROUND_RESULT, lambda peer, data: got.append(data))
        with self.assertRaises(ValueError):
            manager.broadcast_round_result("bob", "西瓜", {}, outcome="void")
        with self.assertRaises(ValueError):
            manager.broadcast_round_result("bob", "西瓜", {}, outcome="unknown")
        with self.assertRaises(ValueError):
            manager.broadcast_round_result("bob", "西瓜", {}, hint="水果")
        self.assertEqual(pool.broadcasted, [])

        payload = {"outcome": "void", "scores": {}, "violations": [], "removed_players": []}
        for malformed in (
            payload | {"outcome": "unknown"},
            payload | {"spy": "bob"},
            payload | {"removed_players": None},
            payload | {"outcome": "tie"},
        ):
            manager.handle_incoming_data(
                "host", StreamPacket.encode(PacketType.ROUND_RESULT, malformed)
            )
        self.assertEqual(got, [])

    def test_host_deals_word_and_player_receives_it(self):
        """房主送出的 bytes 餵進玩家的 StreamManager，玩家的 handler 會收到。"""
        host_pool, player_pool = MockConnectionPool(), MockConnectionPool()
        host, player = StreamManager(host_pool), StreamManager(player_pool)
        got = []
        player.register_handler(PacketType.DEAL_WORD, lambda peer, data: got.append((peer, data)))

        host.send_deal_word(["player"], "西瓜")
        ((_, data),) = host_pool.sent
        player.handle_incoming_data("host", data[:4])
        player.handle_incoming_data("host", data[4:])

        self.assertEqual(got, [("host", {"text": "西瓜"})])


if __name__ == "__main__":
    unittest.main()
