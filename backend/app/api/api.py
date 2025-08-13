from fastapi import APIRouter

from app.api.routers import claims, patients, analytics, meriplex

api_router = APIRouter()

# Include the claims router
api_router.include_router(claims.router)
api_router.include_router(patients.router)
api_router.include_router(analytics.router)
api_router.include_router(meriplex.router)

# In the future, we would add other routers here:
# from app.api.routers import patients
# api_router.include_router(patients.router)