import logging
import json
from sqlalchemy.orm import Session
import asyncio

from app.db.session import SessionLocal
from app import models, schemas
from app.crud import crud_claim, crud_policy_benefit, crud_medical_code # <-- Import added here
from app.services import parsing_service, llm_service
from app.models.claim import ClaimStatus

logger = logging.getLogger(__name__)

async def process_policy_document(patient_id: str, document_id: str):
    """
    A background task specifically for parsing an insurance policy document.
    1. Fetches the document from the DB.
    2. Calls LlamaParse to get structured text.
    3. Uses a dedicated LLM prompt to act as a "Benefits Analyst".
    4. Saves the extracted, structured benefits to the `policy_benefits` table.
    """
    logger.info(f"Starting Policy Document processing for patient_id: {patient_id}, doc_id: {document_id}")
    
    db: Session = SessionLocal()
    
    try:
        # 1. Fetch the document
        policy_document = crud_claim.get_document(db, document_id)
        if not policy_document:
            logger.error(f"Policy document {document_id} not found.")
            return

        # 2. Parse with LlamaParse
        markdown_text = await parsing_service.parse_document_async(policy_document.file_path)
        
        # 3. Use LLM to extract benefits
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
        
        # This is a simplified call; we'll create a dedicated llm_service function for this
        if not llm_service.azure_llm_client:
            raise ConnectionError("Azure LLM Client is not initialized.")
            
        chat_completion = await llm_service.azure_llm_client.chat.completions.create(
            model=llm_service.settings.AZURE_LLM_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        response_content = chat_completion.choices[0].message.content
        extracted_benefits = json.loads(response_content).get("benefits", [])
        logger.info(f"Extracted {len(extracted_benefits)} benefits from policy doc {document_id}.")

        # 4. Save the benefits to the database
        crud_policy_benefit.create_benefits_for_patient(
            db=db,
            patient_id=patient_id,
            source_document_id=document_id,
            benefits_data=extracted_benefits
        )
        logger.info(f"Successfully saved policy benefits for patient {patient_id}.")

    except Exception as e:
        logger.error(f"Error processing policy document {document_id}: {e}", exc_info=True)
    finally:
        db.close()


async def process_claim_documents(claim_id: str, document_id: str):
    """
    The main background task to process a new claim. This is the orchestrator.
    (UPDATED with GVR and Deep Eligibility)
    """
    logger.info(f"Starting full AI processing for claim_id: {claim_id}")
    
    db: Session = SessionLocal()
    
    try:
        # 1. Fetch data from DB
        claim = crud_claim.get_claim(db, claim_id)
        if not claim:
            logger.error(f"Claim {claim_id} not found in background task.")
            return

        primary_document = crud_claim.get_document(db, document_id)
        if not primary_document:
            logger.error(f"Primary document {document_id} for claim {claim_id} not found.")
            return
        
        # 2. Parse with LlamaParse
        logger.info(f"Parsing document: {primary_document.file_path}")
        markdown_text = await parsing_service.parse_document_async(primary_document.file_path)
        
        # 3. Run the AI Assembly Line
        # Step 3a: Extract structured data
        extracted_data = await llm_service.generate_structured_data(markdown_text)
        logger.info(f"AI Step 1 (Extractor) Result: {extracted_data}")

        # --- NEW: GVR Method for Coding ---
        # Step 3b (Generate): Get initial code suggestions
        initial_codes = await llm_service.generate_medical_codes(markdown_text, extracted_data)
        logger.info(f"AI Step 2a (Generate) Result: {initial_codes}")

        # Step 3c (Validate): Validate codes against our database
        validated_codes = crud_medical_code.validate_codes(db, initial_codes)
        logger.info(f"AI Step 2b (Validate) Result: {validated_codes}")
        
        # Step 3d (Refine): Pass validated info to Compliance Officer for final check & confidence
        compliance_and_confidence = await llm_service.check_compliance_and_refine(
            markdown_text=markdown_text,
            extracted_data=extracted_data,
            validated_codes=validated_codes
        )
        logger.info(f"AI Step 2c (Refine & Comply) Result: {compliance_and_confidence}")
        # --- END GVR Method ---
        
        # 4. Perform Deep Eligibility Check
        logger.info(f"Performing deep eligibility check for patient {claim.patient_id}...")
        eligibility_status, patient_resp = crud_policy_benefit.check_claim_eligibility(
            db=db,
            patient_id=claim.patient_id,
            service_codes=validated_codes.get('cpt_codes', []) # Check against validated CPT codes
        )
        logger.info(f"Eligibility check result: {eligibility_status}, Patient Responsibility: ${patient_resp}")
        
        # 5. Update the claim in the database with all the new data
        update_data = schemas.ClaimUpdate(
            payer_name=extracted_data.get("payer_name"),
            total_amount=extracted_data.get("total_amount"),
            date_of_service=extracted_data.get("date_of_service")
        )

        crud_claim.update_claim_with_ai_results(
            db=db,
            claim=claim,
            update_data=update_data,
            status=ClaimStatus.draft,
            eligibility_status=eligibility_status,
            patient_responsibility=patient_resp,
            compliance_flags=compliance_and_confidence.get("compliance_flags", []),
            # We will create service lines with codes and confidence scores separately
        )
        
        # Create Service Lines with validated codes and confidence scores
        crud_claim.create_service_lines_for_claim(
            db=db, 
            claim_id=claim.id, 
            validated_codes=validated_codes,
            confidence_scores=compliance_and_confidence.get("confidence_scores", {})
        )

        logger.info(f"Successfully processed and updated claim {claim_id}. Status set to 'draft'.")

    except Exception as e:
        logger.error(f"Error processing claim {claim_id}: {e}", exc_info=True)
        if 'claim' in locals() and claim:
            crud_claim.update_claim_status(db, claim, ClaimStatus.denied)
    finally:
        db.close()