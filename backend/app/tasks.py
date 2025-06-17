import logging
import json
from sqlalchemy.orm import Session
import asyncio # Import asyncio

from app.db.session import SessionLocal
from app.crud import crud_claim
from app.services import doc_intelligence_service, llm_service
from app.models.claim import ClaimStatus

logger = logging.getLogger(__name__)

# Make the function asynchronous
async def process_claim_documents(claim_id: str):
    """
    The main background task to process a new claim.
    1. Fetches claim and documents from DB.
    2. Calls Document Intelligence for each document.
    3. Calls OpenAI to structure the extracted data.
    4. Updates the claim in the DB with the results.
    """
    logger.info(f"Starting AI processing for claim_id: {claim_id}")
    
    db: Session = SessionLocal()
    
    try:
        claim = crud_claim.get_claim(db, claim_id)
        if not claim:
            logger.error(f"Claim {claim_id} not found in background task.")
            return

        sample_doc_url = "https://github.com/Azure-Samples/cognitive-services-REST-api-samples/raw/master/curl/form-recognizer/rest-api/invoice.pdf"
        logger.info(f"Using sample document URL for processing: {sample_doc_url}")

        # 1. Analyze Document with Document Intelligence
        # --- ADD AWAIT HERE ---
        result_url = await doc_intelligence_service.analyze_document_from_url(doc_url=sample_doc_url, model_id="prebuilt-invoice")
        # --- AND AWAIT HERE ---
        analysis_result = await doc_intelligence_service.get_analysis_results(result_url)
        
        full_text = analysis_result.get("content", "No content extracted.")
        
        # 2. Structure Data with OpenAI
        if not llm_service.azure_llm_client:
            raise ConnectionError("Azure LLM Client is not initialized.")

        system_prompt = """
        You are an expert RCM data entry specialist. Based on the provided text from a medical document (like an invoice or EOB), extract the following information in a structured JSON format.
        The JSON object must have these exact keys: 'payer_name', 'total_amount', 'date_of_service', 'suggested_cpt_codes', 'suggested_icd10_codes'.
        - 'total_amount' should be a number.
        - 'date_of_service' should be in 'YYYY-MM-DD' format.
        - 'suggested_cpt_codes' and 'suggested_icd10_codes' should be arrays of strings.
        If a value is not found, use a reasonable default or null.
        """
        
        user_prompt = f"Here is the document text:\n\n{full_text}"

        # --- AND AWAIT HERE ---
        chat_completion = await llm_service.azure_llm_client.chat.completions.create(
            model=llm_service.settings.AZURE_LLM_DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        response_content = chat_completion.choices[0].message.content
        extracted_data = json.loads(response_content)
        logger.info(f"LLM extracted data: {extracted_data}")

        # 3. Update the Claim in the DB
        claim.payer_name = extracted_data.get("payer_name")
        claim.total_amount = extracted_data.get("total_amount")
        claim.date_of_service = extracted_data.get("date_of_service")
        
        crud_claim.update_claim_status(db, claim, ClaimStatus.draft)
        
        logger.info(f"Successfully processed and updated claim {claim_id}. Status set to 'draft'.")

    except Exception as e:
        logger.error(f"Error processing claim {claim_id}: {e}", exc_info=True)
        if 'claim' in locals() and claim:
            crud_claim.update_claim_status(db, claim, ClaimStatus.denied)
    finally:
        db.close()