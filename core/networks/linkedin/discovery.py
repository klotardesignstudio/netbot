"""
LinkedIn Discovery Strategy
Feed First -> Topic Search Fallback
Posts sorted by engagement (likes + comments) for maximum visibility.
"""
import random
import logging
from typing import List

from config.settings import settings
from core.database import db
from core.networks.linkedin.client import LinkedInClient
from core.interfaces import DiscoveryStrategy
from core.models import SocialPost, SocialPlatform
from core.logger import NetBotLoggerAdapter

logger = NetBotLoggerAdapter(logging.getLogger('netbot'), {'network': 'LinkedIn'})

# Minimum engagement thresholds for LinkedIn posts
MIN_LIKES = 10       # At least 10 reactions
MIN_COMMENTS = 2     # At least 2 comments


class LinkedInDiscovery(DiscoveryStrategy):
    def __init__(self, client: LinkedInClient):
        self.client = client
        self.topics = settings.load_hashtags("linkedin")

    def find_candidates(self, limit: int = 5) -> List[SocialPost]:
        """
        Feed-first discovery:
        1. Browse home feed for relevant posts
        2. Fallback: search by random topic
        Posts are sorted by engagement score (likes + comments).
        """
        strategies = [
            ("Feed", self._fetch_from_feed),
            ("Topic Search", self._fetch_from_topics),
        ]

        for name, fetch_fn in strategies:
            logger.info(f"Discovery: Trying {name}...", stage='A')
            try:
                candidates = fetch_fn(limit=limit)
                valid = [p for p in candidates if self.validate_candidate(p)]
                
                if valid:
                    # Sort by engagement score (descending)
                    valid = self._sort_by_engagement(valid)
                    logger.info(f"Discovery: Found {len(valid)} valid candidates from {name}.", stage='A')
                    
                    # Log top candidates with metrics
                    for i, p in enumerate(valid[:5]):
                        m = getattr(p, 'metrics', {}) or {}
                        logger.info(
                            f"  #{i+1} [{m.get('likes', 0)} likes, {m.get('comments', 0)} comments] "
                            f"by @{p.author.username}: {p.content[:50]}..."
                        )
                    
                    return valid
                
                logger.info(f"{name} yielded no valid candidates.")
            except Exception as e:
                 logger.error(f"Error in strategy {name}: {e}")

        return []

    def _sort_by_engagement(self, posts: List[SocialPost]) -> List[SocialPost]:
        """Sort posts by engagement score: likes + (comments * 3).
        Comments are weighted 3x because they indicate deeper engagement
        and commenting on popular threads gives more visibility.
        """
        def engagement_score(post: SocialPost) -> int:
            m = getattr(post, 'metrics', {}) or {}
            likes = m.get('likes', 0) or m.get('reactions', 0) or m.get('reaction_count', 0) or 0
            comments = m.get('comments', 0) or 0
            return likes + (comments * 3)
        
        return sorted(posts, key=engagement_score, reverse=True)

    def _fetch_from_feed(self, limit: int) -> List[SocialPost]:
        """Scrape posts from the home feed."""
        return self.client.get_feed_posts(limit=limit)

    def _fetch_from_topics(self, limit: int) -> List[SocialPost]:
        """Search for posts by random topic. Retry up to 3 topics."""
        if not self.topics:
            logger.warning("No topics configured for LinkedIn search.")
            return []
            
        attempts = min(3, len(self.topics))
        tried = random.sample(self.topics, attempts)
        
        for topic in tried:
            logger.info(f"Discovery: Searching topic '{topic}'", stage='A')
            posts = self.client.search_posts(topic, limit=limit)
            if posts:
                random.shuffle(posts)
                return posts
        return []

    def validate_candidate(self, post: SocialPost) -> bool:
        """Validates a candidate post: dedup, content check, and engagement threshold."""
        if not post.id:
            return False

        # Log discovery
        metrics = getattr(post, 'metrics', {}) or {}
        try:
            db.log_discovery(post.id, post.platform.value, "discovery", metrics)
        except Exception as e:
            logger.warning(f"Failed to log discovery for {post.id}: {e}")

        # Dedup: check interaction history
        if db.check_if_interacted(post.id, SocialPlatform.LINKEDIN.value):
            logger.warning(f"Skipping {post.id}: Already interacted.", stage='B')
            try:
                db.update_discovery_status(
                    post.id, post.platform.value, "skipped", "Already interacted"
                )
            except: pass
            return False

        # Must have content for the agent to analyze
        if not post.content or len(post.content) < 10:
            logger.warning(f"Skipping {post.id}: Content too short/empty.", stage='B')
            try:
                db.update_discovery_status(post.id, post.platform.value, "skipped", "Low content")
            except: pass
            return False
            
        # Check for Promoted/Ads
        if "Promoted" in post.content:
             return False

        # Engagement threshold — skip low-engagement posts
        likes = metrics.get('likes', 0) or metrics.get('reactions', 0) or 0
        comments = metrics.get('comments', 0) or 0
        
        if likes < MIN_LIKES and comments < MIN_COMMENTS:
            logger.info(
                f"Skipping {post.id}: Low engagement ({likes} likes, {comments} comments). "
                f"Min: {MIN_LIKES} likes or {MIN_COMMENTS} comments.",
                stage='B'
            )
            try:
                db.update_discovery_status(
                    post.id, post.platform.value, "skipped",
                    f"Low engagement: {likes} likes, {comments} comments"
                )
            except: pass
            return False

        return True
