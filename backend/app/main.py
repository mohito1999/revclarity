from fastapi import FastAPI
import logging
from app.api.api import api_router
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RevClarity API",
    description="API for the RevClarity RCM Co-Pilot",
    version="1.0.0"
)

app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    logger.info("RevClarity API starting up...")
    # You can add checks here to ensure services are initialized
    from app.services import llm_service, doc_intelligence_service
    if not llm_service.azure_llm_client:
        logger.warning("Azure LLM Client could not be initialized. AI features will be unavailable.")
    if not all([doc_intelligence_service.settings.DOC_INTEL_ENDPOINT, doc_intelligence_service.settings.DOC_INTEL_KEY]):
        logger.warning("Document Intelligence service is not configured. Document parsing will be unavailable.")

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the RevClarity API. We are live."}

# We will add our API routers here later
# from app.api import claims_router
# app.include_router(claims_router, prefix="/api/v1")