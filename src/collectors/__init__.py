"""汇总所有采集器"""
from __future__ import annotations

import logging

from ..models import NewsItem
from . import github, hackernews, arxiv, rss_feeds

log = logging.getLogger(__name__)

_COLLECTORS = [
    ("github", github.collect),
    ("hackernews", hackernews.collect),
    ("arxiv", arxiv.collect),
    ("rss_feeds", rss_feeds.collect),
]


def collect_all(cfg: dict) -> list[NewsItem]:
    """逐个采集,单源失败不影响整体;按 URL 去重。"""
    all_items: list[NewsItem] = []
    for name, fn in _COLLECTORS:
        section = cfg.get(name, {})
        # rss_feeds 是列表(单个源各自带 enabled), 其余采集器是 dict
        if isinstance(section, dict) and not section.get("enabled", True):
            continue
        try:
            got = fn(cfg)
            log.info("采集器 %-12s 收录 %d 条", name, len(got))
            all_items.extend(got)
        except Exception as e:
            log.error("采集器 %s 失败,已跳过: %s", name, e)

    seen: set[str] = set()
    deduped: list[NewsItem] = []
    for it in all_items:
        key = it.url.rstrip("/").lower() or it.title
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)
    return deduped
