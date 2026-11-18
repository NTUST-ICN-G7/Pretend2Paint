import unittest
from protocol import StreamPacket, StreamPacketDecoder, PacketType
from manager import StreamManager

class MockConnectionPool:
    """模擬 P2P Infra 的連線池，用於攔截測試發送出去的封包"""
    def __init__(self):
        self.sent_packets = []

    def broadcast(self, packet: bytes, targets=None):
        self.sent_packets.append((packet, targets))

class TestStreamingModule(unittest.TestCase):
    
    def test_encode_and_decode_normal(self):
        """測試一般封包的編碼與解碼"""
        payload = {"x": 100, "y": 200, "color": "red"}
        encoded_data = StreamPacket.encode(PacketType.DRAW_STROKE, payload)
        
        decoder = StreamPacketDecoder()
        decoder.feed_data(encoded_data)
        packets = decoder.parse_packets()
        
        self.assertEqual(len(packets), 1)
        ptype, pdata = packets[0]
        self.assertEqual(ptype, PacketType.DRAW_STROKE)
        self.assertEqual(pdata, payload)

    def test_sticky_packets(self):
        """測試 TCP 黏包狀況：多個封包黏在同一個 buffer 裡被一次餵入"""
        p1 = StreamPacket.encode(PacketType.DRAW_STROKE, {"id": 1})
        p2 = StreamPacket.encode(PacketType.ROUND_STATE_SYNC, {"state": "drawing"})
        
        decoder = StreamPacketDecoder()
        # 將兩個封包黏在一起餵給 decoder
        decoder.feed_data(p1 + p2)
        packets = decoder.parse_packets()
        
        # 應成功拆解出 2 個獨立封包
        self.assertEqual(len(packets), 2)
        self.assertEqual(packets[0][0], PacketType.DRAW_STROKE)
        self.assertEqual(packets[1][0], PacketType.ROUND_STATE_SYNC)

    def test_half_packets(self):
        """測試 TCP 半包狀況：封包被切成兩半、分批送達"""
        p = StreamPacket.encode(PacketType.SPY_SELECT_REF, {"target_author": "player_A"})
        half_1 = p[:5]  # 只傳送前 5 個 bytes (不完整)
        half_2 = p[5:]  # 剩餘的 bytes
        
        decoder = StreamPacketDecoder()
        
        # 第一批資料（半包），此時不應解析出任何完整封包
        decoder.feed_data(half_1)
        self.assertEqual(len(decoder.parse_packets()), 0)
        
        # 第二批資料送達（補齊），此時應能成功還原封包
        decoder.feed_data(half_2)
        packets = decoder.parse_packets()
        self.assertEqual(len(packets), 1)
        self.assertEqual(packets[0][1]["target_author"], "player_A")

    def test_stream_manager_dispatch(self):
        """測試 StreamManager 的接收分發與發送功能"""
        pool = MockConnectionPool()
        manager = StreamManager(pool)
        
        payload = {"target_author": "Alice"}
        packet = StreamPacket.encode(PacketType.SPY_SELECT_REF, payload)
        
        # 模擬收到來自 peer_001 的資料並自動分發
        manager.handle_incoming_data("peer_001", packet)
        
        # 測試對外發送畫筆軌跡
        manager.send_draw_stroke(["peer_002"], {"brush": "line"})
        self.assertEqual(len(pool.sent_packets), 1)

if __name__ == '__main__':
    unittest.main()