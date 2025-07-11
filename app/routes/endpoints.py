from fastapi import APIRouter
from app.routes.v1.router import (
    auth,
    health,
    admin_service,
    employee,
    transactions,
    admin_transactions,
    reports,
    ws_notifications,
    treasury,
    services,
    currency,
    customers,
    reciepts,
    create_admin
)

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(admin_service.router, prefix="/admin", tags=["Admin"])
api_router.include_router(employee.router, prefix="/employee", tags=["Employee"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(admin_transactions.router, prefix="/admintx", tags=["Admin Transactions"])
api_router.include_router(ws_notifications.router, prefix="/live", tags=["WebSocket"])
api_router.include_router(treasury.router, prefix="/treasury", tags=["Treasury"])
api_router.include_router(services.router, prefix="/services", tags=["Services"])
api_router.include_router(currency.router, prefix="/currency", tags=["Currency"])
api_router.include_router(customers.router, prefix="/customers", tags=["Customers"])
api_router.include_router(reciepts.router, prefix="/receipts", tags=["Resiepts"])
api_router.include_router(create_admin.router, prefix="/setup", tags=["Create Admin"])

