from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.dependencies import get_db
from app.core.security import require_admin
from app.core.websocket import manager
from app.models import Service, Country
from app.models.users import User
from app.schemas.service import ServiceUpdate, ServiceOut
from app.services.service_service import delete_service, update_service, activate_service

router = APIRouter()

@router.get("/get/available", response_model=List[ServiceOut])
def get_available_services(db: Session = Depends(get_db)):
    """Fetch all active services for public use."""
    return db.query(Service).filter(Service.is_active == True).all()

@router.get("/get/{service_id}", response_model=ServiceOut)
def get_service_by_id(service_id: int, db: Session = Depends(get_db)):
    """Fetch a specific service by ID."""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service

@router.get("/grouped")
def get_services_grouped_by_country(db: Session = Depends(get_db)):
    """Group all services under their countries (admin/public view)."""
    countries = db.query(Country).all()
    result = []
    for country in countries:
        services = db.query(Service).filter(Service.country_id == country.id).all()
        result.append({
            "country": {"name": country.name, "code": country.code},
            "services": services,
        })
    return result

@router.get("/grouped-for-employee")
def get_services_grouped_for_employee(db: Session = Depends(get_db)):
    """Group only active services for employees."""
    services = db.query(Service).filter(Service.is_active == True).all()
    grouped = {}
    for svc in services:
        key = svc.country.code
        if key not in grouped:
            grouped[key] = {
                "country": {"name": svc.country.name, "code": svc.country.code},
                "services": [],
            }
        grouped[key]["services"].append(svc)
    return list(grouped.values())

@router.patch(
    "/update/{service_id}",
    response_model=ServiceOut,
    dependencies=[Depends(require_admin)],
    summary="Edit a service",
    description="Partially update an existing service. Requires admin rights."
)
async def edit_service(
    service_id: int,
    service_input: ServiceUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Admin-only: update service data."""
    updated_service = update_service(db, service_id, service_input)

    # Broadcast to all users
    await manager.broadcast({
        "type": "service_updated",
        "content": f"🔄 تم تعديل الخدمة: {updated_service.name}"
    })

    return updated_service

@router.delete(
    "/delete/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
    summary="Delete a service",
    description="Soft-delete (deactivate) a service. Requires admin rights."
)
async def remove_service(
    service_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Admin-only: deactivate a service."""
    delete_service(db, service_id)

    # Broadcast to all users
    await manager.broadcast({
        "type": "service_deleted",
        "content": f"🗑️ تم حذف الخدمة #{service_id}"
    })

    return

@router.patch(
    "/{service_id}/activate",
    response_model=ServiceOut,
    dependencies=[Depends(require_admin)],
    summary="Activate a service",
    description="Re-activate a previously soft-deleted service. Requires admin rights."
)
async def activate_service_endpoint(
    service_id: int,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Admin-only: reactivate a service."""
    activated_service = activate_service(db, service_id)

    # Broadcast to all users
    await manager.broadcast({
        "type": "service_activated",
        "content": f"✅ تم إعادة تفعيل الخدمة: {activated_service.name}"
    })

    return activated_service
