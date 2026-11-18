import logging
from protocol import StreamPacketDecoder, PacketType, StreamPacket

class StreamManager:
    def __init__(self, p2p_connection_pool):
        """
        :param p2p_connection_pool: P2P Infra 提供的連線池物件，需具備 broadcast 或 send 方法
        """
        self.pool = p2p_connection_pool
        self.decoders = {}  # 針對每個 peer_id 維護一個 decoder

    def handle_incoming_data(self, peer_id: str, raw_data: bytes):
        """
        當 P2P Infra 收到來自某個 Peer 的 TCP 資料時呼叫此方法
        """
        if peer_id not in self.decoders:
            self.decoders[peer_id] = StreamPacketDecoder()

        decoder = self.decoders[peer_id]
        decoder.feed_data(raw_data)
        
        # 解析出所有完整封包
        packets = decoder.parse_packets()
        for packet_type, payload in packets:
            self._dispatch_packet(peer_id, packet_type, payload)

    def _dispatch_packet(self, peer_id: str, packet_type: int, payload: dict):
        """
        根據封包類型分發給對應的業務邏輯處理器 (Core / Canvas)
        """
        if packet_type == PacketType.DRAW_STROKE:
            logging.info(f"收到來自 {peer_id} 的畫筆軌跡資料")
            # TODO: 觸發 Canvas UI 渲染該筆畫
            
        elif packet_type == PacketType.SPY_SELECT_REF:
            logging.info(f"間諜 {peer_id} 選擇了參考圖: {payload.get('target_author')}")
            # TODO: 觸發 Core 業務邏輯，標記該張參考圖
            
        elif packet_type == PacketType.ROUND_STATE_SYNC:
            logging.info(f"同步回合狀態: {payload.get('state')}")

    def send_draw_stroke(self, target_peers: list, stroke_data: dict):
        """
        傳送畫筆座標給指定節點或廣播
        """
        packet = StreamPacket.encode(PacketType.DRAW_STROKE, stroke_data)
        self.pool.broadcast(packet, targets=target_peers)

    def send_spy_selection(self, target_peers: list, target_author: str):
        """
        間諜送出盲選參考圖的動作
        """
        payload = {"target_author": target_author}
        packet = StreamPacket.encode(PacketType.SPY_SELECT_REF, payload)
        self.pool.broadcast(packet, targets=target_peers)