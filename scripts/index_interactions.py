import sys
import os
from pathlib import Path

# Add project root to python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.database import db
from core.knowledge_base import NetBotKnowledgeBase
from core.logger import logger

def index_existing_interactions():
    """
    Fetches past interactions from Supabase and indexes them into the Vector DB.
    """
    logger.info("🚀 Starting backfill of interactions to Knowledge Base...")
    
    kb = NetBotKnowledgeBase()
    if not kb.is_available():
        logger.error("❌ PG_DATABASE_URL not set. Cannot index.")
        return

    # 1. Fetch from 'interactions' table (Supabase REST)
    # limit to last 100 for now to avoid timeouts on initial run
    try:
        res = db.client.table("interactions").select("*").order("created_at", desc=True).limit(100).execute()
        transforming_rows = res.data
        if not transforming_rows:
            logger.info("No interactions found to index.")
            return
            
        logger.info(f"Found {len(transforming_rows)} recent interactions to index.")
        
        for row in transforming_rows:
            # Create a text representation for the embedding
            # Context: "I commented '...' on a post by @user about '...'"
            
            content_text = f"""
            Interaction on {row.get('platform')}:
            User: @{row.get('username')}
            My Comment: "{row.get('comment_text')}"
            Reasoning: {row.get('metadata', {}).get('reasoning', 'N/A')}
            """
            
            # Use kb.insert()
            # name can be post_id or similar
            post_id = row.get("post_id")
            kb.insert(
                name=f"interaction_{post_id}",
                text_content=content_text,
                metadata={
                    "post_id": post_id,
                    "platform": row.get("platform"),
                    "username": row.get("username"),
                    "created_at": row.get("created_at")
                },
                upsert=True
            )

        logger.info("✅ Successfully indexed documents.")

    except Exception as e:
        logger.error(f"Failed to index interactions: {e}")

if __name__ == "__main__":
    index_existing_interactions()
