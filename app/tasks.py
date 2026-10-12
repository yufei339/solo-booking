"""定时任务入口。EventBridge Scheduler → daily Lambda → Lambda Web Adapter 透传 → 这里。

只有环境变量 TASKS_ENABLED=1 的进程（daily 函数）才响应，Web 函数上这条路由返回 404。
"""

import os
from datetime import date

import boto3
from fastapi import APIRouter, HTTPException

from app import clock, db

router = APIRouter(prefix="/tasks")


def build_daily_email(day: date, bookings: list[dict]) -> tuple[str, str]:
    """返回 (主题, 正文)。纯函数，方便测试。"""
    subject = f"{day.month}月{day.day}日课表：{len(bookings)} 节"
    if not bookings:
        body = f"{day} 今天没有预约。"
    else:
        lines = [f"{b['SK']}  {b['name']}  {b['phone']}" for b in bookings]
        body = f"{day} 今天 {len(bookings)} 节课：\n\n" + "\n".join(lines)
    return subject, body


def send_email(subject: str, body: str) -> None:
    """SES 发信。沙盒模式下发件人和收件人都必须是已验证的地址，所以暂时同一个。"""
    coach_email = os.environ["COACH_EMAIL"]
    boto3.client("sesv2").send_email(
        FromEmailAddress=coach_email,
        Destination={"ToAddresses": [coach_email]},
        Content={
            "Simple": {
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
            }
        },
    )


@router.post("/daily-email")
def daily_email() -> dict:
    if os.environ.get("TASKS_ENABLED") != "1":
        raise HTTPException(status_code=404)
    day = clock.today()
    bookings = db.list_bookings(day)
    subject, body = build_daily_email(day, bookings)
    send_email(subject, body)
    return {"sent": True, "day": day.isoformat(), "bookings": len(bookings)}
