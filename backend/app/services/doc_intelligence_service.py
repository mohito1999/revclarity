import logging
import asyncio
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

if not all([settings.DOC_INTEL_ENDPOINT, settings.DOC_INTEL_KEY, settings.DOC_INTEL_API_VERSION]):
    logger.warning("Azure Document Intelligence settings are not fully configured. Document parsing will fail.")

async def analyze_document_from_url(doc_url: str, model_id: str = "prebuilt-layout") -> str:
    """
    Step 1: Submits a document URL to Document Intelligence for analysis.
    Returns the URL to poll for the result.
    """
    if not settings.DOC_INTEL_ENDPOINT or not settings.DOC_INTEL_KEY:
        raise ConnectionError("Document Intelligence service is not configured.")

    analyze_url = f"{settings.DOC_INTEL_ENDPOINT}/documentintelligence/documentModels/{model_id}:analyze"
    params = {"api-version": settings.DOC_INTEL_API_VERSION}
    headers = {"Content-Type": "application/json", "Ocp-Apim-Subscription-Key": settings.DOC_INTEL_KEY}
    body = {"urlSource": doc_url}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(analyze_url, params=params, headers=headers, json=body)
            response.raise_for_status()
            return response.headers["Operation-Location"]
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during document analysis submission: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error submitting document for analysis: {e}")
            raise

async def get_analysis_results(result_url: str) -> dict:
    """
    Step 2: Polls the result URL until the analysis is complete and returns the result.
    """
    if not settings.DOC_INTEL_KEY:
        raise ConnectionError("Document Intelligence service is not configured.")

    headers = {"Ocp-Apim-Subscription-Key": settings.DOC_INTEL_KEY}
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                response = await client.get(result_url, headers=headers)
                response.raise_for_status()
                result_data = response.json()
                
                status = result_data.get("status")
                if status == "succeeded":
                    return result_data.get("analyzeResult", {})
                elif status == "failed":
                    logger.error(f"Document analysis failed: {result_data.get('error')}")
                    raise Exception("Document analysis failed.")
                
                # If still running, wait before polling again
                await asyncio.sleep(1)

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error while getting analysis results: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Error getting analysis results: {e}")
                raise