"""定时调度器: 每周一、周四 08:00 自动执行 采集 → 生成 → Pages → 发邮件

用法:
  python scheduler.py            # 前台常驻运行(关闭窗口即停止)
  python scheduler.py --once     # 立即执行一次(等价于 run_daily.py --pages --send-email)

调度规则在 config.yaml 的 schedule 段配置(星期/时间/补跑窗口)。
需要长期后台运行, 请用 Windows 任务计划程序把本脚本设为开机启动, 或直接让
任务计划程序每周一/四 08:00 运行 run_daily.py(见 README)。
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.config import load_config   # noqa: E402
import run_daily                      # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, "logs", "scheduler.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("scheduler")


def _parse_hm(hm: str) -> int:
    """'08:00' -> 当天分钟数"""
    h, m = hm.split(":")
    return int(h) * 60 + int(m)


def should_fire(now: datetime, days: list[int], hm: str,
                grace_minutes: int, last_fired: str) -> tuple[bool, str]:
    """到达触发条件: 星期匹配 且 当前时刻落在 [time, time+grace] 窗口内 且 今天未触发过。
    宽限窗口让 08:05 才开机/唤醒的机器也能补跑, 而下午开机不会误触发。"""
    key = now.strftime("%Y-%m-%d")
    if last_fired == key or now.isoweekday() not in days:   # isoweekday: 周一=1
        return False, key
    t = now.hour * 60 + now.minute
    start = _parse_hm(hm)
    return start <= t < start + grace_minutes, key


def main() -> None:
    ap = argparse.ArgumentParser(description="知识库前沿新闻推送 · 定时调度器")
    ap.add_argument("--once", action="store_true", help="立即执行一次后退出")
    args = ap.parse_args()

    cfg = load_config("config.yaml")
    sch = cfg.get("schedule", {})
    days = sch.get("days", [1, 4])                 # ISO 星期: 周一=1 ... 周日=7
    hm = sch.get("time", "08:00")
    grace = sch.get("grace_minutes", 30)

    if args.once:
        log.info("手动执行一次")
        run_daily.pipeline(send_email=True, pages=True)
        return

    day_names = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "日"}
    plan = "、周".join(day_names.get(d, str(d)) for d in days)
    log.info("调度器已启动: 每周%s %s 执行(补跑窗口 %d 分钟)", plan, hm, grace)

    last_fired = ""
    while True:
        try:
            fire, key = should_fire(datetime.now(), days, hm, grace, last_fired)
            if fire:
                last_fired = key
                log.info("到达触发时间, 开始执行")
                run_daily.pipeline(send_email=True, pages=True)
                log.info("执行完成")
        except Exception as e:
            log.error("本次执行失败: %s", e, exc_info=True)
        time.sleep(30)


if __name__ == "__main__":
    main()
