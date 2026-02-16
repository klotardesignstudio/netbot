import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from main import AgentOrchestrator
from core.database import db
from core.logger import logger
from config.settings import settings

def run_test():
    print("🚀 Starting Discovery Flow Test (DRY RUN)...")
    
    # Force Dry Run
    settings.dry_run = True
    os.environ["DRY_RUN"] = "True"
    
    orchestrator = AgentOrchestrator()
    
    # Filter for Twitter and Dev.to only for speed
    orchestrator.platform_configs = [
        c for c in orchestrator.platform_configs 
        if c["platform"] in ["twitter", "devto"]
    ]
    
    print(f"🎯 Testing platforms: {[c['name'] for c in orchestrator.platform_configs]}")
    
    try:
        orchestrator.run_cycle()
        print("✅ Cycle complete.")
        
        # Check DB results
        print("\n🔎 Checking 'discovered_posts' table for recent entries...")
        # We can't easily query with the current db wrapper methods unless we add a new one or use raw client
        # Let's try to list recent entries if possible, or just trust the logs.
        # But for verification, let's use the explicit raw query if we can, or just read logs.
        
        res = db.client.table("discovered_posts").select("*").order("created_at", desc=True).limit(5).execute()
        for idx, row in enumerate(res.data):
             print(f"[{idx+1}] {row['platform']} | ID: {row['external_id']} | Status: {row['status']} | Reason: {row.get('ai_reasoning', 'N/A')}")
             
    except Exception as e:
        print(f"❌ Error during test: {e}")
    finally:
        orchestrator.stop()

if __name__ == "__main__":
    run_test()
