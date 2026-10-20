"""空位计算：模板 − 请假日 − 已约 − 已过时间。纯业务逻辑，不碰 HTTP。"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app import clock, db

WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


@dataclass
class DayAvailability:
    day: date
    label: str  # 例如 "10-20 周二"
    weekday: str  # 周二
    status: str  # "open" 有空位 / "full" 已约满 / "off" 休息 / "none" 该星期不开课
    times: list[str]


def available_days(start: date | None = None, days: int = 14) -> list[DayAvailability]:
    start = start or clock.today()
    template = db.get_template()
    days_off = set(db.list_days_off(start))
    now = clock.now()

    result = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        weekday = WEEKDAY_LABELS[day.weekday()]
        label = f"{day.month}-{day.day:02d} {weekday}"
        if day.isoformat() in days_off:
            result.append(DayAvailability(day, label, weekday, "off", []))
            continue
        times = list(template.get(str(day.weekday()), []))
        if not times:
            result.append(DayAvailability(day, label, weekday, "none", []))
            continue
        booked = {b["SK"] for b in db.list_bookings(day)}
        times = [t for t in times if t not in booked]
        if day == now.date():
            times = [t for t in times if t > now.strftime("%H:%M")]  # 今天只留还没到的
        result.append(
            DayAvailability(day, label, weekday, "open" if times else "full", times)
        )
    return result


def is_bookable(day: date, time: str) -> bool:
    """该时段此刻能否预约：在 14 天窗口内，且在当天的可约列表里。"""
    start = clock.today()
    if not (start <= day < start + timedelta(days=14)):
        return False
    return time in available_days(day, days=1)[0].times


CANCEL_NOTICE = timedelta(hours=24)


def can_cancel(day: date, time: str, now: datetime | None = None) -> bool:
    """客户自助取消：距上课开始必须还有 24 小时以上。"""
    now = now or clock.now()
    hour, minute = (int(x) for x in time.split(":"))
    start = datetime(day.year, day.month, day.day, hour, minute, tzinfo=clock.TZ)
    return start - now >= CANCEL_NOTICE
