import logging
import json
import asyncio
from openai import AsyncOpenAI, RateLimitError
from app.core.config import settings
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client: Optional[AsyncOpenAI] = None

if settings.OPENAI_API_KEY:
    try:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("Direct OpenAI Async client initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize direct OpenAI client: {e}", exc_info=True)
else:
    logger.warning("OpenAI API key is not configured. OrthoPilot AI features will be unavailable.")

async def call_llm_with_reasoning(
    instructions: str, 
    user_input: str,
    reasoning_effort: str = "low",
    is_json: bool = False,
    retries: int = 1,
    retry_delay_seconds: int = 15
) -> Dict[str, Any]:
    """
    Central helper function to call the new OpenAI Responses API, controlling reasoning effort
    and including a simple retry mechanism for rate limit errors.
    """
    if not client:
        raise ConnectionError("OpenAI Client is not initialized.")

    last_exception = None
    for attempt in range(retries + 1):
        try:
            response_format = {"type": "json_object"} if is_json else {"type": "text"}
            
            messages = [
                {"role": "system", "content": instructions},
                {"role": "user", "content": user_input}
            ]
            
            response = await client.responses.create(
                model=settings.OPENAI_LLM_MODEL,
                input=messages,
                reasoning={"effort": reasoning_effort},
                text={"format": response_format}
            )
            
            response_content = response.output_text
            if not response_content:
                 raise ValueError("OpenAI API returned an empty response.")

            if is_json:
                return json.loads(response_content)
            else:
                return {"answer": response_content}
        
        # --- THE FIX: Catch RateLimitError and wait ---
        except RateLimitError as e:
            last_exception = e
            if attempt < retries:
                logger.warning(f"OpenAI rate limit hit. Retrying in {retry_delay_seconds} seconds... (Attempt {attempt + 1}/{retries + 1})")
                await asyncio.sleep(retry_delay_seconds)
            else:
                logger.error("OpenAI rate limit hit. Max retries reached.")
                raise e
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}", exc_info=True)
            raise

    # This part should not be reached if retries are exhausted, but as a fallback:
    raise last_exception if last_exception else Exception("LLM call failed after all retries.")


async def classify_document(text_content: str) -> Dict[str, str]:
    """
    Analyzes document text and classifies it into one of the predefined categories.
    """
    logger.info("AI Task: Classifying document...")
    instructions = """
     You are an expert document classifier for an orthopedic practice. Your task is to analyze the text of a document and classify it into ONE of the following categories: 'REFERRAL_FAX', 'DICTATED_NOTE', 'MODMED_NOTE', 'NON_REFERRAL'.

    - 'REFERRAL_FAX': Contains patient demographics, insurance info, and a clear "Reason for Referral".
    - 'DICTATED_NOTE': A transcribed note, often with headings like 'HISTORY OF PRESENT ILLNESS', 'ASSESSMENT AND PLAN'. Usually lacks the structured layout of an EMR printout.
    - 'MODMED_NOTE': A structured EMR printout, often with a clear header (like 'OrthoSouth'), patient identifiers (MRN, DOB), and distinct sections for Allergies, Medications, HPI, Exam, etc.
    - 'NON_REFERRAL': Any other type of document, such as an invoice, a lab result cover sheet, or a medical clearance letter that isn't a direct referral.

    You MUST return a JSON object with a single key "classification" and the corresponding category string as the value.
    """
    user_input = f"Please classify the following document content:\n\n---\n\n{text_content[:4000]}"
    # --- THE FIX: Increased reasoning effort for better accuracy ---
    return await call_llm_with_reasoning(instructions, user_input, reasoning_effort="medium", is_json=True)

# ... (The rest of the functions in this file remain exactly the same) ...

