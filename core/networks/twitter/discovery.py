"""
Twitter Discovery Engine
"""
import random
import logging
from typing import List
from config.settings import settings
from core.database import db
from core.networks.twitter.client import TwitterClient
from core.interfaces import DiscoveryStrategy
from core.models import SocialPost

from core.logger import NetBotLoggerAdapter
logger = NetBotLoggerAdapter(logging.getLogger(__name__), {'network': 'Twitter'})

class TwitterDiscovery(DiscoveryStrategy):
    def __init__(self, client: TwitterClient):
        self.client = client
        self.vip_list = settings.load_vip_list("twitter")
        self.hashtags = settings.load_hashtags("twitter")

    def find_candidates(self, limit: int = 5) -> List[SocialPost]:
        """Tries multiple sources and falls back between VIP and Hashtag."""
        use_vip_first = True
        if self.vip_list and self.hashtags:
            use_vip_first = random.random() < 0.7
        elif self.hashtags:
            use_vip_first = False
        elif not self.vip_list:
            logger.warning("Twitter: No VIPs and No Hashtags defined!")
            return []

        strategies = []
        if use_vip_first:
            strategies = [("VIP", self._fetch_from_vip), ("Hashtag", self._fetch_from_discovery)]
        else:
            strategies = [("Hashtag", self._fetch_from_discovery), ("VIP", self._fetch_from_vip)]

        for strategy_name, fetch_fn in strategies:
            candidates = fetch_fn(amount=limit)
            valid = [p for p in candidates if self.validate_candidate(p)]
            if valid:
                return valid
            logger.info(f"[Twitter] {strategy_name} returned no valid candidates, trying next...")

        return []

    def _fetch_from_vip(self, amount: int) -> List[SocialPost]:
        """Try up to 3 random VIPs and return first non-empty result."""
        if not self.vip_list: return []
        attempts = min(3, len(self.vip_list))
        tried = random.sample(self.vip_list, attempts)
        for target_user in tried:
            logger.info(f"Twitter Discovery: Checking VIP @{target_user}", stage='A')
            posts = self.client.get_user_latest_posts(target_user, limit=amount)
            if posts:
                return posts
        return []

    def _fetch_from_discovery(self, amount: int) -> List[SocialPost]:
        """Try up to 3 random hashtags and return first non-empty result."""
        if not self.hashtags: return []
        attempts = min(3, len(self.hashtags))
        tried = random.sample(self.hashtags, attempts)
        for target_tag in tried:
            logger.info(f"Twitter Discovery: Checking Hashtag #{target_tag}", stage='A')
            posts = self.client.search_posts(target_tag, limit=amount)
            if posts:
                random.shuffle(posts)
                return posts
        return []

    def validate_candidate(self, post: SocialPost) -> bool:
        if not post.id: return False
        
        # 1. Stage A: Collector - Log everything as 'seen'
        # We log immediately to track that we found it
        metrics = getattr(post, 'metrics', {})
        db.log_discovery(post.id, post.platform.value, "discovery", metrics)

        # 2. Stage B: Marketing Filter
        reply_count = metrics.get("reply_count", 0)
        
        # Rule: 5 <= replies <= 50
        # If outside this range, we skip it
        if reply_count < 5:
            logger.warning(f"Skipping {post.id}: Low engagement ({reply_count} replies)", stage='B')
            db.update_discovery_status(post.id, post.platform.value, "skipped", f"Low engagement: {reply_count} replies")
            return False
            
        if reply_count > 50:
            logger.warning(f"Skipping {post.id}: Too crowded ({reply_count} replies)", stage='B')
            db.update_discovery_status(post.id, post.platform.value, "skipped", f"Too crowded: {reply_count} replies")
            return False

        # 3. Check Deduplication (Interaction history)
        if db.check_if_interacted(post.id, post.platform.value):
            logger.warning(f"Skipping {post.id}: Already interacted.", stage='B')
            db.update_discovery_status(post.id, post.platform.value, "skipped", "Already interacted")
            return False
            
        # If we passed all filters, it's a valid candidate for Stage C (Brain)
        return True
