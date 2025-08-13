import logging
import json
from pprint import pformat
from openai import AsyncAzureOpenAI
from app.core.config import settings
from typing import Optional, List, Dict, Any

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
azure_llm_client: Optional[AsyncAzureOpenAI] = None

# --- Initialize the Azure OpenAI Client ---
if all(
    [
        settings.AZURE_OPENAI_ENDPOINT,
        settings.AZURE_OPENAI_API_KEY,
        settings.OPENAI_API_VERSION,
    ]
):
    try:
        azure_llm_client = AsyncAzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.OPENAI_API_VERSION,
        )
        logger.info(
            f"AsyncAzureOpenAI client initialized for endpoint: {settings.AZURE_OPENAI_ENDPOINT}"
        )
    except Exception as e:
        logger.error(
            f"Failed to initialize AsyncAzureOpenAI client: {e}",
            exc_info=True,
        )
else:
    logger.warning(
        "Azure OpenAI settings are not fully configured. LLM service will be impaired."
    )


async def _call_llm_with_json_response(
    system_prompt: str, user_prompt: str
) -> Dict[str, Any]:
    """Helper function to make a structured call to the LLM and get a JSON response."""
    if not azure_llm_client:
        raise ConnectionError("Azure LLM Client is not initialized.")

    try:
        chat_completion = await azure_llm_client.chat.completions.create(
            model=settings.AZURE_LLM_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        response_content = chat_completion.choices[0].message.content
        return json.loads(response_content)
    except Exception as e:
        logger.error(f"Azure OpenAI API call failed: {e}", exc_info=True)
        raise


# --- AI Step 1: Document Synthesizer & Extractor ---
async def synthesize_and_extract_claim_data(
    documents: Dict[str, str]
) -> Dict[str, Any]:
    """
    Takes text from multiple documents, synthesizes the information, and extracts
    a comprehensive set of data points corresponding to a CMS-1500 form.
    """
    logger.info(
        "AI Step 1: Synthesizing and extracting comprehensive claim data from multiple documents."
    )

    system_prompt = """
    You are an expert RCM data entry agent. Your task is to synthesize information from multiple provided documents
    (like a Patient Intake Form, an Insurance Card Summary, and a Physician's Encounter Note) to populate a complete
    JSON object for a medical claim.

    **Instructions:**
    1.  **Synthesize:** Carefully read all provided documents. Information for one field might be spread across multiple sources. Choose the most accurate and specific value.
    2.  **Strict JSON Format:** The JSON object you return MUST conform EXACTLY to the structure below.
    3.  **Handle Missing Data:** If a value for a specific key cannot be found, you MUST use `null`.
    4.  **NEW INFERENCE RULE:** If the document indicates the patient is the primary subscriber, you MUST populate both `patient_address` and `insured_address` with the same address.

    **JSON Schema:**
    {
    "insurance_type": "string",
    "insured_id_number": "string",
    "patient_name": "string",
    "patient_dob": "date (YYYY-MM-DD)",
    "patient_sex": "string (M or F, convert 'Female' to F and 'Male' to M)", 
    "insured_name": "string",
    "patient_address": "string",
    "patient_city": "string",
    "patient_state": "string",
    "patient_zip": "string",
    "patient_phone": "string",
    "patient_relationship_to_insured": "string",
    "insured_address": "string", 
    "is_condition_related_to_employment": "boolean",
    "is_condition_related_to_auto_accident": "boolean",
    "is_condition_related_to_other_accident": "boolean",
    "insured_policy_group_or_feca_number": "string",
    "date_of_current_illness": "date (YYYY-MM-DD)",
    "referring_provider_name": "string",
    "referring_provider_npi": "string",
    "prior_authorization_number": "string",
    "federal_tax_id_number": "string",
    "patient_account_no": "string",
    "accept_assignment": "boolean",
    "total_charge_amount": "number",
    "amount_paid_by_patient": "number",
    "service_facility_location_info": "string",
    "billing_provider_info": "string",
    "billing_provider_npi": "string",
    "payer_name": "string",
    "date_of_service": "date (YYYY-MM-DD)",
    "service_lines": [
        {
        "cpt_code": "string (The 5-digit code, e.g., '99214')",
        "charge_amount": "number"
        }
    ]
    }
    """


    # Combine all document texts into a single prompt
    user_prompt_parts = []
    for doc_name, text in documents.items():
        user_prompt_parts.append(
            f"--- START OF DOCUMENT: {doc_name} ---\n{text}\n--- END OF DOCUMENT: {doc_name} ---"
        )

    user_prompt = "\n\n".join(user_prompt_parts)

    # Log the system prompt and user prompt
    logger.debug(f"System Prompt: {system_prompt}")
    logger.debug(f"User Prompt: {user_prompt}")

    response_json = await _call_llm_with_json_response(system_prompt, user_prompt)

    # Log the extracted claim data
    logger.debug(f"Extracted Claim Data: {pformat(response_json)}")

    return response_json




# --- AI Assembly Line Step 2a: Term Generator & CPT Suggester ---
async def generate_medical_codes(
    markdown_text: str, extracted_data: Dict[str, Any]
) -> Dict[str, List[str]]:
    """
    Analyzes text to extract ICD-10 search terms and suggest CPT codes.
    """
    logger.info(
        "AI Step 2a: Generating CPT codes and ICD-10 search terms."
    )
    system_prompt = """
    You are an expert AI Medical Coder. Based on the provided text, perform two tasks:
    1.  **Extract ICD-10 Search Terms:** ...
    2.  **Suggest CPT Codes:** Based on the 'SERVICES RENDERED' section, infer the most likely CPT codes. **Your output for CPT codes MUST be an array of 5-digit strings. DO NOT return descriptive text.**

    Return a JSON object with two keys:
    1.  `"icd10_search_terms"`: An array of strings.
    2.  `"suggested_cpt_codes"`: An array of 5-digit strings (e.g., ["99396", "36415"]).
    """
    user_prompt = f"Here is the document text:\n\n{markdown_text}\n\nAnd here is the initially extracted data for context:\n\n{json.dumps(extracted_data, indent=2)}"
    return await _call_llm_with_json_response(system_prompt, user_prompt)


# --- AI Assembly Line Step 2c: Final ICD-10 Selector ---
async def select_final_icd10_codes(
    markdown_text: str, candidate_codes: List[Dict[str, str]]
) -> List[str]:
    """
    Given the original text and a list of candidate ICD-10 codes from a DB search,
    selects the most relevant codes.
    """
    logger.info("AI Step 2c: Selecting final ICD-10 codes from candidates.")
    system_prompt = """
    You are a selection filter. Your only job is to select items from a provided list.
    You will be given "Original Text" and a "Candidate Code List".
    You MUST review the "Candidate Code List" and select the codes that are most relevant to the "Original Text".
    
    CRITICAL RULE: Your selection MUST ONLY contain codes that are present in the "Candidate Code List". DO NOT invent, create, or modify any codes.
    
    **CRITICAL FALLBACK RULE: If you review the candidates and find that none are a perfect match, you MUST select the SINGLE most plausible code from the list. DO NOT return an empty list if candidates are available.**
    
    Return a JSON object with a single key: `"selected_icd10_codes"`.
    This key should hold an array of strings, containing only the code values from the "Candidate Code List" that you have selected.
    """
    user_prompt = (
        f"Original Document Text:\n{markdown_text}\n\n"
        f"Candidate ICD-10 Codes from Database Search:\n{json.dumps(candidate_codes, indent=2)}\n\n"
        f"Please select the most relevant codes from the candidates."
    )

    response_dict = await _call_llm_with_json_response(
        system_prompt, user_prompt
    )
    return response_dict.get("selected_icd10_codes", [])


# --- AI Assembly Line Step 3: Compliance Officer & Refiner ---
async def check_compliance_and_refine(
    markdown_text: str,
    extracted_data: Dict[str, Any],
    validated_codes: Dict[str, List[Dict]],
) -> Dict[str, Any]:
    """
    Acts as a claim scrubber and refiner.
    """
    logger.info("AI Step 3: Checking compliance and refining codes.")
    system_prompt = """
    You are an AI RCM Compliance Officer. Your final job is to review a claim and perform three tasks:
    1.  **Compliance Check:** Flag potential issues like missing modifiers. Be aware that our internal database stores ICD-10 codes WITHOUT dots (e.g., 'S93401A'), so do not flag discrepancies related to dots. Also flag other violations as per the documents you have provided such as the policy doc, the intake form and the encounter note. Essentially, anything which might lead to the claim failing should be flagged for review.
    2.  **Confidence Scoring:** Assign a confidence score (0.0 to 1.0) for each CPT and ICD-10 code based on how well it is supported by the document text.
    3.  **Diagnosis Linking:** For each CPT code, determine which ICD-10 code(s) justify the procedure. The first ICD-10 code in the list is "A", the second is "B", etc. You can link multiple, separated by a comma (e.g., "A,B").

    Return a JSON object with three keys:
    1.  `"compliance_flags"`: An array of objects, each with 'level' and 'message'.
    2.  `"confidence_scores"`: A dictionary mapping codes to scores.
    3.  `"diagnosis_pointers"`: A dictionary where keys are CPT codes and values are the corresponding diagnosis letter(s).
    """
    user_prompt = (
        f"Please review the following claim information.\n\n"
        f"Full Document Text:\n{markdown_text}\n\n"
        f"Extracted Claim Data:\n{json.dumps(extracted_data, indent=2)}\n\n"
        f"Final Validated Codes with Official Descriptions:\n{json.dumps(validated_codes, indent=2)}\n\n"
    )
    return await _call_llm_with_json_response(system_prompt, user_prompt)


# --- NEW: AI Assembly Line Step 4: Modifier Applier ---
async def apply_modifiers(
    cpt_codes: List[str], compliance_flags: List[Dict]
) -> List[str]:
    """
    Takes a list of CPT codes and compliance flags, and returns a new list
    of CPT codes with the necessary modifiers applied.
    """
    logger.info("AI Step 4: Applying necessary modifiers.")

    system_prompt = """
    You are a text transformation engine. Your only job is to modify a list of codes based on a set of rules.
    You will be given a list of "Original CPT Codes" and a list of "Compliance Flags".
    For each flag that mentions a missing modifier (like 'modifier 25'), find the corresponding CPT code in the original list and append the modifier (e.g., "-25").
    
    **CRITICAL RULES:**
    1.  Your output MUST be a JSON object with a single key: `"modified_cpt_codes"`.
    2.  The value of `"modified_cpt_codes"` MUST be an array of strings.
    3.  Each string in the array MUST be a valid CPT code or CPT code with a modifier (e.g., "99214" or "99214-25").
    4.  **DO NOT under any circumstances return descriptive text. ONLY return the codes.**
    5.  The returned array must contain the same number of codes as the original list.
    """

    user_prompt = (
        f"Original CPT Codes: {json.dumps(cpt_codes, indent=2)}\n\n"
        f"Compliance Flags to address:\n{json.dumps(compliance_flags, indent=2)}\n\n"
        f"Please return the corrected list of CPT codes according to the rules."
    )

    response_dict = await _call_llm_with_json_response(
        system_prompt, user_prompt
    )

    # --- Final safety check to prevent crashes ---
    modified_codes = response_dict.get("modified_cpt_codes", cpt_codes)
    # Ensure every code is a string and not too long.
    sanitized_codes = [
        str(code)[:10]
        for code in modified_codes
        if isinstance(code, (str, int))
    ]

    # Ensure the final list has the same number of elements as the input
    if len(sanitized_codes) == len(cpt_codes):
        return sanitized_codes
    else:
        logger.warning(
            "Modifier AI returned a list of a different length. Falling back to original codes."
        )
        return cpt_codes  # Fallback to prevent data corruption


# --- AI Payer Adjudicator ---
async def adjudicate_claim_as_payer(
    claim_data: Dict, policy_text: str
) -> Dict[str, Any]:
    """
    Simulates a payer adjudicating a claim against a policy.
    Decides to Approve or Deny and provides rationale.
    """
    logger.info("AI Payer: Adjudicating claim against policy.")

    system_prompt = """
    You are an expert claims adjudicator for HealthFirst Insurance. You will be given a submitted claim (as JSON) and the full text of the member's policy document. Your job is to review the claim **against the policy** and make a decision.

    **Instructions:**
    1.  **Review:** Compare the claim's CPT codes against the policy's 'COVERAGE DETAILS'. Check for coverage, co-pays, deductibles, and prior authorization requirements.
    2.  **Decide:** Your decision MUST be either 'approved' or 'denied'. To decide whether to deny or approve a claim, you need to carry out a hollistic review of the claim and the policy and use your own knowledge as an adjudicator to decide whether to approve or deny a claim.
    3.  **Provide Full Rationale:**
        -   **If you Deny:** You MUST provide a `denial_reason` which should contain the reason for the denial along with a denial code, a `root_cause`, AND a `recommended_action`.
        -   **If you Approve:** You MUST calculate the `payer_paid_amount` and confirm the `patient_responsibility_amount`.
    4.  **Return JSON:** Your entire response must be a single JSON object.

    **JSON Structure for Approval:**
    {
      "decision": "approved",
      "payer_paid_amount": 275.00,
      "patient_responsibility_amount": 25.00
    }

    **JSON Structure for Denial:**
    {
      "decision": "denied",
      "denial_reason": "Service requires prior authorization.",
      "root_cause": "The policy requires Prior Authorization for CPT code 20610, but the `prior_authorization_number` on the claim was not provided.",
      "recommended_action": "Obtain prior authorization from the payer and resubmit the claim with the PA number in Box 23."
    }
    """

    user_prompt = (
        f"Please adjudicate the following claim.\n\n"
        f"--- SUBMITTED CLAIM DATA ---\n{json.dumps(claim_data, indent=2, default=str)}\n\n"
        f"--- MEMBER POLICY DOCUMENT ---\n{policy_text}"
    )

    return await _call_llm_with_json_response(system_prompt, user_prompt)