from fastapi import APIRouter
from app.config import get_settings

router = APIRouter()


@router.get("")
async def health_check():
    return {
        "status": "ok",
        "service": "potencjal-api",
        "version": "1.0.0",
        "environment": get_settings().ENVIRONMENT,
    }
