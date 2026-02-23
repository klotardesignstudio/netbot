"""
Playwright Twitter/X Login Script

Run this to create the browser session for Twitter.
Opens a visible browser for manual login, then saves the session.
"""
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright

def setup_twitter_login():
    print("🐦 Playwright Twitter/X Login Setup")
    print("=" * 50)
    print("A browser window will open.")
    print("1. Login to Twitter/X normally")
    print("2. Complete any challenges (2FA, puzzles)")
    print("3. Wait until you see your feed")
    print("=" * 50)
    input("Press Enter to start...")
    
    session_path = Path(__file__).resolve().parent.parent / "browser_state"
    session_path.mkdir(exist_ok=True, parents=True)
    
    user_data_dir = session_path / "twitter_context"
    user_data_dir.mkdir(exist_ok=True)

    with sync_playwright() as p:
        # Use persistent context for better "real user" simulation
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/Sao_Paulo',
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--disable-remote-fonts',
                '--window-size=1280,800',
            ]
        )
        
        page = browser.pages[0] if browser.pages else browser.new_page()
        
        print("\n🌐 Opening X.com...")
        try:
            page.goto('https://x.com/i/flow/login', timeout=60000)
        except Exception as e:
            print(f"⚠️ Error loading page (might be okay if open): {e}")
        
        print("⏳ Waiting for you to login...")
        print("   (The script will detect when you're logged in)")
        
        try:
            # Wait for Home icon or Tweet button
            page.wait_for_selector(
                'div[aria-label="Home"], a[aria-label="Home"], nav[aria-label="Primary"]',
                timeout=300000  # 5 minutes
            )
            print("\n✅ Login detected!")
            
            # Save browser state (cookies/origins) explicitly to JSON for the client to use
            # The client usually uses `storage_state` from a file.
            # Even though we use persistent context here, we need the JSON for the main bot
            # if the main bot uses `new_context(storage_state=...)`.
            browser.storage_state(path=str(session_path / "state_twitter.json"))
            print(f"\n💾 Session JSON saved to: {session_path}/state_twitter.json")
            print(f"📂 Persistent Context saved to: {user_data_dir}")
            
        except Exception as e:
            print(f"\n⚠️ Timeout or error: {e}")
            browser.close()
            return False
        
        browser.close()
        
    print("\n🎉 Success! You can now use the Twitter Client.")
    return True

if __name__ == "__main__":
    success = setup_twitter_login()
    if not success:
        sys.exit(1)
