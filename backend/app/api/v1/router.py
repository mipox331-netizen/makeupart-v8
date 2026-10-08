from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.beauty import router as beauty_router
from app.api.v1.consents import router as consents_router
from app.api.v1.consultations import router as consultations_router
from app.api.v1.customers import router as customers_router
from app.api.v1.salons import router as salons_router
from app.api.v1.subscriptions import admin_router as admin_subscriptions_router
from app.api.v1.subscriptions import router as subscriptions_router
from app.api.v1.users import admin_router as admin_users_router
from app.api.v1.users import router as users_router
from app.api.v1.watermarks import router as watermarks_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(admin_users_router)
api_router.include_router(salons_router)
api_router.include_router(customers_router)
api_router.include_router(consultations_router)
api_router.include_router(consents_router)
api_router.include_router(beauty_router)
api_router.include_router(subscriptions_router)
api_router.include_router(admin_subscriptions_router)
api_router.include_router(watermarks_router)
