from datetime import date, datetime

from app import availability, clock, db

MONDAY = date(2026, 10, 19)


def test_empty_template_means_no_class():
    days = availability.available_days(MONDAY, days=3)
    assert [d.status for d in days] == ["none", "none", "none"]


def test_all_booked_is_full():
    db.save_template({"0": ["09:00"]})
    db.create_booking(MONDAY, "09:00", "小王", "13800000000")
    assert availability.available_days(MONDAY, days=1)[0].status == "full"


def test_is_bookable_respects_window_and_slots(monkeypatch):
    monkeypatch.setattr(clock, "today", lambda: MONDAY)
    monkeypatch.setattr(
        clock, "now", lambda: datetime(2026, 10, 19, 8, 0, tzinfo=clock.TZ)
    )
    db.save_template({"0": ["09:00"]})
    assert availability.is_bookable(MONDAY, "09:00")
    assert not availability.is_bookable(MONDAY, "10:00")  # 模板里没有
    assert not availability.is_bookable(date(2026, 10, 18), "09:00")  # 过去
    assert not availability.is_bookable(date(2026, 11, 2), "09:00")  # 超出 14 天


def test_template_slots_show_up_on_matching_weekday():
    db.save_template({"0": ["09:00", "10:00"], "1": ["18:00"]})
    days = availability.available_days(MONDAY, days=2)
    assert days[0].times == ["09:00", "10:00"]
    assert days[1].times == ["18:00"]
    assert days[0].label == "10-19 周一"


def test_day_off_is_marked_off():
    db.save_template({"0": ["09:00"]})
    db.add_day_off(MONDAY)
    days = availability.available_days(MONDAY, days=1)
    assert days[0].status == "off" and days[0].times == []


def test_booked_slot_is_removed():
    db.save_template({"0": ["09:00", "10:00"]})
    db.create_booking(MONDAY, "09:00", "小王", "13800000000")
    days = availability.available_days(MONDAY, days=1)
    assert days[0].times == ["10:00"]


def test_past_times_today_are_removed(monkeypatch):
    db.save_template({"0": ["09:00", "10:00", "11:00"]})
    fake_now = datetime(2026, 10, 19, 10, 0, tzinfo=clock.TZ)
    monkeypatch.setattr(clock, "now", lambda: fake_now)
    days = availability.available_days(MONDAY, days=1)
    assert days[0].times == ["11:00"]  # 10:00 已经开始，不能约


def test_can_cancel_needs_24_hours():
    now = datetime(2026, 10, 19, 10, 0, tzinfo=clock.TZ)
    assert availability.can_cancel(date(2026, 10, 20), "10:00", now)  # 正好 24h
    assert availability.can_cancel(date(2026, 10, 21), "09:00", now)
    assert not availability.can_cancel(date(2026, 10, 20), "09:00", now)  # 23h
    assert not availability.can_cancel(date(2026, 10, 19), "11:00", now)
