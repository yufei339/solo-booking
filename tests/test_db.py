from datetime import date

import pytest

from app import db


def test_template_defaults_to_empty_week():
    assert db.get_template() == db.EMPTY_TEMPLATE


def test_template_round_trip_sorts_times():
    db.save_template({"0": ["10:00", "09:00"], "1": []})
    assert db.get_template()["0"] == ["09:00", "10:00"]


def test_days_off_lists_only_from_start_date():
    db.add_day_off(date(2026, 10, 1))
    db.add_day_off(date(2026, 10, 20))
    db.add_day_off(date(2026, 11, 2))
    assert db.list_days_off(date(2026, 10, 11)) == ["2026-10-20", "2026-11-02"]


def test_remove_day_off():
    db.add_day_off(date(2026, 10, 20))
    db.remove_day_off(date(2026, 10, 20))
    assert db.list_days_off(date(2026, 10, 11)) == []


def test_create_booking_and_list():
    db.create_booking(date(2026, 10, 20), "10:00", "小王", "13800000000")
    db.create_booking(date(2026, 10, 20), "09:00", "小李", "13900000000")
    names = [b["name"] for b in db.list_bookings(date(2026, 10, 20))]
    assert names == ["小李", "小王"]


def test_same_slot_twice_raises():
    db.create_booking(date(2026, 10, 20), "10:00", "小王", "13800000000")
    with pytest.raises(db.SlotTaken):
        db.create_booking(date(2026, 10, 20), "10:00", "小张", "13700000000")
    assert db.get_booking(date(2026, 10, 20), "10:00")["name"] == "小王"


def test_delete_booking():
    db.create_booking(date(2026, 10, 20), "10:00", "小王", "13800000000")
    db.delete_booking(date(2026, 10, 20), "10:00")
    assert db.get_booking(date(2026, 10, 20), "10:00") is None
