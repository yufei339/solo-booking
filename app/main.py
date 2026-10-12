import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware

from app.admin import router as admin_router
from app.availability import available_days
from app.booking import router as booking_router
from app.tasks import router as tasks_router
from app.templating import templates

app = FastAPI(title="solo-booking")

# 登录态放在签名 Cookie 里。密钥线上由 Terraform 注入，本机用 .env；默认值只为了测试能跑。
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "dev-only-secret"),
    max_age=14 * 24 * 3600,  # 14 天免登录
)
app.include_router(admin_router)
app.include_router(booking_router)
app.include_router(tasks_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request, "index.html", {"coach_name": "教练", "days": available_days()}
    )
