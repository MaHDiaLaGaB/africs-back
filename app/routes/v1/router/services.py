from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models import Service, Country
from app.schemas.service import ServiceUpdate, ServiceOut
from app.services.service_service import delete_service, update_service, activate_service

router = APIRouter()


@router.get("/get/available")
def get_available_services(db: Session = Depends(get_db)):
    services = db.query(Service).filter(Service.is_active == True).all()
    return services


# مثال في FastAPI
@router.get("/grouped")
def get_services_grouped_by_country(db: Session = Depends(get_db)):
    countries = db.query(Country).all()
    result = []
    for country in countries:
        services = db.query(Service).filter(Service.country_id == country.id).all()
        result.append({
            "country": {
                "country_name": country.name,
                "country_code": country.code,
            },
            "services": services,
        })
    return result


@router.get("/grouped-for-employee")
def get_services_grouped_for_employee(db: Session = Depends(get_db)):
    services = db.query(Service).filter(Service.is_active == True).all()
    grouped = {}
    for s in services:
        key = s.country.code
        if key not in grouped:
            grouped[key] = {
                "country": {
                    "country_name": s.country.name,
                    "country_code": s.country.code,
                },
                "services": [],
            }
        grouped[key]["services"].append(s)
    return list(grouped.values())


@router.patch(
    "/update/{service_id}",
    response_model=ServiceOut,
    summary="Edit a service",
    description="Update fields of an existing, active service."
)
def edit_service(
    service_id: int,
    service_in: ServiceUpdate,
    db: Session = Depends(get_db),
):
    """
    Partially update a service by its ID.
    Only fields provided in the body will be changed.
    """
    return update_service(db, service_id, service_in)


@router.delete(
    "/delete/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a service",
    description="Soft-delete a service by marking it inactive."
)
def remove_service(
    service_id: int,
    db: Session = Depends(get_db),
):
    """
    Soft-delete a service; it will no longer be returned by list/read endpoints.
    """
    delete_service(db, service_id)
    return


@router.patch(
    "/{service_id}/activate",
    response_model=ServiceOut,
    summary="Activate a service",
    description="Re-activate a previously soft-deleted service."
)
def activate_service_endpoint(
    service_id: int,
    db: Session = Depends(get_db),
):
    return activate_service(db, service_id)
