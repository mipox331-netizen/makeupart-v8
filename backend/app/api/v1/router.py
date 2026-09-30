from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.beauty import router as beauty_router
from app.api.v1.consents import router as consents_router
from app.api.v1.consultations import router as consultations_router
from app.api.v1.customers import router as customers_router
from app.api.v1.salons import router as salons_router
from app.api.v1.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(salons_router)
api_router.include_router(customers_router)
api_router.include_router(consultations_router)
api_router.include_router(consents_router)
api_router.include_router(beauty_router)
