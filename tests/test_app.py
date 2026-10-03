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
    assert "预约" in response.text
    assert 'name="viewport"' in response.text