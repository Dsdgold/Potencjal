from fastapi import APIRouter
from app.routes import auth, companies, admin, subscriptions, health

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
