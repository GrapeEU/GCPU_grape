"""
Vertex AI Configuration - Singleton initialization
This ensures Vertex AI is initialized only once across the application.
"""

import logging
import vertexai
from functools import lru_cache
from core.config import settings

logger = logging.getLogger(__name__)

_vertex_ai_initialized = False


def init_vertex_ai():
    """
    Initialize Vertex AI once. Subsequent calls are no-ops.
    Uses singleton pattern to avoid re-initialization errors.
    """
    global _vertex_ai_initialized

    if _vertex_ai_initialized:
        return

    try:
        project_id = settings.gcp_project_id or "brave-streamer-474620-c1"
        location = settings.vertex_ai_location or "us-central1"

        logger.info(f"Initializing Vertex AI with project={project_id}, location={location}")

        vertexai.init(
            project=project_id,
            location=location
        )

        _vertex_ai_initialized = True
        logger.info("✅ Vertex AI initialized successfully")

    except Exception as e:
        logger.error(f"❌ Failed to initialize Vertex AI: {str(e)}")
        raise


@lru_cache(maxsize=1)
def get_vertex_ai_chat_model(model_name: str = "gemini-2.5-flash", temperature: float = 0.7):
    """
    Get a cached Vertex AI chat model instance.

    Args:
        model_name: Name of the Gemini model to use
        temperature: Temperature for text generation

    Returns:
        ChatVertexAI instance
    """
    from langchain_google_vertexai import ChatVertexAI

    # Ensure Vertex AI is initialized
    init_vertex_ai()

    return ChatVertexAI(
        model=model_name,
        temperature=temperature,
    )
