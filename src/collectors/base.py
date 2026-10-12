"""采集器公共工具"""
from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger(__name__)


def http_get(url: str, cfg: dict, **kwargs) -> requests.Response:
    """带超时/重试/代理/UA 的 GET. 失败抛异常,由调用方决定跳过。"""
    net = cfg.get("network", {})
    timeout = net.get("timeout", 20)
    retries = net.get("retries", 2)
    proxies = net.get("proxies") or None
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", net.get("user_agent", "KB-Ontology-News"))

    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout,
                                proxies=proxies, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last_err


def clean_html(text: str) -> str:
    """粗粒度去 HTML 标签 + 压缩空白,用于 RSS 摘要。"""
    import re
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"&\w+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()