async def extract_referral_data(text_content: str) -> Dict[str, Any]:
    """
    Extracts a comprehensive set of structured data from a referral fax document.
    """
    logger.info("AI Task: Performing comprehensive extraction on Referral Fax...")
    instructions = """
    You are a highly accurate medical data extraction AI for an orthopedic practice. Your task is to extract a comprehensive set of information from the provided text of a referral fax.

    You MUST return a JSON object with the following exact keys. If a value for any key cannot be found in the text, you MUST use `null`. Do not invent information. Pay close attention to formatting and the rules below.

    --- DISAMBIGUATION RULES ---
    1.  **patient_phone**: This is the patient's primary contact number. Look for labels like 'Patient Phone', 'Home Phone', 'Cell Phone', or simply 'Phone' within the main patient information block.
    2.  **patient_policy_id**: This is a critical field. It is the patient's insurance identification number. Look for labels like 'Subscriber No', 'Insurance #', 'Policy ID', or 'Member ID'. It is often an alphanumeric string located near the insurance carrier's name.
    3.  **patient_name**: Format as 'LAST, FIRST'.
    4.  **Dates**: Format all dates as YYYY-MM-DD.

    On a high level, I need you to be adaptable and understand that real world messy data can lead to documents which are not always formatted in a way that is easy to parse. As such, use your capabilities to understand the context of the document and extract the data in a way that is most likely to be correct. 
    Do your absolute best to understand the context of the document and extract the data in a way that is most likely to be correct as per the JSON schema provided to you below. 

    --- END DISAMBIGUATION RULES ---

    **JSON Schema:**
    {
      "patient_name": "string",
      "patient_dob": "string",
      "patient_address": "string (Full address including city, state, zip)",
      "patient_phone": "string",
      "patient_primary_insurance": "string (The name of the insurance carrier, e.g., 'CIGNA', 'Medicare')",
      "patient_policy_id": "string",
      "reason_for_referral": "string (A concise, one-sentence summary of why the patient is being referred)",
      "referring_physician_name": "string (Format as 'LAST, FIRST, CREDENTIALS')",
      "referring_physician_facility": "string (The name of the clinic or hospital)",
      "referring_physician_phone": "string",
      "referring_physician_fax": "string",
      "referral_date": "string"
    }
    """
    user_input = f"Please extract the data from this referral text, following all rules carefully:\n\n---\n\n{text_content}"
    return await call_llm_with_reasoning(instructions, user_input, reasoning_effort="low", is_json=True)

async def extract_dictated_note_data(text_content: str) -> Dict[str, Any]:
    """
    Performs a granular extraction of clinical data from a dictated visit note.
    """
    logger.info("AI Task: Performing GRANULAR extraction on Dictated Note...")
    instructions = """
     You are a specialist AI trained in parsing clinical documentation. Your task is to perform a highly granular extraction of a physician's dictated note and structure it into a clean JSON object.

    Break down the 'Assessment and Plan' into discrete components: diagnoses, prescribed medications, recommended procedures, therapies, follow-up instructions, etc.

    **JSON Schema:**
    {
      "chief_complaint": "string",
      "history_of_present_illness": "string",
      "physical_exam_summary": "string",
      "imaging_results_summary": "string",
      "diagnoses": ["string"],
      "plan": {
        "medications_prescribed": [
          { "name": "string", "instructions": "string" }
        ],
        "procedures_administered": [
          { "name": "string", "details": "string" }
        ],
        "therapies_recommended": ["string"],
        "durable_medical_equipment": ["string"],
        "further_testing_recommended": ["string"],
        "follow_up": "string (e.g., 'Follow-up in 4 weeks to reassess symptoms')"
      }
    }
    """
    user_input = f"Please extract the clinical data from this dictated note into the specified granular JSON format:\n\n---\n\n{text_content}"
    return await call_llm_with_reasoning(instructions, user_input, reasoning_effort="low", is_json=True)

