"""DynamoDB 数据访问层。"""

import os
from datetime import date

import boto3
from boto3.dynamodb.conditions import Key

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
