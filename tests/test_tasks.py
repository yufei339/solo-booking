from datetime import date

from fastapi.testclient import TestClient

from app import clock, db, tasks
from app.main import app

client = TestClient(app)
MONDAY = date(2026, 10, 19)


def test_build_daily_email_with_bookings():
    bookings = [
        {"SK": "09:00", "name": "小李", "phone": "13900000000"},
        {"SK": "10:00", "name": "小王", "phone": "13800000000"},
    ]
    subject, body = tasks.build_daily_email(MONDAY, bookings)
    assert subject == "10月19日课表：2 节"
    assert "09:00  小李  13900000000" in body and "10:00  小王" in body


def test_build_daily_email_empty():
    subject, body = tasks.build_daily_email(MONDAY, [])
    assert "0 节" in subject and "没有预约" in body


def test_route_is_404_unless_tasks_enabled(monkeypatch):
    monkeypatch.delenv("TASKS_ENABLED", raising=False)
    assert client.post("/tasks/daily-email").status_code == 404


def test_route_sends_todays_bookings(monkeypatch):
    monkeypatch.setenv("TASKS_ENABLED", "1")
    monkeypatch.setattr(clock, "today", lambda: MONDAY)
    sent = []
    monkeypatch.setattr(
        tasks, "send_email", lambda subject, body: sent.append((subject, body))
    )
    db.create_booking(MONDAY, "10:00", "小王", "13800000000")
    db.create_booking(date(2026, 10, 20), "10:00", "明天的", "13800000001")

    response = client.post("/tasks/daily-email")
    assert response.status_code == 200
    assert response.json() == {"sent": True, "day": "2026-10-19", "bookings": 1}
    assert len(sent) == 1 and "小王" in sent[0][1] and "明天的" not in sent[0][1]
