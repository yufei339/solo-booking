import json
import logging

from fastapi.testclient import TestClient

from app.main import app
from app.observability import JsonFormatter


def test_json_formatter_outputs_one_json_line():
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "hello", None, None)
    record.data = {"status": 200}
    line = JsonFormatter().format(record)
    parsed = json.loads(line)
    assert parsed["msg"] == "hello" and parsed["data"] == {"status": 200}
    assert "\n" not in line


def test_request_log_has_method_path_status(caplog):
    caplog.set_level(logging.INFO, logger="solo_booking")
    TestClient(app).get("/health", headers={"x-amzn-trace-id": "Root=1-abc"})
    records = [r for r in caplog.records if r.getMessage() == "request"]
    assert records[-1].data["path"] == "/health"
    assert records[-1].data["status"] == 200
    assert records[-1].data["request_id"] == "Root=1-abc"
    assert records[-1].data["duration_ms"] >= 0


def test_unhandled_exception_logged_and_returns_500_page(admin, caplog):
    caplog.set_level(logging.INFO, logger="solo_booking")
    # raise_server_exceptions 默认 True：异常若漏到服务器层测试会直接炸，证明中间件兜住了
    client = TestClient(app)
    client.cookies = admin.cookies
    response = client.post("/admin/boom")
    assert response.status_code == 500
    assert "出了点问题" in response.text and "RuntimeError" not in response.text

    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert errors and "boom" in JsonFormatter().format(errors[-1])
    request_log = [r for r in caplog.records if r.getMessage() == "request"][-1]
    assert request_log.data["status"] == 500
