import logging
from sqlalchemy.orm import Session
import asyncio
import uuid
import json

from app.db.session import SessionLocal
from app import models, schemas
from app.crud import crud_claim, crud_policy_benefit, crud_medical_code
from app.services import parsing_service, llm_service
from app.models.claim import ClaimStatus
from app.celery_worker import celery_app
import datetime
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Helper function to run async code from a sync Celery task
def run_async(func):
    return asyncio.run(func)

# This is our "Policy Genius" task, now fully included.
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


# --- NEW, POWERFUL CLAIM PROCESSING ORCHESTRATOR ---
@celery_app.task
def process_claim_creation(claim_id_str: str):
    """
    The main Celery task to orchestrate the creation and processing of a new claim.
    This is the heart of the hyper-realism pipeline.
    """
    logger.info(f"CELERY TASK: Starting hyper-realistic claim processing for claim_id: {claim_id_str}")
    db: Session = SessionLocal()
    claim_id = uuid.UUID(claim_id_str)
    
    try:
        # 1. FETCH ALL RELEVANT DATA
        claim = crud_claim.get_claim(db, claim_id)
        if not claim or not claim.patient:
            logger.error(f"Claim {claim_id} or its patient not found.")
            return
            
        all_docs = claim.patient.documents + claim.documents
        parsed_docs = {}
        for doc in all_docs:
            purpose = doc.document_purpose or 'UNKNOWN'
            logger.info(f"Parsing document '{purpose}': {doc.file_name}")
            content = run_async(parsing_service.parse_document_async(doc.file_path))
            if purpose in parsed_docs:
                parsed_docs[purpose] += f"\n\n--- (Additional Document: {doc.file_name}) ---\n\n" + content
            else:
                parsed_docs[purpose] = content

        # 2. STEP 1 OF PIPELINE: SYNTHESIZE & EXTRACT
        extracted_claim_data = run_async(llm_service.synthesize_and_extract_claim_data(parsed_docs))
        logger.info("AI Step 1 (Synthesize & Extract) complete.")
        
        # 3. STEP 2 OF PIPELINE: CODING (RAG METHOD)
        encounter_note_text = parsed_docs.get('ENCOUNTER_NOTE', '')
        coding_suggestions = run_async(llm_service.generate_medical_codes(encounter_note_text, extracted_claim_data))
        icd10_search_terms = coding_suggestions.get("icd10_search_terms", [])
        retrieved_icd10_candidates = crud_medical_code.find_similar_icd10_codes(db, icd10_search_terms)
        final_icd10_codes = run_async(llm_service.select_final_icd10_codes(encounter_note_text, retrieved_icd10_candidates))
        
        initial_codes_for_validation = {
            "suggested_cpt_codes": coding_suggestions.get("suggested_cpt_codes", []),
            "suggested_icd10_codes": final_icd10_codes
        }
        validated_codes = crud_medical_code.validate_codes(db, initial_codes_for_validation)
        logger.info(f"AI Step 2 (Coding) complete. Validated codes: {validated_codes}")

        # 4. STEP 3 OF PIPELINE: ELIGIBILITY, COMPLIANCE & MODIFIER APPLICATION
        cpt_code_strings = [item['code'] for item in validated_codes.get('cpt_codes', [])]
        eligibility_status, patient_resp = crud_policy_benefit.check_claim_eligibility(
            db=db, patient_id=claim.patient_id, service_codes=cpt_code_strings
        )
        logger.info(f"AI Step 3a (Eligibility) complete. Status: {eligibility_status}")

        compliance_and_confidence = run_async(llm_service.check_compliance_and_refine(
            encounter_note_text, extracted_claim_data, validated_codes
        ))
        logger.info("AI Step 3b (Compliance) complete.")

        # --- NEW STEP 3c: APPLY MODIFIERS ---
        modified_cpt_codes = run_async(llm_service.apply_modifiers(
            cpt_codes=cpt_code_strings,
            compliance_flags=compliance_and_confidence.get("compliance_flags", [])
        ))
        logger.info(f"AI Step 3c (Modifier) complete. Final CPT codes: {modified_cpt_codes}")
        
        # Update the validated_codes dictionary with the newly modified CPT codes
        for i, item in enumerate(validated_codes['cpt_codes']):
            if i < len(modified_cpt_codes):
                item['code'] = modified_cpt_codes[i]
        # --- END NEW STEP ---

        # 5. FINAL STEP: UPDATE DATABASE
        valid_update_fields = {
            k: v for k, v in extracted_claim_data.items() 
            if k in schemas.ClaimUpdate.model_fields
        }
        update_data = schemas.ClaimUpdate(**valid_update_fields)
        
        update_data.eligibility_status = eligibility_status
        update_data.patient_responsibility_amount = patient_resp
        update_data.compliance_flags = compliance_and_confidence.get("compliance_flags", [])
        
        crud_claim.update_claim(db=db, claim_id=claim.id, claim_in=update_data)
        
        crud_claim.create_service_lines_for_claim(
            db=db, claim_id=claim.id, validated_codes=validated_codes,
            confidence_scores=compliance_and_confidence.get("confidence_scores", {}),
            diagnosis_pointers=compliance_and_confidence.get("diagnosis_pointers", {}),
            extracted_claim_data=extracted_claim_data
        )
        
        crud_claim.update_claim_status(db, claim=claim, status=ClaimStatus.draft)
        logger.info(f"Successfully processed and updated claim {claim_id}. Status set to 'draft'.")

    except Exception as e:
        logger.error(f"Error in Celery task process_claim_creation for claim {claim_id}: {e}", exc_info=True)
        if 'claim' in locals() and claim:
            crud_claim.update_claim_status(db, claim, ClaimStatus.denied)
    finally:
        db.close()


