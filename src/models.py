"""数据模型: 一条新闻/项目条目"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class NewsItem:
    title: str
    url: str
    source: str                     # 来源名, 如 GitHub / Hacker News / 机器之心
    category: str                   # github | domestic | international
    published: str = ""             # YYYY-MM-DD
    summary: str = ""               # 摘要(2-3句)
    key_points: list[str] = field(default_factory=list)   # 内容要点
    effect: str = ""                # 实现了什么效果
    repro_level: str = ""           # 内网可复现性: 高 | 中 | 低 | ""
    repro_note: str = ""            # 复现说明
    image_url: str = ""             # 配图(远程或本地相对路径)
    heat: str = ""                  # 热度, 如 "⭐ ~40.1k" / "HN 391分"
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "NewsItem":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


CATEGORY_NAMES = {
    "github": "GitHub 增速榜",
    "domestic": "国内论坛精选",
    "international": "国际论坛精选",
}
CATEGORY_ORDER = ["github", "domestic", "international"]
