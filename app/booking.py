"""客户端预约：选时段 → 填姓名电话 → 成功页。"""

import re
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import availability, db
from app.templating import templates

router = APIRouter()

PHONE_RE = re.compile(r"\+?\d{7,15}")


def _unavailable(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "unavailable.html", {}, status_code=404)


@router.get("/book/{day}/{time}", response_class=HTMLResponse)
def book_form(request: Request, day: date, time: str):
    if not availability.is_bookable(day, time):
        return _unavailable(request)
    return templates.TemplateResponse(
        request,
        "book.html",
        {"day": day, "time": time, "error": None, "name": "", "phone": ""},
    )


@router.post("/book/{day}/{time}")
def book_submit(
    request: Request,
    day: date,
    time: str,
    name: Annotated[str, Form()],
    phone: Annotated[str, Form()],
):
    name = name.strip()
    phone = re.sub(r"[\s-]", "", phone)
    ctx = {"day": day, "time": time, "name": name, "phone": phone}
    if not name or not PHONE_RE.fullmatch(phone):
        ctx["error"] = "请填写姓名和正确的手机号"
        return templates.TemplateResponse(request, "book.html", ctx, status_code=400)
    if not availability.is_bookable(day, time):
        return _unavailable(request)
    try:
        booking = db.create_booking(day, time, name, phone)
    except db.SlotTaken:
        ctx["error"] = "这个时段刚被别人约走了，请回首页另选"
        return templates.TemplateResponse(request, "book.html", ctx, status_code=409)
    return RedirectResponse(
        f"/booking/{day}/{time}/{booking['token']}", status_code=303
    )


@router.get("/booking/{day}/{time}/{token}", response_class=HTMLResponse)
def booking_detail(request: Request, day: date, time: str, token: str):
    booking = db.get_booking(day, time)
    if not booking or booking["token"] != token:
        return _unavailable(request)
    return templates.TemplateResponse(
        request, "booked.html", {"day": day, "time": time, "booking": booking}
    )
