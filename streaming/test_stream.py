import socket
import threading
import time
from protocol import StreamProtocol

def dummy_server(host='127.0.0.1', port=8888):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(1)
    conn, addr = server_sock.accept()
    received_msg = StreamProtocol.unpack_message(conn)
    print(f"[Server] 成功收到訊息: {received_msg}")
    conn.close()
    server_sock.close()

if __name__ == "__main__":
    t = threading.Thread(target=dummy_server)
    t.daemon = True
    t.start()
    time.sleep(0.5)
    
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect(('127.0.0.1', 8888))
    packed_data = StreamProtocol.pack_message("DRAW", {"x": 120, "y": 250})
    client_sock.sendall(packed_data)
    client_sock.close()
    t.join()
    print("[Test] 測試完成！")