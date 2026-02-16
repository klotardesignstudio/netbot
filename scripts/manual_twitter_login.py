"""
Manual Twitter Login Script (Cookie Injection)

Use this script to inject cookies/state from your real browser into the bot's persistent context.
This helps bypass the login screen and anti-bot checks.

Instructions:
1. Log in to Twitter/X on your regular browser (Chrome/Edge/Brave).
2. Open Developer Tools (F12) -> Console.
3. Paste the following JavaScript code to copy your session:

   copy(JSON.stringify({
       cookies: document.cookie.split('; ').map(c => {
           const [name, ...v] = c.split('=');
           return { name, value: v.join('='), domain: ".x.com", path: "/" }
       }),
       origins: [{
           origin: "https://x.com",
           localStorage: Object.entries(localStorage).map(([name, value]) => ({ name, value }))
       }]
   }));

4. A JSON string will be copied to your clipboard.
5. Save it to a file named `twitter_cookies.json` in the project root.
6. Run this script.
"""
import sys
import json
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright

def inject_cookies():
    print("🍪 Manual Twitter Cookie Injection")
    print("====================================")
    
    cookies_file = Path("twitter_cookies.json")
    if not cookies_file.exists():
        print(f"❌ File not found: {cookies_file.absolute()}")
        print("Please create 'twitter_cookies.json' with the content from your browser console.")
        return
        
    try:
        with open(cookies_file, 'r') as f:
            state_data = json.load(f)
    except Exception as e:
        print(f"❌ Invalid JSON in twitter_cookies.json: {e}")
        return

    session_path = Path(__file__).resolve().parent.parent / "browser_state"
    user_data_dir = session_path / "twitter_context"
    user_data_dir.mkdir(exist_ok=True, parents=True)

    print(f"📂 Injecting into Persistent Context: {user_data_dir}")
    
    with sync_playwright() as p:
        # Launch persistent context
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            viewport={'width': 1280, 'height': 800},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        )
        
        page = browser.pages[0] if browser.pages else browser.new_page()
        
        # 1. Go to domain to enable setting local storage
        print("🌐 Navigating to x.com...")
        try:
            page.goto("https://x.com", timeout=30000, wait_until="domcontentloaded")
        except:
            pass
            
        # 2. Add Cookies
        if "cookies" in state_data:
            print(f"🍪 Adding {len(state_data['cookies'])} cookies...")
            browser.add_cookies(state_data["cookies"])
            
        # 3. Add LocalStorage
        if "origins" in state_data:
            print("💾 Adding LocalStorage data...")
            for origin in state_data["origins"]:
                page.goto(origin["origin"])
                for item in origin["localStorage"]:
                    page.evaluate(f"localStorage.setItem('{item['name']}', '{item['value']}')")

        # 4. Save and Verify
        print("✅ Injection complete. Refreshing to verify...")
        page.reload()
        try:
             page.wait_for_selector('div[aria-label="Home"], a[aria-label="Home"], nav[aria-label="Primary"]', timeout=15000)
             print("🎉 Success! You are logged in.")
             
             # Save state file as backup
             browser.storage_state(path=str(session_path / "state_twitter.json"))
             print(f"💾 Backup saved to: {session_path}/state_twitter.json")
        except:
             print("⚠️ Warning: Login not detected immediately. You might need to refresh or solve a captcha manually.")
             input("Press Enter to close browser...")

        browser.close()

if __name__ == "__main__":
    inject_cookies()
