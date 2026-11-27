"""Drawing ↔ JSON 可序列化的 dict。放進訊息 payload 前後使用。"""

import math
import re
from collections.abc import Mapping
from typing import Any

from pretend2paint.common.types import Drawing, Stroke

MAX_STROKES = 500
MAX_POINTS = 5000
"""整張畫所有筆畫加起來的點數上限，防止超大封包。"""
_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


class PayloadError(ValueError):
    """收到的 payload 格式不合法。伺服器遇到時只記 log 並丟掉。"""


def drawing_to_payload(drawing: Drawing) -> dict[str, Any]:
    """把 Drawing 轉成可以放進 JSON 的 dict。"""
    return {
        "strokes": [
            {"color": s.color, "width": s.width, "points": [[x, y] for x, y in s.points]}
            for s in drawing.strokes
        ]
    }


def drawing_from_payload(data: Any) -> Drawing:
    """從 dict 還原 Drawing；格式錯、超過上限或座標不在 0～1 時丟 PayloadError。"""
    if not isinstance(data, Mapping) or not isinstance(data.get("strokes"), list):
        raise PayloadError("drawing 必須是含 strokes 清單的物件")
    raw_strokes = data["strokes"]
    if len(raw_strokes) > MAX_STROKES:
        raise PayloadError(f"筆畫數超過上限 {MAX_STROKES}")

    strokes: list[Stroke] = []
    total_points = 0
    for raw in raw_strokes:
        if not isinstance(raw, Mapping):
            raise PayloadError("stroke 必須是物件")
        color, width, points = raw.get("color"), raw.get("width"), raw.get("points")
        if not isinstance(color, str) or not _COLOR.match(color):
            raise PayloadError("color 必須是 #RRGGBB")
        if not _is_unit_number(width) or width == 0:
            raise PayloadError("width 必須是 0～1 之間的正數")
        if not isinstance(points, list) or not points:
            raise PayloadError("points 必須是非空清單")
        total_points += len(points)
        if total_points > MAX_POINTS:
            raise PayloadError(f"點數超過上限 {MAX_POINTS}")
        parsed: list[tuple[float, float]] = []
        for p in points:
            if not (isinstance(p, list | tuple) and len(p) == 2):
                raise PayloadError("每個點必須是 [x, y]")
            x, y = p
            if not (_is_unit_number(x) and _is_unit_number(y)):
                raise PayloadError("座標必須在 0～1 之間")
            parsed.append((float(x), float(y)))
        strokes.append(Stroke(color=color, width=float(width), points=tuple(parsed)))
    return Drawing(strokes=tuple(strokes))


def _is_unit_number(value: Any) -> bool:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
        and 0 <= value <= 1
    )
