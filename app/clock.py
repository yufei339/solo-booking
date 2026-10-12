"""时间统一按温哥华本地时区。Lambda 系统时区是 UTC，不能直接用 date.today()。"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Vancouver")


def now() -> datetime:
    return datetime.now(TZ)


def today() -> date:
    return now().date()
