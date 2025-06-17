import logging
import json
from openai import AsyncAzureOpenAI
from app.core.config import settings
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)
azure_llm_client: Optional[AsyncAzureOpenAI] = None

# --- Initialize the Azure OpenAI Client ---
if all([settings.AZURE_OPENAI_ENDPOINT, settings.AZURE_OPENAI_API_KEY, settings.OPENAI_API_VERSION]):
    try:
        azure_llm_client = AsyncAzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.OPENAI_API_VERSION,
        )
        logger.info(f"AsyncAzureOpenAI client initialized for endpoint: {settings.AZURE_OPENAI_ENDPOINT}")
    except Exception as e:
        logger.error(f"Failed to initialize AsyncAzureOpenAI client: {e}", exc_info=True)
else:
    logger.warning("Azure OpenAI settings are not fully configured. LLM service will be impaired.")


async def _call_llm_with_json_response(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """Helper function to make a structured call to the LLM and get a JSON response."""
    if not azure_llm_client:
        raise ConnectionError("Azure LLM Client is not initialized.")
    
    try:
        chat_completion = await azure_llm_client.chat.completions.create(
            model=settings.AZURE_LLM_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        response_content = chat_completion.choices[0].message.content
        return json.loads(response_content)
    except Exception as e:
        logger.error(f"Azure OpenAI API call failed: {e}", exc_info=True)
        raise  # Re-raise the exception to be handled by the calling task


# --- AI Assembly Line Step 1: Extractor ---
async def generate_structured_data(markdown_text: str) -> Dict[str, Any]:
    """
    Takes raw markdown from LlamaParse and extracts key-value data.
    """
    logger.info("AI Step 1: Extracting structured data from text.")
    system_prompt = """
    You are an expert RCM data extraction specialist. Based on the provided markdown text from a medical document,
    extract the following information into a structured JSON object.
    The JSON object MUST have these exact keys: 'payer_name', 'patient_name', 'total_amount', 'date_of_service'.
    - 'total_amount' should be a number (float or integer).
    - 'date_of_service' should be in 'YYYY-MM-DD' format.
    If a value is not found, use a reasonable default like an empty string "" or null.
    """
    user_prompt = f"Here is the document text in markdown format:\n\n{markdown_text}"
    
    return await _call_llm_with_json_response(system_prompt, user_prompt)

# --- AI Assembly Line Step 2: Medical Coder ---
async def generate_medical_codes(markdown_text: str, extracted_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Analyzes the text and extracted data to suggest relevant medical codes.
    """
    logger.info("AI Step 2: Generating medical codes.")
    system_prompt = """
    You are an expert AI Medical Coder. Based on the provided markdown text from a medical document,
    suggest relevant CPT and ICD-10 codes.
    Return a JSON object with two keys: 'suggested_cpt_codes' and 'suggested_icd10_codes'.
    - Both keys should hold an array of strings.
    - Analyze the services, procedures, and diagnoses mentioned in the text.
    - If no codes can be determined, return empty arrays.
    """
    user_prompt = f"Here is the document text:\n\n{markdown_text}\n\nAnd here is the initially extracted data for context:\n\n{json.dumps(extracted_data, indent=2)}"
    
    return await _call_llm_with_json_response(system_prompt, user_prompt)


# --- AI Assembly Line Step 3: Compliance Officer ---
async def check_compliance_and_refine(markdown_text: str, extracted_data: Dict[str, Any], validated_codes: Dict[str, List[Dict]]) -> Dict[str, Any]:
    """
    Acts as a claim scrubber and refiner.
    1. Checks for compliance issues (e.g., payer rules).
    2. Assigns a confidence score to each validated code.
    3. Returns a dictionary with compliance flags and confidence scores.
    """
    logger.info("AI Step 3: Checking compliance and refining codes.")
    system_prompt = """
    You are an AI RCM Compliance Officer and Quality Analyst. Your job is to perform a final review of a claim.
    Based on all the provided information, you must perform two tasks:
    1.  **Compliance Check:** Identify potential problems or payer-specific rules. For example, if the payer is 'HealthFirst Insurance', flag if a modifier 25 is missing for an office visit with a procedure.
    2.  **Confidence Scoring:** For each provided CPT and ICD-10 code, assign a confidence score (from 0.0 to 1.0) based on how well the code's official description matches the original document text.

    Return a JSON object with two keys:
    1.  `"compliance_flags"`: An array of objects, where each object has 'level' ('Warning' or 'Error') and 'message'.
    2.  `"confidence_scores"`: A dictionary where keys are the code strings (e.g., "99214") and values are the confidence scores (e.g., 0.98).
    
    If no compliance issues are found, return an empty array for "compliance_flags".
    """
    
    user_prompt = (
        f"Please review the following claim information.\n\n"
        f"Extracted Data:\n{json.dumps(extracted_data, indent=2)}\n\n"
        f"Pre-Validated Codes with Official Descriptions:\n{json.dumps(validated_codes, indent=2)}\n\n"
        f"Full Document Text:\n{markdown_text}"
    )
    
    return await _call_llm_with_json_response(system_prompt, user_prompt)

# --- Denial Management Function (from before, can be refined later) ---
async def generate_denial_analysis(claim_data: dict) -> dict:
    """
    Uses Azure OpenAI to generate a plausible denial reason for a given claim.
    """
    logger.info("Generating denial analysis.")
    system_prompt = """
    You are an expert RCM denial management assistant. Based on the provided claim data and denial reason, 
    generate a plausible root cause and a recommended action.
    Return a JSON object with two keys: 'root_cause' and 'recommended_action'.
    """
    user_prompt = f"Claim Data: {json.dumps(claim_data, indent=2)}"

    return await _call_llm_with_json_response(system_prompt, user_prompt)