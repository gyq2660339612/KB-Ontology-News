"""GitHub 采集器 —— 增速导向

两个来源:
1. GitHub Trending 日榜/周榜: 官方"涨星最快"榜单, 按主题关键词过滤命中项
2. 新锐项目搜索: 最近 N 天创建且 star 数达标的仓库(GitHub Search API)

成熟旗舰项目(如 LightRAG/GraphRAG)不再每日重复推荐;
如需跟踪其 star 日增/周增, 可利用 data/raw_*.json 的历史快照做差分(后续版本)。
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone

from ..models import NewsItem
from .base import http_get

log = logging.getLogger(__name__)

API = "https://api.github.com"
TRENDING = "https://github.com/trending"


def _headers(cfg: dict) -> dict:
    h = {"Accept": "application/vnd.github+json"}
    token = os.environ.get(cfg.get("github", {}).get("token_env", "GITHUB_TOKEN"), "")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _og_image(full_name: str) -> str:
    return f"https://opengraph.githubassets.com/1/{full_name}"


def _match_topic(text: str, keywords: list[str]) -> bool:
    """主题命中: 关键词直接匹配, 或 agent 与 memory/context/knowledge 共现
    (用于捕捉 claude-mem 这类不含领域关键词但确属本主题的项目)。"""
    t = text.lower()
    for k in keywords:
        if k.lower() in t:
            return True
    if "agent" in t and any(w in t for w in ("memory", "context", "knowledge")):
        return True
    return False


def _trending(cfg: dict, keywords: list[str]) -> list[NewsItem]:
    today = datetime.now().strftime("%Y-%m-%d")
    items: list[NewsItem] = []
    for since in ("daily", "weekly"):
        try:
            r = http_get(f"{TRENDING}?since={since}", cfg)
        except Exception as e:
            log.warning("GitHub Trending %s 抓取失败: %s", since, e)
            continue
        articles = re.findall(r'<article class="Box-row">(.*?)</article>', r.text, re.S)
        for a in articles:
            m = re.search(r'href="/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"', a)
            if not m:
                continue
            name = m.group(1)
            if name.startswith("sponsors/"):  # 赞助位, 跳过
                continue
            dm = re.search(r'<p class="[^"]*color-fg-muted[^"]*">(.*?)</p>', a, re.S)
            desc = re.sub(r"<[^>]+>", "", dm.group(1)).strip() if dm else ""
            if not _match_topic(f"{name} {desc}", keywords):
                continue
            gm = re.search(r"([\d,]+)\s*stars\s*(today|this week)", a)
            heat = ""
            if gm:
                unit = "日" if gm.group(2) == "today" else "周"
                heat = f"🔥 涨星 +{gm.group(1)}/{unit}"
            items.append(NewsItem(
                title=name,
                url=f"https://github.com/{name}",
                source="GitHub Trending",
                category="github",
                published=today,
                summary=desc,
                image_url=_og_image(name),
                heat=heat,
                tags=["trending", since],
            ))
    return items


def _newborn(cfg: dict) -> list[NewsItem]:
    """新锐项目: 近期创建 + 涨星快(star 总量/创建天数 = 隐含增速)。"""
    n = cfg.get("github", {}).get("newborn", {})
    since = (datetime.now(timezone.utc)
             - timedelta(days=n.get("created_within_days", 120))).strftime("%Y-%m-%d")
    min_stars = n.get("min_stars", 500)
    items: list[NewsItem] = []
    for q in n.get("queries", []):
        params = {
            "q": f"{q} created:>={since} stars:>={min_stars}",
            "sort": "stars", "order": "desc", "per_page": 5,
        }
        try:
            data = http_get(f"{API}/search/repositories", cfg,
                            headers=_headers(cfg), params=params).json()
        except Exception as e:
            log.warning("GitHub 新锐搜索失败 [%s]: %s", q, e)
            continue
        for r in data.get("items", []):
            stars = r.get("stargazers_count", 0)
            created = (r.get("created_at") or "")[:10]
            star_txt = f"⭐ ~{stars/1000:.1f}k" if stars >= 1000 else f"⭐ {stars}"
            items.append(NewsItem(
                title=r["full_name"],
                url=r["html_url"],
                source="GitHub 新锐",
                category="github",
                published=created,
                summary=(r.get("description") or "").strip(),
                image_url=_og_image(r["full_name"]),
                heat=f"{star_txt} · {created[5:]} 创建",
                tags=(r.get("topics") or [])[:5],
            ))
    return items


def collect(cfg: dict) -> list[NewsItem]:
    g = cfg.get("github", {})
    keywords = cfg.get("keywords", [])
    items: list[NewsItem] = []
    if g.get("trending", True):
        items.extend(_trending(cfg, keywords))
    if g.get("newborn", {}).get("enabled", True):
        items.extend(_newborn(cfg))

    seen: set[str] = set()
    deduped: list[NewsItem] = []
    for it in items:
        if it.title in seen:
            continue
        seen.add(it.title)
        deduped.append(it)
    return deduped
