from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_renders_booking_page():
    response = client.get("/")
    assert response.status_code == 200
    assert "选择日期" in response.text  # 日期条
    assert 'name="viewport"' in response.text
