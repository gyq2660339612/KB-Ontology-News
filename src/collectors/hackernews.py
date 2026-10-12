"""Hacker News 采集器 (Algolia 官方 API,无需翻墙工具之外的配置)"""
from __future__ import annotations

import logging
import time

from ..models import NewsItem
from .base import http_get

log = logging.getLogger(__name__)

ALGOLIA = "https://hn.algolia.com/api/v1/search_by_date"


def collect(cfg: dict) -> list[NewsItem]:
    h = cfg.get("hackernews", {})
    min_points = h.get("min_points", 10)
    since_ts = int(time.time()) - h.get("days", 14) * 86400

    seen: set[str] = set()
    items: list[NewsItem] = []
    for q in h.get("queries", []):
        params = {
            "query": q,
            "tags": "story",
            # 限定只匹配标题: Algolia 默认会匹配正文并做容错, 短词(如 RAG)噪声极大
            "restrictSearchableAttributes": "title",
            "numericFilters": f"created_at_i>{since_ts},points>{min_points}",
            "hitsPerPage": 8,
        }
        try:
            data = http_get(ALGOLIA, cfg, params=params).json()
        except Exception as e:
            log.warning("HN 查询失败 [%s]: %s", q, e)
            continue
        for hit in data.get("hits", []):
            oid = hit.get("objectID")
            title = hit.get("title", "")
            if not oid or oid in seen:
                continue
            seen.add(oid)
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={oid}"
            points = hit.get("points", 0)
            comments = hit.get("num_comments", 0)
            items.append(NewsItem(
                title=title,
                url=url,
                source="Hacker News",
                category="international",
                published=(hit.get("created_at") or "")[:10],
                heat=f"HN {points} 分 · {comments} 评论",
                tags=[q],
            ))
    items.sort(key=lambda x: x.published, reverse=True)
    return items
