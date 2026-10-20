import os
from datetime import date
from pathlib import Path

from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
SESSION_MINUTES = 60


def coach_profile() -> dict[str, str]:
    """页面上的教练信息，来自环境变量，本机 .env、线上 Terraform 注入。"""
    return {
        "name": os.environ.get("COACH_NAME", "教练"),
        "tagline": os.environ.get("COACH_TAGLINE", "一对一私教 · 每节 60 分钟"),
        "location": os.environ.get("COACH_LOCATION", ""),
    }


def cn_date(day: date) -> str:
    """2026-10-26 → 10 月 26 日 周一"""
    return f"{day.month} 月 {day.day} 日 {WEEKDAY_LABELS[day.weekday()]}"


def end_time(start: str, minutes: int = SESSION_MINUTES) -> str:
    """09:00 → 10:00"""
    h, m = (int(x) for x in start.split(":"))
    total = h * 60 + m + minutes
    return f"{total // 60 % 24:02d}:{total % 60:02d}"


templates.env.filters["cn_date"] = cn_date
templates.env.filters["end_time"] = end_time
templates.env.globals["coach"] = coach_profile
templates.env.globals["session_minutes"] = SESSION_MINUTES
