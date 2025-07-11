from fastapi import APIRouter, HTTPException
from app.create_admin import create_admin
import os

router = APIRouter()

@router.post("/setup-admin")
def setup_admin(secret: str):
    if secret != os.getenv("ADMIN_SETUP_SECRET"):
        raise HTTPException(status_code=403, detail="Forbidden")

    created = create_admin("admin", "System Admin", "admin123", verbose=False)
    if not created:
        return {"status": "admin already exists"}
    return {"status": "admin created"}
