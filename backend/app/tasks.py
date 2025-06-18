import logging
import json
from sqlalchemy.orm import Session
import asyncio
import uuid

from app.db.session import SessionLocal
from app import models, schemas
from app.crud import crud_claim, crud_policy_benefit, crud_medical_code
from app.services import parsing_service, llm_service
from app.models.claim import ClaimStatus
from app.celery_worker import celery_app

logger = logging.getLogger(__name__)

# Helper function to run async code from a sync Celery task
def run_async(func):
    return asyncio.run(func)

@celery_app.task
def process_policy_document(patient_id_str: str, document_id_str: str):
    """Celery task to process an insurance policy document."""
    logger.info(f"CELERY TASK: Starting Policy Document processing for patient_id: {patient_id_str}")
    db: Session = SessionLocal()
    patient_id = uuid.UUID(patient_id_str)
    document_id = uuid.UUID(document_id_str)
    try:
        policy_document = crud_claim.get_document(db, document_id)
        if not policy_document:
            logger.error(f"Policy document {document_id} not found.")
            return

        markdown_text = run_async(parsing_service.parse_document_async(policy_document.file_path))
        
        # This logic is correct and remains the same.
        system_prompt = """
        You are an expert Health Insurance Benefits Analyst. Your task is to read the provided policy document text
        and extract a list of covered benefits. Return a JSON object with a single key "benefits".
        The "benefits" key should hold an array of objects. Each object represents a single benefit and
        MUST have these exact keys: 'benefit_type' (e.g., "Office Visit", "Specialist Visit", "Emergency Room"),
        'is_covered' (boolean), 'co_pay_amount' (number), and 'coverage_percent' (number, e.g., 80 for 80%).
        If a value isn't specified, use a reasonable default like null or 0.
        Focus on common medical services.
        """
        user_prompt = f"Here is the policy document text:\n\n{markdown_text}"

        if not llm_service.azure_llm_client:
            raise ConnectionError("Azure LLM Client is not initialized.")

        chat_completion = run_async(llm_service.azure_llm_client.chat.completions.create(
            model=llm_service.settings.AZURE_LLM_DEPLOYMENT_NAME,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"}
        ))
        response_content = chat_completion.choices[0].message.content
        extracted_benefits = json.loads(response_content).get("benefits", [])
        logger.info(f"Extracted {len(extracted_benefits)} benefits from policy doc {document_id}.")

        crud_policy_benefit.create_benefits_for_patient(
            db=db, patient_id=patient_id, source_document_id=document_id, benefits_data=extracted_benefits
        )
        logger.info(f"Successfully saved policy benefits for patient {patient_id}.")
    except Exception as e:
        logger.error(f"Error in Celery task process_policy_document: {e}", exc_info=True)
    finally:
        db.close()

@celery_app.task
def process_claim_documents(claim_id_str: str, document_id_str: str):
    """Celery task to process a new claim using the RAG method for ICD-10 coding."""
    logger.info(f"CELERY TASK: Starting full AI processing for claim_id: {claim_id_str}")
    db: Session = SessionLocal()
    claim_id = uuid.UUID(claim_id_str)
    document_id = uuid.UUID(document_id_str)
    try:
        claim = crud_claim.get_claim(db, claim_id)
        if not claim: return
        
        primary_document = crud_claim.get_document(db, document_id)
        if not primary_document: return

        markdown_text = run_async(parsing_service.parse_document_async(primary_document.file_path))
        
        extracted_data = run_async(llm_service.generate_structured_data(markdown_text))
        logger.info(f"AI Step 1 (Extractor) Result: {extracted_data}")

        # --- NEW RAG WORKFLOW FOR CODING ---
        # Step 2a (Generate Terms): Get CPT suggestions and ICD-10 search terms from AI
        coding_suggestions = run_async(llm_service.generate_medical_codes(markdown_text, extracted_data))
        logger.info(f"AI Step 2a (Generate Terms) Result: {coding_suggestions}")

        # Step 2b (Retrieve): Search our DB for ICD-10 code candidates using the AI's terms
        icd10_search_terms = coding_suggestions.get("icd10_search_terms", [])
        retrieved_icd10_candidates = crud_medical_code.find_similar_icd10_codes(db, icd10_search_terms)
        logger.info(f"AI Step 2b (Retrieve): Found {len(retrieved_icd10_candidates)} ICD-10 candidates from DB via vector search.")

        # Step 2c (Final Selection): Ask the LLM to choose the best ICD-10 codes from the retrieved candidates
        final_icd10_codes = run_async(llm_service.select_final_icd10_codes(markdown_text, retrieved_icd10_candidates))
        logger.info(f"AI Step 2c (Final Selection): LLM selected {len(final_icd10_codes)} final ICD-10 codes.")
        
        # Create a combined dictionary of all suggested codes for the validation step
        initial_codes_for_validation = {
            "suggested_cpt_codes": coding_suggestions.get("suggested_cpt_codes", []),
            "suggested_icd10_codes": final_icd10_codes # Use the LLM's final selection
        }

        # Step 2d (Validate): Validate CPT codes and the final list of ICD-10 codes
        validated_codes = crud_medical_code.validate_codes(db, initial_codes_for_validation)
        logger.info(f"AI Step 2d (Validate) Result: {validated_codes}")
        
        # Step 3 (Refine & Comply): Pass the final, validated codes to the Compliance Officer
        compliance_and_confidence = run_async(llm_service.check_compliance_and_refine(
            markdown_text=markdown_text, extracted_data=extracted_data, validated_codes=validated_codes
        ))
        logger.info(f"AI Step 3 (Refine & Comply) Result: {compliance_and_confidence}")
        
        # --- END RAG WORKFLOW ---

        # The rest of the pipeline uses the final, validated data
        cpt_code_strings = [item['code'] for item in validated_codes.get('cpt_codes', [])]
        eligibility_status, patient_resp = crud_policy_benefit.check_claim_eligibility(
            db=db, patient_id=claim.patient_id, service_codes=cpt_code_strings
        )
        logger.info(f"Eligibility check result: {eligibility_status}, Patient Responsibility: ${patient_resp}")

        update_data = schemas.ClaimUpdate(
            payer_name=extracted_data.get("payer_name"),
            total_amount=extracted_data.get("total_amount"),
            date_of_service=extracted_data.get("date_of_service")
        )

        crud_claim.update_claim_with_ai_results(
            db=db, claim=claim, update_data=update_data, status=ClaimStatus.draft,
            eligibility_status=eligibility_status, patient_responsibility=patient_resp,
            compliance_flags=compliance_and_confidence.get("compliance_flags", [])
        )
        
        crud_claim.create_service_lines_for_claim(
            db=db, claim_id=claim.id, validated_codes=validated_codes,
            confidence_scores=compliance_and_confidence.get("confidence_scores", {}),
            diagnosis_pointers=compliance_and_confidence.get("diagnosis_pointers", {})
        )

        logger.info(f"Successfully processed and updated claim {claim_id}. Status set to 'draft'.")
    except Exception as e:
        logger.error(f"Error in Celery task process_claim_documents: {e}", exc_info=True)
        if 'claim' in locals() and claim:
            crud_claim.update_claim_status(db, claim, ClaimStatus.denied)
    finally:
        db.close()