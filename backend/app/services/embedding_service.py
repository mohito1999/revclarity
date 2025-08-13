import logging
from openai import OpenAI
from app.core.config import settings
from typing import List, Optional

logger = logging.getLogger(__name__)

# Initialize a synchronous client for the utility script
client: Optional[OpenAI] = None

if settings.OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        logger.info("Direct OpenAI Embedding client initialized.")
    except Exception as e:
        logger.error(f"Failed to initialize direct OpenAI Embedding client: {e}", exc_info=True)
else:
    logger.warning("OpenAI API key is not configured. Embedding generation will fail.")


def get_embeddings(texts: List[str]) -> List[List[float]]:
    if not client:
        raise ConnectionError("Embedding client is not initialized.")

    try:
        response = client.embeddings.create(
            input=texts,
            model=settings.OPENAI_EMBEDDING_MODEL
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        logger.error(f"Failed to get embeddings from OpenAI: {e}", exc_info=True)
        return [[] for _ in texts]