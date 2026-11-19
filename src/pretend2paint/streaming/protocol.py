import json
import logging
import struct

logger = logging.getLogger(__name__)


class PacketType:
    DRAW_STROKE = 0x01
    SPY_SELECT_REF = 0x02
    ROUND_STATE_SYNC = 0x03
    CANVAS_SNAPSHOT = 0x04


class StreamPacket:
    MAGIC = b"\x49\x43"  # "IC" 代表 ICN-G7

    @staticmethod
    def encode(packet_type: int, payload_dict: dict) -> bytes:
        """
        將字典資料編碼為帶有 Header 的二進位封包
        """
        payload_bytes = json.dumps(payload_dict, ensure_ascii=False).encode("utf-8")
        payload_len = len(payload_bytes)

        # 格式：2bytes Magic, 1byte Type, 4bytes Length (Network byte order: big-endian)
        header = struct.pack("!2sBI", StreamPacket.MAGIC, packet_type, payload_len)
        return header + payload_bytes


class StreamPacketDecoder:
    """
    處理 TCP 串流的累加與解包器，完美解決黏包與半包問題
    """

    def __init__(self):
        self.buffer = bytearray()

    def feed_data(self, data: bytes):
        self.buffer.extend(data)

    def parse_packets(self):
        packets = []
        header_size = 7  # 2 (Magic) + 1 (Type) + 4 (Length)

        while len(self.buffer) >= header_size:
            # 檢查 Magic Number
            if self.buffer[0:2] != StreamPacket.MAGIC:
                logger.error("Magic number mismatch! Flushing corrupted stream buffer.")
                self.buffer.clear()
                break

            # 解析 Type 與 Length
            packet_type = self.buffer[2]
            payload_len = struct.unpack("!I", self.buffer[3:7])[0]

            total_packet_size = header_size + payload_len

            # 如果緩衝區內的資料不足一個完整封包，等待更多資料進來（半包處理）
            if len(self.buffer) < total_packet_size:
                break

            # 擷取 Payload
            payload_bytes = self.buffer[header_size:total_packet_size]
            try:
                payload_dict = json.loads(payload_bytes.decode("utf-8"))
                packets.append((packet_type, payload_dict))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON payload: {e}")

            # 從 buffer 中移除已處理的封包
            self.buffer = self.buffer[total_packet_size:]

        return packets
