"""arXiv 采集器 (官方 Atom API)"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from ..models import NewsItem
from .base import http_get, clean_html

log = logging.getLogger(__name__)

NS = {"a": "http://www.w3.org/2005/Atom"}


def collect(cfg: dict) -> list[NewsItem]:
    a = cfg.get("arxiv", {})
    cutoff = datetime.now(timezone.utc) - timedelta(days=a.get("days", 14))
    max_results = a.get("max_results", 8)

    seen: set[str] = set()
    items: list[NewsItem] = []
    for q in a.get("queries", []):
        url = ("http://export.arxiv.org/api/query?search_query="
               + quote(q)
               + f"&sortBy=submittedDate&sortOrder=descending&max_results={max_results}")
        try:
            root = ET.fromstring(http_get(url, cfg).text)
        except Exception as e:
            log.warning("arXiv 查询失败 [%s]: %s", q, e)
            continue
        for entry in root.findall("a:entry", NS):
            aid = (entry.findtext("a:id", "", NS) or "").strip()
            if not aid or aid in seen:
                continue
            published = (entry.findtext("a:published", "", NS) or "")[:10]
            try:
                dt = datetime.fromisoformat(published).replace(tzinfo=timezone.utc)
                if dt < cutoff:
                    continue
            except ValueError:
                pass
            seen.add(aid)
            title = clean_html(entry.findtext("a:title", "", NS))
            abstract = clean_html(entry.findtext("a:summary", "", NS))
            cats = [c.get("term", "") for c in entry.findall("a:category", NS)]
            items.append(NewsItem(
                title=title,
                url=aid,
                source="arXiv",
                category="international",
                published=published,
                summary=abstract[:280] + ("…" if len(abstract) > 280 else ""),
                heat=" · ".join(cats[:3]),
                tags=["paper"],
            ))
    return items
