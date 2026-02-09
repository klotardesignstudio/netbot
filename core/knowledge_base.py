import logging
from typing import Optional
from agno.knowledge.knowledge import Knowledge
from agno.vectordb.pgvector import PgVector, SearchType
from agno.knowledge.embedder.openai import OpenAIEmbedder
from config.settings import settings

logger = logging.getLogger(__name__)

class NetBotKnowledgeBase(Knowledge):
    """
    Knowledge Base for NetBot using PostgreSQL and pgvector.
    Stores and retrieves interaction history to provide context for the agent.
    """

    def __init__(self):
        if not settings.PG_DATABASE_URL:
            logger.warning("PG_DATABASE_URL not set. Knowledge Base will not function.")
            # We initialize with a dummy URL to avoid crashing, but methods warn
            db_url = "postgresql+psycopg://dummy:dummy@localhost:5432/dummy"
        else:
            db_url = settings.PG_DATABASE_URL
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+psycopg://")

        # embedding model: text-embedding-3-small (1536 dimensions)
        embedder = OpenAIEmbedder(
            id="text-embedding-3-small", 
            dimensions=1536,
            api_key=settings.OPENAI_API_KEY
        )

        vector_db = PgVector(
            table_name="interaction_embeddings",
            db_url=db_url,
            search_type=SearchType.vector,
            embedder=embedder,
        )

        super().__init__(
            vector_db=vector_db,
            # num_documents=5 -> max_results in Knowledge
            max_results=5,
        )
        
    def is_available(self) -> bool:
        """Checks if the KB is properly configured."""
        return bool(settings.PG_DATABASE_URL)
