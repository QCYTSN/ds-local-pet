from __future__ import annotations

PERSONALITIES = {
    "standard": "标准大肥鱼",
    "sharp": "轻微毒舌",
    "gentle": "温和陪伴",
    "community": "社区梗",
}


def normalize_personality(value: str) -> str:
    return value if value in PERSONALITIES else "standard"
