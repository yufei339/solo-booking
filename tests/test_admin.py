import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app

client = TestClient(app)


def test_login_page_renders():
    response = client.get("/admin/login")
    assert response.status_code == 200
    assert 'name="password"' in response.text


def test_wrong_password_rejected(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "right")
    response = client.post("/admin/login", data={"password": "wrong"})
    assert response.status_code == 401
    assert "session" not in response.cookies


def test_right_password_sets_session_and_redirects(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "right")
    response = client.post(
        "/admin/login", data={"password": "right"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/template"
    assert "session" in response.cookies


def test_missing_password_env_locks_everyone_out(monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    response = client.post("/admin/login", data={"password": "anything"})
    assert response.status_code == 401


@pytest.fixture
def admin(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "right")
    c = TestClient(app)
    c.post("/admin/login", data={"password": "right"})
    return c


def test_template_requires_login():
    # 用全新客户端，模块级 client 可能在前面的测试里已登录
    response = TestClient(app).get("/admin/template", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_template_page_renders_week(admin):
    response = admin.get("/admin/template")
    assert response.status_code == 200
    assert "周一" in response.text and "21:00" in response.text


def test_save_template_round_trip(admin):
    response = admin.post(
        "/admin/template",
        data={"slot": ["0-09:00", "0-10:00", "3-18:00", "9-99:00"]},
        follow_redirects=False,
    )
    assert response.status_code == 303
    page = admin.get("/admin/template")
    assert 'value="0-09:00" checked' in page.text
    assert db.get_template()["3"] == ["18:00"]


def test_dayoff_requires_login():
    response = TestClient(app).get("/admin/dayoff", follow_redirects=False)
    assert response.status_code == 303


def test_dayoff_add_and_delete(admin):
    admin.post("/admin/dayoff", data={"day": "2099-01-10"})
    admin.post("/admin/dayoff", data={"day": "2099-02-20"})
    page = admin.get("/admin/dayoff")
    assert "2099-01-10" in page.text and "2099-02-20" in page.text

    response = admin.post("/admin/dayoff/2099-01-10/delete", follow_redirects=False)
    assert response.status_code == 303
    page = admin.get("/admin/dayoff")
    assert "2099-01-10" not in page.text and "2099-02-20" in page.text


def test_dayoff_rejects_bad_date(admin):
    response = admin.post("/admin/dayoff", data={"day": "not-a-date"})
    assert response.status_code == 422
