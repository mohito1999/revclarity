import logging
from openai import AzureOpenAI
from app.core.config import settings
from typing import List, Optional

logger = logging.getLogger(__name__)

# Initialize a synchronous client for the utility script
embedding_client: Optional[AzureOpenAI] = None

if all([
    settings.AZURE_OPENAI_EMBEDDING_ENDPOINT,
    settings.AZURE_OPENAI_API_KEY,
    settings.AZURE_OPENAI_API_VERSION_EMBEDDING
]):
    try:
        embedding_client = AzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_EMBEDDING_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION_EMBEDDING,
        )
        logger.info(f"AzureOpenAI Embedding client initialized for endpoint: {settings.AZURE_OPENAI_EMBEDDING_ENDPOINT}")
    except Exception as e:
        logger.error(f"Failed to initialize AzureOpenAI Embedding client: {e}", exc_info=True)
else:
    logger.warning("Azure OpenAI Embedding settings are not fully configured. Embedding generation will fail.")


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Takes a list of texts and returns a list of their vector embeddings.
    """
    if not embedding_client:
        raise ConnectionError("Embedding client is not initialized.")

    try:
        # The embedding model can handle a batch of texts in a single API call
        response = embedding_client.embeddings.create(
            input=texts,
            model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME
        )
        # Extract just the embedding vector from each data object
        return [item.embedding for item in response.data]
    except Exception as e:
        logger.error(f"Failed to get embeddings from Azure OpenAI: {e}", exc_info=True)
        # Return a list of empty lists with the same shape to prevent crashes
        return [[] for _ in texts]