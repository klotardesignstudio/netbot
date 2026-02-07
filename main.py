"""
NetBot - Omnichannel AI Persona

Main entry point for the engagement bot.
Orchestrates multiple social network clients and the central AI agent.
"""
import time
import random
import signal
import sys
from typing import List
from config.settings import settings
from core.database import db
from core.agent import agent
from core.logger import logger
from core.interfaces import SocialNetworkClient, DiscoveryStrategy

# Networks
from core.networks.instagram.client import client as instagram_client
from core.networks.instagram.discovery import discovery as instagram_discovery

class AgentOrchestrator:
    def __init__(self):
        self.networks: List[dict] = []
        self._setup_networks()
        self.running = True

    def _setup_networks(self):
        """Register enabled networks."""
        # In the future, this could be dynamic based on settings
        self.networks.append({
            "name": "Instagram",
            "client": instagram_client,
            "discovery": instagram_discovery
        })

    def start(self):
        """Main execution loop."""
        logger.info("🤖 NetBot Orchestrator Initialized")
        
        # Verify DB connection
        try:
            # We check total interactions for now, platform specific breakdown is in logs
            # This is a bit of a hack until we update get_daily_count to be cleaner in main
            count = db.get_daily_count(platform="instagram") 
            logger.info(f"Connected to Supabase. Daily count (IG): {count}")
        except Exception as e:
            logger.error(f"Failed to connect to DB: {e}. Check .env keys.")
            return

        # Start Clients
        for net in self.networks:
            client: SocialNetworkClient = net["client"]
            if not client.login():
                logger.error(f"Failed to login to {net['name']}. Removing from active list.")
                self.networks.remove(net)

        if not self.networks:
            logger.error("No active networks. Exiting.")
            return

        if settings.dry_run:
            logger.warning("⚠️ MODE: DRY RUN (No comments will be posted)")

        # Loop
        while self.running:
            try:
                self.run_cycle()
                
                # Sleep between cycles
                short_sleep = random.randint(60, 300)  # 1-5 mins
                logger.info(f"Cycle finished. Waiting {short_sleep}s before next check...")
                time.sleep(short_sleep)
                
            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                logger.exception(f"Error in main loop: {e}")
                time.sleep(60)

    def run_cycle(self):
        """Single execution cycle across all networks."""
        logger.info("--- Starting Cycle ---")

        for net in self.networks:
            name = net["name"]
            client: SocialNetworkClient = net["client"]
            discovery: DiscoveryStrategy = net["discovery"]
            
            # Check Limits (Per platform)
            current_count = db.get_daily_count(platform=client.platform.value)
            if current_count >= settings.daily_interaction_limit:
                logger.info(f"[{name}] Daily limit reached ({current_count}/{settings.daily_interaction_limit}). Skipping...")
                continue

            # Discovery
            logger.info(f"[{name}] Discovery started...")
            candidates = discovery.find_candidates(limit=5)
            
            if not candidates:
                logger.info(f"[{name}] No candidates found.")
                continue

            # Attempt Interaction
            interacted = False
            for i, post in enumerate(candidates):
                try:
                    logger.info(f"[{name}] Analyzing Post {i+1}/{len(candidates)}: {post.id}")
                    
                    # Agent Analysis
                    decision = agent.decide_and_comment(post)
                    
                    if decision.should_act:
                        logger.info(f"[{name}] Decided to ACT: {decision.content}")
                        
                        # Execute Action
                        client.like_post(post)
                        time.sleep(random.uniform(1, 2))
                        
                        success = client.post_comment(post, decision.content)
                        
                        if success:
                            # Log
                            db.log_interaction(
                                post_id=post.id,
                                username=post.author.username,
                                comment_text=decision.content,
                                platform=client.platform.value,
                                metadata={"reasoning": decision.reasoning}
                            )
                            
                            interacted = True
                            
                            # Jitter
                            sleep_time = random.randint(settings.min_sleep_interval, settings.max_sleep_interval)
                            logger.info(f"[{name}] Interaction successful. Sleeping {sleep_time}s...")
                            time.sleep(sleep_time)
                            break # Move to next network
                        else:
                            logger.error(f"[{name}] Failed to execute action.")
                    else:
                        logger.info(f"[{name}] Skipped. Reason: {decision.reasoning}")
                
                except Exception as e:
                    logger.error(f"[{name}] Error processing candidate {post.id}: {e}")
                    continue
            
            if not interacted:
                logger.info(f"[{name}] Finished candidates with no interaction.")

    def stop(self, signum=None, frame=None):
        """Cleanup."""
        logger.info("Shutting down...")
        self.running = False
        for net in self.networks:
            try:
                net["client"].stop()
            except:
                pass
        sys.exit(0)


if __name__ == "__main__":
    orchestrator = AgentOrchestrator()
    
    signal.signal(signal.SIGINT, orchestrator.stop)
    signal.signal(signal.SIGTERM, orchestrator.stop)
    
    orchestrator.start()
