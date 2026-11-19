protocol.py

StreamPacket.encode(packet_type: int, payload_dict: dict) -> bytes
用途：將事件型態與 Python 字典轉換成帶有 7-byte Header 的二進位封包。

StreamPacketDecoder

feed_data(data: bytes)：接收並累積從 TCP 讀取到的原始位元組。

parse_packets() -> list：解析緩衝區，自動處理半包/黏包，回傳解包後的 (packet_type, payload) 串列。


manager.py

handle_incoming_data(peer_id: str, raw_data: bytes)
用途：當 P2P 網路層收到資料時的唯一進入點。會自動透過 Decoder 解析並分發事件。

send_draw_stroke(target_peers: list, stroke_data: dict)
用途：廣播或發送畫筆軌跡給指定節點。

send_spy_selection(target_peers: list, target_author: str)
用途：間諜送出盲選參考圖的動作。



P2P Infra
當 TCP 收到來自某個節點的原始資料時，直接呼叫：
stream_manager.handle_incoming_data(peer_id, raw_bytes)

Canvas / UI
玩家繪圖時，發送筆畫座標：
stream_manager.send_draw_stroke(target_peers=[], stroke_data={"x": x, "y": y, "color": color})

Core
間諜選擇參考圖時，發送選擇動作：
stream_manager.send_spy_selection(target_peers=[], target_author="player_name")