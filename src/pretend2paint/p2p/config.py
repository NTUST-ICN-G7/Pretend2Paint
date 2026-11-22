"""P2P 的設定常數，集中在這裡，不要散落在各檔案。"""

from typing import Final

APP_ID: Final = "pretend2paint"
"""Discovery 與 handshake 用的應用程式識別字，用來忽略其他程式的封包。"""

PROTOCOL_VERSION: Final = 1
"""p2p 自己的版本號（handshake / discovery 格式），與 streaming 的封包格式無關。"""

DEFAULT_ROOM: Final = "default"
"""預設的房間（網路分區）名稱。同一區網內不同 room 的節點不會互連。"""

# ---------------------------------------------------------------- TCP
DEFAULT_LISTEN_HOST: Final = "0.0.0.0"
DEFAULT_TCP_PORT: Final = 0
"""0 = 由作業系統挑一個空的 port，實際 port 會透過 discovery 公告。"""

CONNECT_TIMEOUT: Final = 3.0
"""主動連線的逾時秒數。"""

HANDSHAKE_TIMEOUT: Final = 3.0
"""等待對方 handshake 的逾時秒數。"""

READ_CHUNK_SIZE: Final = 64 * 1024
"""每次從 socket 讀取的最大 bytes 數。"""

MAX_WRITE_BUFFER: Final = 32 * 1024 * 1024
"""每條連線尚未送出的資料上限（bytes）。超過代表對方太久沒讀，直接斷線保護記憶體。"""

# ---------------------------------------------------------------- Handshake
HANDSHAKE_MAGIC: Final = b"P2PH"
"""Handshake frame 的開頭，用來辨識不是本程式的連線。"""

HANDSHAKE_MAX_SIZE: Final = 4 * 1024
"""Handshake JSON 的長度上限（bytes）。"""

# ---------------------------------------------------------------- UDP discovery
DEFAULT_DISCOVERY_PORT: Final = 50_505
"""UDP discovery 使用的 port（所有節點相同）。"""

DISCOVERY_BROADCAST_ADDR: Final = "255.255.255.255"

DISCOVERY_INTERVAL: Final = 1.0
"""每隔幾秒廣播一次自己的存在。"""

DISCOVERY_MAX_SIZE: Final = 1024
"""Discovery datagram 的長度上限（bytes）。"""