async def generate_emr_actions(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Takes structured clinical data and generates a list of suggested EMR actions.
    """
    logger.info("AI Task: Generating EMR actions from extracted data...")
    instructions = """
    You are an AI RCM Co-pilot. Your task is to analyze a structured JSON object of extracted clinical data and generate a list of concrete, actionable tasks that an EMR system would perform. For each diagnosis, suggest a plausible ICD-10 code.

    Return a JSON object with a single key, "suggested_actions", which is an array of objects. Each object must have `type`, `summary`, and `details`.

    **Action Types:** 'DIAGNOSIS', 'PRESCRIPTION', 'PROCEDURE', 'REFERRAL', 'FOLLOW_UP'

    **Example Input JSON:**
    { "diagnoses": ["Osteoarthritis of the left knee"], "plan": { "medications_prescribed": [{"name": "Medrol Dosepak"}], "follow_up": "Follow up in 2 weeks" } }

    **Example Output JSON:**
    {
      "suggested_actions": [
        {
          "type": "DIAGNOSIS",
          "summary": "Add Diagnosis: Osteoarthritis of the left knee",
          "details": { "diagnosis": "Osteoarthritis of the left knee", "suggested_code": "M17.12" }
        },
        {
          "type": "PRESCRIPTION",
          "summary": "Prescribe: Medrol Dosepak",
          "details": { "medication": "Medrol Dosepak", "instructions": "Take as directed." }
        },
        {
          "type": "FOLLOW_UP",
          "summary": "Schedule Follow-up: 2 weeks",
          "details": { "timeframe": "2 weeks", "reason": "To monitor improvement." }
        }
      ]
    }
    """
    user_input = f"Based on the following extracted clinical data, generate the suggested EMR actions:\n\n{json.dumps(extracted_data, indent=2)}"
    return await call_llm_with_reasoning(instructions, user_input, reasoning_effort="low", is_json=True)

async def extract_modmed_note_data(text_content: str) -> Dict[str, Any]:
    """
    Performs an exhaustive, deeply nested extraction of all data points from a structured EMR note (ModMed/EMA).
    """
    logger.info("AI Task: Performing EXHAUSTIVE extraction on ModMed/EMA Note...")
    instructions = """
   Performs an exhaustive, deeply nested extraction of all data points from a structured EMR note (ModMed/EMA).
    """
    logger.info("AI Task: Performing EXHAUSTIVE extraction on ModMed/EMA Note...")
    system_prompt = """
    You are a world-class clinical data architect. Your task is to meticulously parse the text from an EMR visit note and transform it into a highly structured, deeply nested JSON object. Every single piece of information must be captured and categorized.

    **CRITICAL INSTRUCTIONS:**
    1.  **Be Exhaustive:** Do not omit any data. Extract everything, including patient identifiers, allergies, medications, history, vitals, every detail of the physical exam, test interpretations, and the full impression and plan.
    2.  **Maintain Structure:** Adhere strictly to the nested JSON schema provided below.
    3.  **Handle Nulls:** If a specific field or entire section is not present in the document, use `null` for that key.

    **JSON Schema:**
    {
      "patient_demographics": {
        "name": "string (LAST, FIRST)",
        "pms_id": "string",
        "mrn": "string",
        "dob": "string (YYYY-MM-DD)",
        "sex": "string",
        "contact_info": "string"
      },
      "visit_details": {
        "visit_date": "string (YYYY-MM-DD)",
        "provider_name": "string",
        "chief_complaint": "string"
      },
      "clinical_history": {
        "allergies": ["string"],
        "medications": ["string"],
        "medical_history": ["string"],
        "musculoskeletal_history": ["string"],
        "surgical_history": ["string"],
        "social_history": "string"
      },
      "vitals": {
        "date": "string (YYYY-MM-DD)",
        "time": "string (HH:MM)",
        "taken_by": "string",
        "height": "string",
        "weight": "string",
        "bmi": "number",
        "bsa": "number"
      },
      "physical_exam": {
        "general_appearance": "string",
        "orientation": "string",
        "mood": "string",
        "lumbosacral": {
          "rom": "string",
          "skin_inspection": "string",
          "palpation_findings": "string",
          "posture": "string"
        },
        "extremity_strength_and_tone": [
            { "muscle_group": "string (e.g., Right Iliopsoas)", "strength": "string (e.g., 5/5)", "tone": "string" }
        ],
        "sensation_and_reflexes": {
            "dermatomal_sensation": "string",
            "peripheral_sensation": "string",
            "reflexes": "string"
        }
      },
      "tests_and_results": [
        {
          "test_type": "string (e.g., 'X-Ray Interpretation Lumbar Spine')",
          "diagnosis": "string",
          "findings": "string"
        }
      ],
      "impression_and_plan": [
        {
          "diagnosis": "string",
          "associated_diagnoses": ["string"],
          "plan_items": [
            { "type": "string (e.g., 'Home Exercise Program', 'Counseling', 'Prescription')", "details": "string" }
          ]
        }
      ],
      "follow_up": {
          "timeframe": "string",
          "notes": "string"
      }
    }
    """
    user_input = f"Please perform an exhaustive extraction on the following EMR note, adhering strictly to the provided JSON schema:\n\n---\n\n{text_content}"
    return await call_llm_with_reasoning(instructions, user_input, reasoning_effort="low", is_json=True)