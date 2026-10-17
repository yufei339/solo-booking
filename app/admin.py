"""教练后台：登录、每周模板、请假日。"""

import hmac
import os
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import db
from app.clock import today
from app.templating import templates

router = APIRouter(prefix="/admin")


def require_admin(request: Request) -> None:
    """后台路由的门卫：未登录就 303 跳到登录页。"""
    if not request.session.get("admin"):
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "admin/login.html", {"error": None})


@router.post("/login")
def login(request: Request, password: Annotated[str, Form()]):
    expected = os.environ.get("ADMIN_PASSWORD", "")
    if expected and hmac.compare_digest(password, expected):
        request.session["admin"] = True
        return RedirectResponse("/admin/bookings", status_code=303)
    return templates.TemplateResponse(
        request, "admin/login.html", {"error": "密码不对"}, status_code=401
    )


@router.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)


# ---------- 每周模板 ----------

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
HOURS = [f"{h:02d}:00" for h in range(7, 22)]  # 07:00 – 21:00


@router.get(
    "/template", response_class=HTMLResponse, dependencies=[Depends(require_admin)]
)
def template_page(request: Request, saved: bool = False):
    return templates.TemplateResponse(
        request,
        "admin/template.html",
        {
            "weekdays": WEEKDAYS,
            "hours": HOURS,
            "slots": db.get_template(),
            "saved": saved,
        },
    )


@router.post("/template", dependencies=[Depends(require_admin)])
def save_template(slot: Annotated[list[str] | None, Form()] = None):
    slots: dict[str, list[str]] = {str(i): [] for i in range(7)}
    for value in slot or []:  # 一个都没勾时表单里没有 slot 字段
        day, time = value.split("-", 1)
        if day in slots and time in HOURS:  # 服务端白名单校验，表单值不可信
            slots[day].append(time)
    db.save_template(slots)
    return RedirectResponse("/admin/template?saved=1", status_code=303)


# ---------- 请假日 ----------


@router.get(
    "/dayoff", response_class=HTMLResponse, dependencies=[Depends(require_admin)]
)
def dayoff_page(request: Request):
    return templates.TemplateResponse(
        request,
        "admin/dayoff.html",
        {"days": db.list_days_off(today()), "today": today()},
    )


@router.post("/dayoff", dependencies=[Depends(require_admin)])
def add_dayoff(day: Annotated[date, Form()]):
    db.add_day_off(day)
    return RedirectResponse("/admin/dayoff", status_code=303)


@router.post("/dayoff/{day}/delete", dependencies=[Depends(require_admin)])
def delete_dayoff(day: date):
    db.remove_day_off(day)
    return RedirectResponse("/admin/dayoff", status_code=303)


# ---------- 预约列表 ----------


@router.get(
    "/bookings", response_class=HTMLResponse, dependencies=[Depends(require_admin)]
)
def bookings_page(request: Request):
    start = today()
    days = []
    for offset in range(14):
        day = start + timedelta(days=offset)
        items = db.list_bookings(day)
        if items:
            days.append((day, items))
    return templates.TemplateResponse(request, "admin/bookings.html", {"days": days})


@router.post("/bookings/{day}/{time}/delete", dependencies=[Depends(require_admin)])
def admin_delete_booking(day: date, time: str):
    db.delete_booking(day, time)
    return RedirectResponse("/admin/bookings", status_code=303)


# ---------- 告警演练 ----------


@router.post("/boom", dependencies=[Depends(require_admin)])
def boom():
    """故意抛异常制造 500，用来演练告警。只有登录教练能打，界面上不露出。"""
    raise RuntimeError("boom: deliberate failure for alarm drill")
