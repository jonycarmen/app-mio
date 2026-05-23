from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db
from app.schemas.person import PersonCreate, PersonListItem, PersonOut, PersonUpdate
from app.security.rate_limiter import limiter
from app.services.person_service import (
    create_person,
    delete_person,
    get_person,
    list_people,
    regenerate_access_token,
    update_person,
)

router = APIRouter(tags=["people"])


@router.get("/people", response_model=list[PersonListItem])
@limiter.limit(settings.rate_limit_general)
def api_list_people(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    return list_people(db, q=q)


@router.post("/people", response_model=PersonOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_put)
def api_create_person(request: Request, payload: PersonCreate, db: Session = Depends(get_db)):
    try:
        return create_person(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="DNI o pasaporte duplicado")


@router.get("/people/{person_id}", response_model=PersonOut)
@limiter.limit(settings.rate_limit_general)
def api_get_person(person_id: int, request: Request, db: Session = Depends(get_db)):
    person = get_person(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return person


@router.put("/people/{person_id}", response_model=PersonOut)
@limiter.limit(settings.rate_limit_put)
def api_update_person(person_id: int, request: Request, payload: PersonUpdate, db: Session = Depends(get_db)):
    person = get_person(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    try:
        return update_person(db, person, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="DNI o pasaporte duplicado")


@router.delete("/people/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.rate_limit_put)
def api_delete_person(person_id: int, request: Request, db: Session = Depends(get_db)):
    person = get_person(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    delete_person(db, person)
    return None


@router.post("/people/{person_id}/regenerate-token", response_model=PersonOut)
@limiter.limit(settings.rate_limit_put)
def api_regenerate_person_token(person_id: int, request: Request, db: Session = Depends(get_db)):
    person = get_person(db, person_id)
    if not person:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return regenerate_access_token(db, person)
