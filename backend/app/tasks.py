import logging
import json
from sqlalchemy.orm import Session
import asyncio 

from app.db.session import SessionLocal
from app import models, schemas
from app.crud import crud_claim
from app.services import parsing_service, llm_service
from app.models.claim import ClaimStatus

logger = logging.getLogger(__name__)

async def process_claim_documents(claim_id: str, document_id: str):
    """
    The main background task to process a new claim. This is the orchestrator.
    1. Fetches claim and primary document from DB.
    2. Calls LlamaParse to get structured text from the document.
    3. Runs the 3-step AI Assembly Line (Extract -> Code -> Comply).
    4. Performs a simulated eligibility check.
    5. Updates the claim in the DB with all the rich, new data.
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
        
        # 2. Call LlamaParse to get clean text
        logger.info(f"Parsing document: {primary_document.file_path}")
        markdown_text = await parsing_service.parse_document_async(primary_document.file_path)
        
        # 3. Run the AI Assembly Line
        # Step 3a: Extract structured data
        extracted_data = await llm_service.generate_structured_data(markdown_text)
        logger.info(f"AI Step 1 (Extractor) Result: {extracted_data}")

        # Step 3b: Generate medical codes
        medical_codes = await llm_service.generate_medical_codes(markdown_text, extracted_data)
        logger.info(f"AI Step 2 (Coder) Result: {medical_codes}")

        # Step 3c: Check for compliance issues
        compliance_flags = await llm_service.check_compliance(markdown_text, extracted_data, medical_codes)
        logger.info(f"AI Step 3 (Compliance) Result: {compliance_flags}")

        # 4. Perform simulated eligibility check
        # In a real system, this would be a complex lookup. Here, we simulate it.
        # For the demo, we'll just check if a "POLICY_DOC" exists for the patient.
        eligibility_status = "Unknown"
        if claim.patient_id:
            policy_doc = crud_claim.find_document_by_purpose(db, patient_id=claim.patient_id, purpose='POLICY_DOC')
            if policy_doc:
                # We could even have the LLM read the policy doc, but for now, we'll assume its existence means active.
                eligibility_status = "Active"
                logger.info(f"Policy document found for patient {claim.patient_id}. Setting eligibility to Active.")
            else:
                eligibility_status = "Inactive - No Policy on File"
                logger.info(f"No policy document found for patient {claim.patient_id}. Setting eligibility to Inactive.")
        
        # 5. Update the claim in the database with all the new data
        update_data = schemas.ClaimUpdate(
            payer_name=extracted_data.get("payer_name"),
            total_amount=extracted_data.get("total_amount"),
            date_of_service=extracted_data.get("date_of_service")
        )

        # Use a new, more powerful CRUD function to update everything at once
        crud_claim.update_claim_with_ai_results(
            db=db,
            claim=claim,
            update_data=update_data,
            status=ClaimStatus.draft,
            eligibility_status=eligibility_status,
            cpt_codes=medical_codes.get("suggested_cpt_codes", []),
            icd10_codes=medical_codes.get("suggested_icd10_codes", []),
            compliance_flags=compliance_flags
        )
        
        logger.info(f"Successfully processed and updated claim {claim_id}. Status set to 'draft'.")

    except Exception as e:
        logger.error(f"Error processing claim {claim_id}: {e}", exc_info=True)
        if 'claim' in locals() and claim:
            # If anything fails, mark the claim as denied for manual review
            crud_claim.update_claim_status(db, claim, ClaimStatus.denied)
    finally:
        db.close()