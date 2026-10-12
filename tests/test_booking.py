from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

from app import availability, clock, db
from app.main import app

MONDAY = date(2026, 10, 19)


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(clock, "today", lambda: MONDAY)
    monkeypatch.setattr(
        clock, "now", lambda: datetime(2026, 10, 19, 8, 0, tzinfo=clock.TZ)
    )
    db.save_template({"0": ["09:00", "10:00"]})


client = TestClient(app)


def test_index_links_to_open_slots():
    response = client.get("/")
    assert "/book/2026-10-19/09:00" in response.text


def test_form_for_unbookable_slot_is_404():
    assert client.get("/book/2026-10-19/11:00").status_code == 404
    assert client.get("/book/2026-10-18/09:00").status_code == 404


def test_book_success_redirects_to_detail_with_token():
    response = client.post(
        "/book/2026-10-19/09:00",
        data={"name": "小王", "phone": "138 0000 0000"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    booking = db.get_booking(MONDAY, "09:00")
    assert booking["phone"] == "13800000000"
    assert (
        response.headers["location"] == f"/booking/2026-10-19/09:00/{booking['token']}"
    )

    page = client.get(response.headers["location"])
    assert page.status_code == 200 and "小王" in page.text
    assert client.get("/booking/2026-10-19/09:00/wrong-token").status_code == 404


def test_invalid_phone_rejected():
    response = client.post(
        "/book/2026-10-19/09:00", data={"name": "小王", "phone": "abc"}
    )
    assert response.status_code == 400
    assert db.get_booking(MONDAY, "09:00") is None


def test_already_booked_slot_is_404():
    db.create_booking(MONDAY, "09:00", "小李", "13900000000")
    response = client.post(
        "/book/2026-10-19/09:00", data={"name": "小王", "phone": "13800000000"}
    )
    assert response.status_code == 404  # is_bookable 已经把它过滤掉了
    assert db.get_booking(MONDAY, "09:00")["name"] == "小李"


def test_race_between_check_and_write_gets_409(monkeypatch):
    """两人同时提交：都通过了 is_bookable，第二个条件写入失败。"""
    monkeypatch.setattr(availability, "is_bookable", lambda day, time: True)
    db.create_booking(MONDAY, "09:00", "小李", "13900000000")
    response = client.post(
        "/book/2026-10-19/09:00", data={"name": "小王", "phone": "13800000000"}
    )
    assert response.status_code == 409
    assert "刚被别人约走" in response.text
    assert db.get_booking(MONDAY, "09:00")["name"] == "小李"


def _book(day: str, time: str) -> str:
    response = client.post(
        f"/book/{day}/{time}",
        data={"name": "小王", "phone": "13800000000"},
        follow_redirects=False,
    )
    return response.headers["location"]  # /booking/{day}/{time}/{token}


def test_cancel_more_than_24h_ahead():
    db.save_template({"0": ["09:00"], "1": ["09:00"]})
    detail = _book("2026-10-20", "09:00")  # 周二 09:00，距"现在"(周一 08:00) 25 小时
    page = client.get(detail + "/cancel")
    assert page.status_code == 200 and "确认取消" in page.text

    response = client.post(detail + "/cancel")
    assert response.status_code == 200 and "已取消" in response.text
    assert db.get_booking(date(2026, 10, 20), "09:00") is None
    assert client.get(detail).status_code == 404  # 链接随之失效


def test_cancel_within_24h_is_refused():
    detail = _book("2026-10-19", "10:00")  # 距"现在" 2 小时
    page = client.get(detail + "/cancel")
    assert "不足 24 小时" in page.text and "确认取消" not in page.text

    response = client.post(detail + "/cancel")
    assert response.status_code == 403
    assert db.get_booking(MONDAY, "10:00") is not None


def test_cancel_with_wrong_token_is_404():
    _book("2026-10-19", "10:00")
    assert client.post("/booking/2026-10-19/10:00/bad-token/cancel").status_code == 404
    assert db.get_booking(MONDAY, "10:00") is not None
