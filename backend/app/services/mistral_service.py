import logging
import mimetypes
import os
import base64
from typing import Any

from app.core.config import settings
from mistralai import Mistral # <-- This is the ONLY import we need from the library

logger = logging.getLogger(__name__)

# Initialize the client, checking for the API key first
if not settings.MISTRAL_API_KEY:
    logger.warning("Mistral API key is not configured in .env. Document OCR will fail.")
    client = None
else:
    client = Mistral(api_key=settings.MISTRAL_API_KEY)

async def ocr_document_async(file_path: str) -> str:
    """
    Asynchronously processes a document with Mistral OCR by sending its base64 content
    and returns the parsed Markdown.
    """
    if not client:
        raise ConnectionError("Mistral client is not initialized due to a missing API key.")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at path: {file_path}")

    try:
        logger.info(f"Reading and encoding file for Mistral OCR: {file_path}")
        with open(file_path, "rb") as pdf_file:
            base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
        
        mime_type = mimetypes.guess_type(file_path)[0] or "application/pdf"
        
        logger.info(f"Submitting OCR request to Mistral for {os.path.basename(file_path)}...")
        
        # The documentation shows that the async client is not needed for a single call.
        # We can use the synchronous client's `ocr.process` method within our async function.
        # The HTTP request itself is what we care about being async, which the library handles.
        # However, to be fully async-native, we will use an async HTTP client wrapper later if needed,
        # but for now, let's stick to the simplest documented pattern.
        # NOTE: The official SDK examples for async use `complete_async` for chat, but not for OCR.
        # We will use the standard `process` method as shown in all OCR examples.
        
        # Since this is a Celery task (sync context), we should use the sync client method.
        # The `run_async` helper in tasks.py will handle this.
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": f"data:{mime_type};base64,{base64_pdf}" 
            }
        )
        
        # Join the content from all pages returned by the OCR
        # The response object has a `pages` attribute which is a list of dictionaries
        full_markdown_content = "".join([page.markdown for page in ocr_response.pages if page.markdown])
        
        if not full_markdown_content.strip():
             logger.warning(f"Mistral OCR returned no content for file {file_path}")
             return ""

        logger.info(f"Successfully received OCR content for {os.path.basename(file_path)}")
        return full_markdown_content

    except Exception as e:
        logger.error(f"An unexpected error occurred during Mistral OCR processing for {file_path}: {e}", exc_info=True)
        raise