# --- NEW: Adjudication Task ---
@celery_app.task
def process_adjudication(claim_id_str: str):
    """
    Celery task to simulate a payer adjudicating a claim.
    """
    logger.info(f"CELERY TASK: Starting adjudication for claim_id: {claim_id_str}")
    db: Session = SessionLocal()
    claim_id = uuid.UUID(claim_id_str)
    try:
        # 1. Fetch all necessary data for adjudication
        claim = crud_claim.get_claim_for_adjudication(db, claim_id)
        if not claim or not claim.patient:
            logger.error(f"Claim {claim_id} or its patient not found for adjudication.")
            return

        # Find the patient's policy document to pass to the AI
        policy_doc = crud_claim.find_document_by_purpose(db, patient_id=claim.patient_id, purpose='POLICY_DOC')
        if not policy_doc:
            logger.error(f"No policy document found for patient {claim.patient_id}, cannot adjudicate.")
            # In a real scenario, we would deny for no policy, but here we'll stop.
            return
        
        policy_text = run_async(parsing_service.parse_document_async(policy_doc.file_path))
        
        # 2. Call the AI Adjudicator
        # We need to serialize the claim object to pass it to the LLM
        claim_dict = schemas.Claim.from_orm(claim).model_dump()
        
        adjudication_result = run_async(llm_service.adjudicate_claim_as_payer(claim_dict, policy_text))
        logger.info(f"AI Adjudicator result: {adjudication_result}")

        # 3. Update the claim based on the AI's decision
        decision = adjudication_result.get("decision")
        
        update_data = {
            "adjudication_date": datetime.utcnow()
        }

        if decision == "approved":
            update_data["status"] = ClaimStatus.approved
            update_data["payer_paid_amount"] = adjudication_result.get("payer_paid_amount")
            # The patient responsibility was already calculated, but the AI confirms it.
        elif decision == "denied":
            update_data["status"] = ClaimStatus.denied
            update_data["denial_reason"] = adjudication_result.get("denial_reason")
            update_data["denial_root_cause"] = adjudication_result.get("denial_root_cause")
            update_data["denial_recommended_action"] = adjudication_result.get("denial_recommended_action")
        else:
            logger.error("AI Adjudicator returned an invalid decision. Defaulting to denied.")
            update_data["status"] = ClaimStatus.denied
            update_data["denial_reason"] = "Processing Error: Invalid adjudication response from AI."

        crud_claim.update_claim_adjudication(db, claim_id=claim.id, update_data=update_data)
        logger.info(f"Claim {claim_id} successfully adjudicated with status: {update_data['status']}.")

    except Exception as e:
        logger.error(f"Error in Celery task process_adjudication for claim {claim_id}: {e}", exc_info=True)
    finally:
        db.close()