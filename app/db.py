"""DynamoDB 数据访问层。"""

import os
import secrets
from datetime import date

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.clock import now

TABLE_NAME = os.environ.get("TABLE_NAME", "solo-booking")

_table = None


def table():
    """懒加载 Table 对象：第一次调用时才连接。"""
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(TABLE_NAME)
    return _table


# ---------- 每周模板 ----------

EMPTY_TEMPLATE: dict[str, list[str]] = {str(i): [] for i in range(7)}


def get_template() -> dict[str, list[str]]:
    """返回 {"0": ["09:00", ...], ..., "6": [...]}，没设置过则全空。"""
    resp = table().get_item(Key={"PK": "COACH", "SK": "TEMPLATE"})
    item = resp.get("Item")
    if not item:
        return dict(EMPTY_TEMPLATE)
    return {k: sorted(v) for k, v in item["slots"].items()}


def save_template(slots: dict[str, list[str]]) -> None:
    table().put_item(Item={"PK": "COACH", "SK": "TEMPLATE", "slots": slots})


# ---------- 请假日 ----------


def list_days_off(start: date) -> list[str]:
    """返回 start 当天及以后的请假日期，格式 YYYY-MM-DD，升序。"""
    resp = table().query(
        KeyConditionExpression=Key("PK").eq("COACH")
        & Key("SK").between(f"DAYOFF#{start.isoformat()}", "DAYOFF#9999-12-31")
    )
    return [item["SK"].removeprefix("DAYOFF#") for item in resp["Items"]]


def add_day_off(day: date) -> None:
    table().put_item(Item={"PK": "COACH", "SK": f"DAYOFF#{day.isoformat()}"})


def remove_day_off(day: date) -> None:
    table().delete_item(Key={"PK": "COACH", "SK": f"DAYOFF#{day.isoformat()}"})


# ---------- 预约 ----------


class SlotTaken(Exception):
    """该时段已被别人约走。"""


def list_bookings(day: date) -> list[dict]:
    """某天的全部预约，按时间升序（SK 就是时间，Query 天然有序）。"""
    resp = table().query(
        KeyConditionExpression=Key("PK").eq(f"BOOKING#{day.isoformat()}")
    )
    return resp["Items"]


def get_booking(day: date, time: str) -> dict | None:
    resp = table().get_item(Key={"PK": f"BOOKING#{day.isoformat()}", "SK": time})
    return resp.get("Item")


def create_booking(day: date, time: str, name: str, phone: str) -> dict:
    """条件写入：主键已存在就失败，保证同一时段只成功一个。"""
    item = {
        "PK": f"BOOKING#{day.isoformat()}",
        "SK": time,
        "name": name,
        "phone": phone,
        "token": secrets.token_urlsafe(16),  # 取消凭证，只出现在预约人的链接里
        "created_at": now().isoformat(),
    }
    try:
        table().put_item(Item=item, ConditionExpression="attribute_not_exists(PK)")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise SlotTaken(f"{day} {time}") from e
        raise
    return item


def delete_booking(day: date, time: str) -> None:
    table().delete_item(Key={"PK": f"BOOKING#{day.isoformat()}", "SK": time})
