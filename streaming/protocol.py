import json
import struct

class StreamProtocol:
    @staticmethod
    def pack_message(msg_type: str, payload: dict) -> bytes:
        message_data = {"type": msg_type, "payload": payload}
        json_bytes = json.dumps(message_data).encode('utf-8')
        header = struct.pack('!I', len(json_bytes))
        return header + json_bytes

    @staticmethod
    def unpack_message(sock) -> dict | None:
        try:
            raw_header = sock.recv(4)
            if not raw_header or len(raw_header) < 4:
                return None
            msg_length = struct.unpack('!I', raw_header)[0]
            data = bytearray()
            while len(data) < msg_length:
                packet = sock.recv(msg_length - len(data))
                if not packet:
                    return None
                data.extend(packet)
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            print(f"[Streaming Error] Unpack failed: {e}")
            return None