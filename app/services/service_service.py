from fastapi import HTTPException, status
from app.models import Service, Country
from app.schemas.service import ServiceCreate, ServiceUpdate
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.logger import Logger


logger = Logger.get_logger(__name__)


def create_service(db: Session, service_data: ServiceCreate):
    country = (
        db.query(Country).filter(Country.code == service_data.country.code).first()
    )
    if not country:
        country = Country(
            name=service_data.country.name, code=service_data.country.code
        )
        db.add(country)
        db.commit()
        db.refresh(country)

    service = Service(
        name=service_data.name,
        price=service_data.price,
        operation=service_data.operation,
        currency_id=service_data.currency_id,
        image_url=service_data.image_url,
        country_id=country.id,
    )

    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def update_service(db: Session, service_id: int, service_in: ServiceUpdate) -> Service:
    service = (
        db.query(Service)
        .filter(Service.id == service_id, Service.is_active == True)
        .first()
    )
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found",
        )
    update_data = service_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def delete_service(db: Session, service_id: int) -> None:
    service = (
        db.query(Service)
        .filter(Service.id == service_id, Service.is_active == True)
        .first()
    )
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found",
        )

    service.is_active = False
    db.add(service)
    db.commit()


def activate_service(db: Session, service_id: int) -> Service:
    service = (
        db.query(Service)
        .filter(Service.id == service_id, Service.is_active == False)
        .first()
    )
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_id} not found or already active",
        )
    service.is_active = True
    try:
        db.commit()
        db.refresh(service)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate service due to a database error",
        )
    return service
