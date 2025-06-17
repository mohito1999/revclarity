from fastapi import FastAPI
import logging

from app.db import base_class, session
from app.models import *


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
    # --- MODIFIED ---
    # Replace the old doc_intelligence_service with our new parsing_service
    from app.services import llm_service, parsing_service
    if not llm_service.azure_llm_client:
        logger.warning("Azure LLM Client could not be initialized. AI features will be unavailable.")
    # Check if the LlamaParse API key is set
    if not parsing_service.settings.LLAMAPARSE_API_KEY:
        logger.warning("LlamaParse API key is not configured. Document parsing will be unavailable.")


@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the RevClarity API. We are live."}