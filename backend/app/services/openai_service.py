import logging
import json
from openai import AsyncOpenAI
from app.core.config import settings
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client: Optional[AsyncOpenAI] = None

if settings.OPENAI_API_KEY:
    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("Direct OpenAI client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize direct OpenAI client: {e}", exc_info=True)
else:
    logger.warning("OpenAI API key is not configured. OrthoPilot AI features will be unavailable.")

async def _call_llm_with_json_response(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """Helper function to make a structured call to the LLM and get a JSON response."""
    if not client:
        raise ConnectionError("OpenAI Client is not initialized.")

    try:
        # Using the new /v1/responses endpoint structure
        response = await client.chat.completions.create(
            model=settings.OPENAI_LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"}
        )
        response_content = response.choices[0].message.content
        return json.loads(response_content)
    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}", exc_info=True)
        raise

async def classify_document(text_content: str) -> Dict[str, str]:
    """
    Analyzes document text and classifies it into one of the predefined categories.
    """
    logger.info("AI Task: Classifying document...")
    system_prompt = """
    You are an expert document classifier for an orthopedic practice. Your task is to analyze the text of a document and classify it into ONE of the following categories: 'REFERRAL_FAX', 'DICTATED_NOTE', 'MODMED_NOTE', 'NON_REFERRAL'.

    - 'REFERRAL_FAX': Contains patient demographics, insurance info, and a clear "Reason for Referral".
    - 'DICTATED_NOTE': A transcribed note, often with headings like 'HISTORY OF PRESENT ILLNESS', 'ASSESSMENT AND PLAN'. Usually lacks the structured layout of an EMR printout.
    - 'MODMED_NOTE': A structured EMR printout, often with a clear header (like 'OrthoSouth'), patient identifiers (MRN, DOB), and distinct sections for Allergies, Medications, HPI, Exam, etc.
    - 'NON_REFERRAL': Any other type of document, such as an invoice, a lab result cover sheet, or a medical clearance letter that isn't a direct referral.

    You MUST return a JSON object with a single key "classification" and the corresponding category string as the value.
    """
    user_prompt = f"Please classify the following document content:\n\n---\n\n{text_content[:4000]}" # Truncate for efficiency

    return await _call_llm_with_json_response(system_prompt, user_prompt)

# We will add the extraction functions here in a future step. This is enough for now.