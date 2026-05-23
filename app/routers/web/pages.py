from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db
from app.security.rate_limiter import limiter
from app.services.payroll_service import list_payrolls
from app.services.person_service import ensure_access_token, get_person, list_people

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/people")


@router.get("/people", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_general)
def people_list(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "people_list.html",
        {"request": request, "people": list_people(db, q=q), "q": q or ""},
    )


@router.get("/people/new", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_general)
def people_new(request: Request):
    return templates.TemplateResponse("person_form.html", {"request": request, "person": None})


@router.get("/people/{person_id}", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_general)
def person_detail(person_id: int, request: Request, db: Session = Depends(get_db)):
    person = get_person(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    ensure_access_token(db, person)
    return templates.TemplateResponse(
        "person_detail.html",
        {
            "request": request,
            "person": person,
            "payrolls": list_payrolls(db, person_id),
        },
    )


@router.get("/people/{person_id}/edit", response_class=HTMLResponse)
@limiter.limit(settings.rate_limit_general)
def person_edit(person_id: int, request: Request, db: Session = Depends(get_db)):
    person = get_person(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return templates.TemplateResponse("person_form.html", {"request": request, "person": person})
