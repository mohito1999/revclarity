import logging
import asyncio
import httpx
import mimetypes
import os
from app.core.config import settings

logger = logging.getLogger(__name__)

LLAMAPARSE_API_URL = "https://api.cloud.llamaindex.ai/api/v1/parsing"

if not settings.LLAMAPARSE_API_KEY:
    logger.warning("LlamaParse API key is not configured. Document parsing will fail.")

async def parse_document_async(file_path: str) -> str:
    """
    Asynchronously uploads a document to LlamaParse, polls for completion,
    and returns the parsed Markdown content.
    """
    if not settings.LLAMAPARSE_API_KEY:
        raise ConnectionError("LlamaParse API key is not configured.")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at path: {file_path}")

    headers = {"Authorization": f"Bearer {settings.LLAMAPARSE_API_KEY}"}

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            # 1. Upload the file to start the parsing job
            with open(file_path, "rb") as f:
                mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
                files = {"file": (os.path.basename(file_path), f, mime_type)}
                
                logger.info(f"Uploading {file_path} to LlamaParse...")
                upload_response = await client.post(f"{LLAMAPARSE_API_URL}/upload", headers=headers, files=files)
                upload_response.raise_for_status()
                job_id = upload_response.json()["id"]
                logger.info(f"LlamaParse job created with ID: {job_id}")

            # 2. Poll for the job result
            result_url = f"{LLAMAPARSE_API_URL}/job/{job_id}/result/markdown"
            while True:
                await asyncio.sleep(2) # Wait for 2 seconds before checking
                logger.info(f"Polling for result for job ID: {job_id}...")
                result_response = await client.get(result_url, headers=headers)
                
                if result_response.status_code == 200:
                    logger.info(f"Job {job_id} completed successfully.")
                    result_json = result_response.json()
                    return result_json.get("markdown", "Error: Parsed markdown not found in response.")
                elif result_response.status_code == 404: # Not ready yet
                    logger.info(f"Job {job_id} is still processing...")
                    continue 
                else:
                    # Handle other potential errors during polling
                    result_response.raise_for_status()

        except httpx.HTTPStatusError as e:
            error_details = e.response.text
            logger.error(f"HTTP error during LlamaParse processing: {e} - {error_details}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during LlamaParse processing: {e}", exc_info=True)
            raise

    return "Error: Failed to retrieve parsing result."