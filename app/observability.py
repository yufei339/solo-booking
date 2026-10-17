"""结构化日志：每条日志一行 JSON，CloudWatch Logs Insights 可直接按字段过滤。"""

import json
import logging
import sys
import time

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from app.templating import templates

logger = logging.getLogger("solo_booking")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        data = getattr(
            record, "data", None
        )  # logger.info("...", extra={"data": {...}})
        if data:
            payload["data"] = data
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").disabled = True  # 请求日志由下面的中间件统一打
    for noisy in ("botocore", "boto3", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def install(app: FastAPI) -> None:
    """挂上请求日志中间件和全局异常处理。"""

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        started = time.perf_counter()
        status = 500  # 抛异常时没有 response，按 500 记
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            logger.info(
                "request",
                extra={
                    "data": {
                        "method": request.method,
                        "path": request.url.path,
                        "status": status,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                        "request_id": request.headers.get("x-amzn-trace-id"),
                    }
                },
            )

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> HTMLResponse:
        logger.error(
            "unhandled exception",
            exc_info=exc,
            extra={"data": {"path": request.url.path}},
        )
        return templates.TemplateResponse(request, "error.html", {}, status_code=500)
