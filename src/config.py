"""配置加载"""
from __future__ import annotations

import os

import yaml


def load_config(path: str = "config.yaml") -> dict:
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
