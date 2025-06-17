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
        raise

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

# --- AI Assembly Line Step 2a: Term Generator & CPT Suggester ---
async def generate_medical_codes(markdown_text: str, extracted_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Analyzes text to extract ICD-10 search terms and suggest CPT codes.
    """
    logger.info("AI Step 2a: Generating CPT codes and ICD-10 search terms.")
    system_prompt = """
    You are an expert AI Medical Coder. Based on the provided text, perform two tasks:
    1.  **Extract ICD-10 Search Terms:** From the 'CLINICAL NOTES' section, identify all key clinical terms, diagnoses, and symptoms. Be comprehensive.
    2.  **Suggest CPT Codes:** Based on the 'SERVICES RENDERED' section, infer the most likely CPT codes. You are an expert; make an educated guess.

    Return a JSON object with two keys:
    1.  `"icd10_search_terms"`: An array of strings (e.g., ["right ankle pain", "fall from stairs", "suspected fracture"]).
    2.  `"suggested_cpt_codes"`: An array of strings (e.g., ["99214", "73610"]).
    """
    user_prompt = f"Here is the document text:\n\n{markdown_text}\n\nAnd here is the initially extracted data for context:\n\n{json.dumps(extracted_data, indent=2)}"
    return await _call_llm_with_json_response(system_prompt, user_prompt)

# --- NEW: AI Assembly Line Step 2c: Final ICD-10 Selector ---
async def select_final_icd10_codes(markdown_text: str, candidate_codes: List[Dict[str, str]]) -> List[str]:
    """
    Given the original text and a list of candidate ICD-10 codes from a DB search,
    selects the most relevant codes.
    """
    logger.info("AI Step 2c: Selecting final ICD-10 codes from candidates.")
    system_prompt = """
    You are an expert AI Medical Coder. You will be given the original physician's notes and a list of
    candidate ICD-10 codes retrieved from a database. Your job is to review the candidates and select
    the one or two codes that are MOST appropriate and relevant to the text.
    
    **You MUST select at least one code if candidates are provided.** Choose the best fit, even if it's not perfect.
    
    Return a JSON object with a single key: `"selected_icd10_codes"`.
    This key should hold an array of strings, containing only the code values of your selection.
    """
    user_prompt = (
        f"Original Document Text:\n{markdown_text}\n\n"
        f"Candidate ICD-10 Codes from Database Search:\n{json.dumps(candidate_codes, indent=2)}\n\n"
        f"Please select the most relevant codes from the candidates."
    )
    
    response_dict = await _call_llm_with_json_response(system_prompt, user_prompt)
    return response_dict.get("selected_icd10_codes", [])

# --- AI Assembly Line Step 3: Compliance Officer & Refiner ---
async def check_compliance_and_refine(markdown_text: str, extracted_data: Dict[str, Any], validated_codes: Dict[str, List[Dict]]) -> Dict[str, Any]:
    """
    Acts as a claim scrubber and refiner.
    """
    logger.info("AI Step 3: Checking compliance and refining codes.")
    system_prompt = """
    You are an AI RCM Compliance Officer. Your job is to perform a final review of a claim.
    Perform two tasks:
    1.  **Compliance Check:** Flag potential issues like missing modifiers, especially for HealthFirst Insurance.
    2.  **Confidence Scoring:** For each provided code, assign a confidence score (from 0.0 to 1.0). Be confident in your analysis; scores should generally be high (e.g., above 0.85) unless there is a major ambiguity.

    Return a JSON object with two keys: `"compliance_flags"` and `"confidence_scores"`.
    """
    user_prompt = (
        f"Please review the following claim information.\n\n"
        f"Extracted Data:\n{json.dumps(extracted_data, indent=2)}\n\n"
        f"Final Validated Codes with Official Descriptions:\n{json.dumps(validated_codes, indent=2)}\n\n"
        f"Full Document Text:\n{markdown_text}"
    )
    return await _call_llm_with_json_response(system_prompt, user_prompt)

# --- Denial Management Function ---
async def generate_denial_analysis(claim_data: dict) -> dict:
    """
    Generates a plausible denial reason for a given claim.
    """
    # (No changes to this function)
    logger.info("Generating denial analysis.")
    system_prompt = """
    You are an expert RCM denial management assistant. Based on the provided claim data and denial reason,
    generate a plausible root cause and a recommended action.
    Return a JSON object with two keys: 'root_cause' and 'recommended_action'.
    """
    user_prompt = f"Claim Data: {json.dumps(claim_data, indent=2)}"
    return await _call_llm_with_json_response(system_prompt, user_prompt)