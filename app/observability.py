"""结构化日志：每条日志一行 JSON，CloudWatch Logs Insights 可直接按字段过滤。"""

import json
import logging
import sys
import time

from fastapi import FastAPI, Request

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
    for name in ("uvicorn", "uvicorn.error"):  # uvicorn 自己的日志也走 JSON
        uv = logging.getLogger(name)
        uv.handlers = []
        uv.propagate = True
    for noisy in ("botocore", "boto3", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def install(app: FastAPI) -> None:
    """挂上请求日志中间件；未捕获异常在这里就地处理成 500 页面。

    为什么不用 app.exception_handler(Exception)：Starlette 的 ServerErrorMiddleware 会在发完
    500 响应后把异常再抛给 uvicorn，uvicorn 随即关闭连接。Lambda Web Adapter 复用 keep-alive
    连接，连接被关会让它报 "connection closed before message completed"，Lambda 调用被记为失败。
    演练时 10 个 500 里有 5 个变成了 Lambda Errors，就是这个原因。
    """

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                "unhandled exception",
                exc_info=exc,
                extra={"data": {"path": request.url.path}},
            )
            response = templates.TemplateResponse(
                request, "error.html", {}, status_code=500
            )
        logger.info(
            "request",
            extra={
                "data": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    "request_id": request.headers.get("x-amzn-trace-id"),
                }
            },
        )
        return response
