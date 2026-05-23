from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db
from app.schemas.payroll import PayrollCreate, PayrollOut
from app.models import PayrollEntry
from app.security.rate_limiter import limiter
from app.services.payroll_service import create_payroll, current_payroll, delete_payroll, list_payrolls
from app.services.person_service import get_person

router = APIRouter(tags=["payrolls"])


@router.get("/people/{person_id}/payrolls", response_model=list[PayrollOut])
@limiter.limit(settings.rate_limit_general)
def api_list_payrolls(person_id: int, request: Request, db: Session = Depends(get_db)):
    if not get_person(db, person_id):
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return list_payrolls(db, person_id)


@router.post("/people/{person_id}/payrolls", response_model=PayrollOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_put)
def api_create_payroll(person_id: int, request: Request, payload: PayrollCreate, db: Session = Depends(get_db)):
    if not get_person(db, person_id):
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return create_payroll(db, person_id, payload)


@router.get("/people/{person_id}/payrolls/current", response_model=PayrollOut | None)
@limiter.limit(settings.rate_limit_general)
def api_current_payroll(person_id: int, request: Request, db: Session = Depends(get_db)):
    if not get_person(db, person_id):
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return current_payroll(db, person_id)


@router.delete("/people/{person_id}/payrolls/{payroll_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.rate_limit_put)
def api_delete_payroll(person_id: int, payroll_id: int, request: Request, db: Session = Depends(get_db)):
    if not get_person(db, person_id):
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    payroll = db.get(PayrollEntry, payroll_id)
    if not payroll or payroll.person_id != person_id:
        raise HTTPException(status_code=404, detail="Nómina no encontrada")
    delete_payroll(db, payroll)
    return None
