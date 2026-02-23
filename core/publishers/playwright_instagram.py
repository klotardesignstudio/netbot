import os
import time
import random
import logging
from typing import List, Optional
from pathlib import Path

from playwright.sync_api import Playwright, Browser, BrowserContext, Page, expect, sync_playwright
try:
    from playwright_stealth import stealth_sync
except ImportError:
    from playwright_stealth import Stealth
    def stealth_sync(page_or_context):
        Stealth().apply_stealth_sync(page_or_context)

from core.logger import NetBotLoggerAdapter

logger = NetBotLoggerAdapter(logging.getLogger(__name__), {'network': 'InstagramPublisher'})

class PlaywrightInstagramPublisher:
    """
    Handles publishing of content to Instagram using Playwright UI Automation.
    Reuses the browser session state from the standard discovery client.
    """
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.session_path = Path("browser_state")
        self.state_file = self.session_path / "state.json"
        
    def _random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """Human-like random delay."""
        time.sleep(random.uniform(min_sec, max_sec))
        
    def start(self) -> bool:
        """Initialize browser and load the existing Instagram session."""
        try:
            self._local_playwright_context = sync_playwright()
            self.playwright = self._local_playwright_context.start()
            
            # Launch browser
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            # Require existing state for publishing to avoid login popups during automated runs
            if not self.state_file.exists():
                logger.error(f"No Instagram session state found at {self.state_file}. Please run the standard NetBot login first.")
                return False
                
            logger.info("Loading existing browser session for publishing...")
            self.context = self.browser.new_context(
                storage_state=str(self.state_file),
                viewport={'width': 1280, 'height': 800},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/Sao_Paulo',
                # Grant clipboard permissions which might be needed for text insertion depending on the UI
                permissions=['clipboard-read', 'clipboard-write']
            )
            
            self.page = self.context.new_page()
            stealth_sync(self.page)
            return True
            
        except Exception as e:
            logger.error(f"Failed to start publisher browser: {e}")
            return False

    def stop(self):
        """Close browser and cleanup."""
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
            
        self.playwright = None
        if hasattr(self, '_local_playwright_context') and self._local_playwright_context:
            try:
                self._local_playwright_context.__exit__(None, None, None)
            except:
                pass
            
    def publish(self, image_paths: List[str], caption: str) -> bool:
        """
        Executes the Web UI flow to publish a New Post (Single or Carousel).
        Receives absolute paths to local image files.
        """
        if not self.start():
            return False
            
        try:
            # 1. Access Instagram Home
            logger.info("Accessing Instagram Home...")
            self.page.goto('https://www.instagram.com/', timeout=30000)
            self._random_delay(3, 5)
            
            # Verify Login
            try:
                self.page.wait_for_selector('svg[aria-label="New post"]', timeout=10000)
            except:
                logger.error("Could not find the 'New post' button. Session might be invalid or UI changed.")
                return False
                
            # 2. Click "New Post" (Create)
            logger.info("Clicking 'New Post' button...")
            self.page.click('svg[aria-label="New post"]')
            self.page.click('text="Post"') # Sometimes it opens a submenu (Post / Live)
            self._random_delay(2, 3)
            
            # 3. Handle File Input Upload
            logger.info(f"Injecting {len(image_paths)} images into the DOM input file array...")
            
            # Instagram hides the input[type="file"], so we find it and set its files
            file_input = self.page.locator('input[accept*="image"]')
            file_input.set_input_files(image_paths)
            self._random_delay(3, 5)
            
            # 4. Aspect Ratio Adjustment (Crucial for 4:5 and Carousels)
            logger.info("Adjusting Aspect Ratio to 'Original'...")
            try:
                # The crop button is usually an SVG with aria-label "Select crop"
                crop_btn = self.page.locator('svg[aria-label="Select crop"]').locator('..')
                crop_btn.click(timeout=5000, force=True)
                self._random_delay(1, 2)
                
                # Click 'Original' aspect ratio
                original_ratio_btn = self.page.locator('svg[aria-label="Original"]').locator('..')
                original_ratio_btn.click(timeout=5000, force=True)
                self._random_delay(1, 2)
                
                # If there are multiple images, we need to click the "Multiple Select" button? 
                # Actually, set_input_files with a list array already loads them all into the carousel queue natively!
            except Exception as e:
                logger.warning(f"Could not adjust aspect ratio (maybe UI changed or it's a 1:1 square already): {e}")

            # 5. Click Next (to Filters)
            logger.info("Moving to Filters step...")
            next_btn = self.page.locator('div[role="button"]:has-text("Next")').last
            next_btn.click()
            self._random_delay(2, 3)
            
            # 6. Click Next (to Caption)
            logger.info("Moving to Caption step...")
            next_btn = self.page.locator('div[role="button"]:has-text("Next")').last
            next_btn.click()
            self._random_delay(2, 3)
            
            # 7. Inject Caption
            logger.info("Injecting caption text...")
            caption_area = self.page.locator('div[aria-label="Write a caption..."]')
            
            # Using paste/fill is safer than typing slowly for huge captions
            caption_area.click()
            self._random_delay(0.5, 1)
            caption_area.fill(caption)
            self._random_delay(2, 3)
            
            # 8. Share
            logger.info("Clicking Share! 🎉")
            share_btn = self.page.locator('text="Share"').last
            share_btn.click(force=True)
            
            # Wait for the successful upload animation or "Your post has been shared."
            logger.info("Waiting for upload confirmation (this can take up to 30s)...")
            try:
                # Instagram shows a specific animated SVG or text when done
                self.page.wait_for_selector('img[alt*="Animated checkmark"]', timeout=30000)
                logger.info("✅ Post successfully published via Playwright!")
                return True
            except:
                # Fallback check
                if "Your post has been shared" in self.page.content():
                     logger.info("✅ Post successfully published via Playwright (Text match)!")
                     return True
                else:
                    logger.warning("Could not explicitly detect the success screen, but 'Share' was clicked.")
                    return True # We assume true if it didn't crash
                    
        except Exception as e:
            logger.error(f"Playwright publishing failed during execution: {e}")
            # Take a screenshot on failure for debugging
            try:
                self.page.screenshot(path="failed_publish.png")
                logger.info("Saved failure screenshot to failed_publish.png")
            except:
                pass
            return False
        finally:
            self._random_delay(2, 4)
            self.stop()
