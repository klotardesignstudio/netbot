import sys
import os
import argparse
from datetime import datetime, date
import json
import logging
import asyncio
from typing import Optional, Dict, Any

from telegram import Update, Bot
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from config.settings import settings
from core.database import db
from core.logger import logger
from core.notifications import TelegramNotifier
import re

from core.cascade.strategists import StrategicRoadmapper, WeeklyTactician, DailyBriefingAgent
from core.cascade.makers import VisualDesigner, Copywriter, SlideContentGenerator
from core.cascade.renderer import PillowRenderer
from core.cascade.storage import StorageManager

from core.publishers.playwright_instagram import PlaywrightInstagramPublisher

class ContentOrchestrator:
    """Main orchestrator for the NetBot v2 Content Cascade."""
    
    def __init__(self):
        self.roadmapper = StrategicRoadmapper()
        self.tactician = WeeklyTactician()
        self.briefer = DailyBriefingAgent()
        self.designer = VisualDesigner()
        self.slide_generator = SlideContentGenerator()
        self.renderer = PillowRenderer()
        self.copywriter = Copywriter()
        self.storage = StorageManager()
        self.notifier = TelegramNotifier()
        self.brand_info = self._extract_brand_guidelines()
        
    def _extract_brand_guidelines(self) -> Dict[str, str]:
        """Reads brand.md to establish dynamic branding defaults."""
        brand = {
            "bg_color": "#1E1E1E",     # Deep Charcoal (Dark)
            "text_color": "#F9F9F9",   # Pure Ghost (White)
            "accent_color": "#FF4F00", # Action Orange
            "handle": f"@{os.getenv('IG_USERNAME', 'netbot')}"
        }
        
        try:
            brand_file = os.path.join(settings.BASE_DIR, "docs", "persona", "brand.md")
            if os.path.exists(brand_file):
                with open(brand_file, "r") as f:
                    content = f.read()
                    # Attempt to find common color names and their hex codes via regex
                    # Example format in brand.md: "Deep Charcoal (#1E1E1E): Background"
                    bg_match = re.search(r"Background.*?#([A-Fa-f0-9]{6})", content, re.IGNORECASE)
                    if bg_match: brand['bg_color'] = f"#{bg_match.group(1)}"
                    
                    text_match = re.search(r"(?:Tipografia|texto).*?#([A-Fa-f0-9]{6})", content, re.IGNORECASE)
                    if text_match: brand['text_color'] = f"#{text_match.group(1)}"
        except Exception as e:
            logger.warning(f"Could not parse brand rules automatically: {e}")
            
        return brand
        
    def _get_or_create_monthly_theme(self, current_date: date) -> Optional[Dict[str, Any]]:
        """Ensures a monthly theme exists for the target month."""
        try:
            res = db.client.table("monthly_themes").select("*") \
                  .eq("year", current_date.year) \
                  .eq("month", current_date.month).limit(1).execute()
                  
            if res.data:
                return res.data[0]
                
            # If not found, generate semester plan
            logger.info("No monthly theme found. Triggering Strategic Roadmapper...")
            themes = self.roadmapper.generate_semester_plan(current_date.year, current_date.month)
            if themes:
                return themes[0]
            return None
            
        except Exception as e:
            logger.error(f"Error fetching monthly theme: {e}")
            return None

    def _get_or_create_weekly_topic(self, theme: Dict[str, Any], current_date: date) -> Optional[Dict[str, Any]]:
        """Ensures a weekly topic exists for the target week."""
        current_iso_week = current_date.isocalendar()[1]
        try:
            res = db.client.table("weekly_topics").select("*") \
                  .eq("year", current_date.year) \
                  .eq("week_number", current_iso_week).limit(1).execute()
                  
            if res.data:
                return res.data[0]
                
            # If not found, generate tactics for this month
            logger.info("No weekly topic found. Triggering Weekly Tactician...")
            topics = self.tactician.generate_weekly_topics(
                monthly_theme_id=theme['id'],
                year=theme['year'],
                month=theme['month'],
                theme=theme['theme'],
                description=theme['description']
            )
            
            # Find the specific one for this week
            for t in topics:
                if t['week_number'] == current_iso_week:
                    return self._fetch_weekly_topic_by_week(current_date.year, current_iso_week)
            return None
            
        except Exception as e:
            logger.error(f"Error fetching weekly topic: {e}")
            return None

    def _fetch_weekly_topic_by_week(self, year: int, week: int) -> Optional[Dict[str, Any]]:
        try:
           res = db.client.table("weekly_topics").select("*").eq("year", year).eq("week_number", week).limit(1).execute()
           return res.data[0] if res.data else None
        except:
           return None

    def _get_todays_content(self, current_date: date, platform: str) -> Optional[Dict[str, Any]]:
        try:
            res = db.client.table("content_queue").select("*").eq("post_date", current_date.isoformat()).eq("platform", platform).limit(1).execute()
            if res.data:
                return res.data[0]
            return None
        except:
            return None

    async def _publish_direct(self, queue_id: str, image_urls: list, caption: str, platform: str) -> bool:
        """Publishes the downloaded images directly to Playwright and updates the DB."""
        import requests
        import tempfile
        
        local_files = []
        try:
            for i, url in enumerate(image_urls):
                resp = requests.get(url)
                if resp.status_code == 200:
                    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                    temp_file.write(resp.content)
                    temp_file.close()
                    local_files.append(temp_file.name)
                else:
                    logger.error("Failed to download image from storage.")
                    return False
                    
            def run_publish_sync(files, cap):
                if platform == "instagram":
                    publisher = PlaywrightInstagramPublisher(headless=False)
                    return publisher.publish(files, cap)
                return False
                
            success = await asyncio.to_thread(run_publish_sync, local_files, caption)
            
            if success:
                db.client.table("content_queue").update({"status": "published"}).eq("id", queue_id).execute()
                logger.info(f"✅ Post publicado no {platform}.")
                return True
            else:
                logger.error("❌ A automação Playwright falhou.")
                return False
                
        except Exception as e:
            logger.error(f"Error during publishing pipeline: {e}")
            return False
        finally:
            for f in local_files:
                if os.path.exists(f):
                    os.remove(f)

    async def _wait_for_approval_and_publish(self, queue_id: str, image_urls: list, caption: str, platform: str):
        """
        Starts a temporary Telegram bot polling session to listen *only* for this specific post's approval.
        """
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN missing. Cannot wait for approval.")
            return

        # Create an event to signal when we are done
        approval_event = asyncio.Event()
        publish_success = False

        async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            nonlocal publish_success
            query = update.callback_query
            await query.answer()
            
            data = query.data
            
            if data == f"approve_{queue_id}":
                await query.edit_message_text(text=f"{query.message.text}\n\n⏳ <b>Iniciando Publicação via Playwright...</b>", parse_mode="HTML")
                
                success = await self._publish_direct(queue_id, image_urls, caption, platform)
                
                if success:
                    await query.edit_message_text(text=f"{query.message.text}\n\n✅ <b>Sucesso! Post publicado no {platform}.</b>", parse_mode="HTML")
                    publish_success = True
                else:
                    await query.edit_message_text(text=f"{query.message.text}\n\n❌ <b>Erro! A automação Playwright falhou.</b>", parse_mode="HTML")
                        
                approval_event.set()
                
            elif data == f"reject_{queue_id}":
                db.client.table("content_queue").update({"status": "rejected"}).eq("id", queue_id).execute()
                await query.edit_message_text(text=f"{query.message.text}\n\n🚫 <b>Post Rejeitado e arquivado.</b>", parse_mode="HTML")
                approval_event.set()

        # Build application
        application = Application.builder().token(token).build()
        application.add_handler(CallbackQueryHandler(button_callback))
        
        logger.info("⏳ Waiting for your approval on Telegram...")
        
        # Start application polling in the background
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # Wait until the event is triggered (button clicked)
        await approval_event.wait()
        
        # Cleanup and stop polling
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        
        if publish_success:
             logger.info("🎉 Cascade Complete & Successfully Published End-to-End!")
        else:
             logger.info("🛑 Cascade Complete (Post rejected or failed to publish).")

    async def run_cascade(self, platform: str = "instagram", target_date: date = None):
        """Executes the full content cascade flow."""
        current_date = target_date or datetime.now().date()
        logger.info(f"🚀 Starting Cascade Workflow for {current_date} on {platform}")
        
        existing_post = self._get_todays_content(current_date, platform)
        if existing_post:
             status = existing_post.get("status")
             if status == "published":
                  logger.info(f"✅ Content for {current_date} on {platform} is already published. Skipping.")
                  return
             elif status == "approved":
                  logger.info(f"✅ Content is already approved. Proceeding straight to publishing.")
                  await self._publish_direct(existing_post['id'], existing_post.get('image_urls', []), existing_post.get('caption', ''), platform)
                  return
             elif status == "pending_approval":
                  logger.info(f"⏳ Content is pending approval. Resending Notification and Waiting...")
                  queue_id = existing_post['id']
                  msg = (
                      f"🎨 <b>Post Pendente de Aprovação!</b>\n\n"
                      f"<b>Formato:</b> {existing_post.get('format', 'N/A')}\n\n"
                      f"<b>Legenda (Preview):</b>\n<i>{existing_post.get('caption', '')[:150]}...</i>\n\n"
                      f"<b>ID:</b> <code>{queue_id}</code>"
                  )
                  keyboard = {"inline_keyboard": [[{"text": "✅ Aprovar e Publicar", "callback_data": f"approve_{queue_id}"}, {"text": "❌ Rejeitar", "callback_data": f"reject_{queue_id}"}]]}
                  self.notifier.send_message(msg, reply_markup=keyboard)
                  await self._wait_for_approval_and_publish(queue_id, existing_post.get('image_urls', []), existing_post.get('caption', ''), platform)
                  return
        
        # 1. Strategic Level
        theme = self._get_or_create_monthly_theme(current_date)
        if not theme:
            logger.error("Failed to establish Monthly Theme. Aborting cascade.")
            return
            
        # 2. Tactical Level
        topic = self._get_or_create_weekly_topic(theme, current_date)
        if not topic:
            logger.error("Failed to establish Weekly Topic. Aborting cascade.")
            return
            
        logger.info(f"Targeting Topic: {topic['topic']}")
        
        # 3. Operational Briefing
        briefing = self.briefer.generate_briefing(topic['topic'])
        if not briefing:
            logger.error("Failed to generate Daily Briefing. Aborting cascade.")
            return
            
        # 4. Content Generation (Makers)
        # 4.1 Visual JSON
        visual_json = self.designer.generate_visual_json(briefing)
        if not visual_json:
            logger.error("Failed to generate Visual JSON. Aborting cascade.")
            return
            
        print("\n--- GENERATED VISUAL JSON ---")
        print(json.dumps(visual_json, indent=2, ensure_ascii=False))
        print("-----------------------------\n")
            
        # 4.2 Copywriting
        caption = self.copywriter.generate_caption(briefing, visual_json)
        if not caption:
            logger.error("Failed to generate Caption. Aborting cascade.")
            return

        # 4.3 Image Generation (Cover)
        image_path = self.designer.generate_image(visual_json)
        if not image_path:
            logger.error("Failed to generate Image. Aborting cascade.")
            return
            
        all_image_paths = [image_path]

        # 4.4 Internal Slides Generation
        if briefing['format'] == 'carousel_cover':
            slide_contents = self.slide_generator.generate_slides(briefing)
            if slide_contents:
                # Dynamic Branding Override based on Visual JSON if provided, otherwise use brand.md defaults
                # Check if visual_json asks for a specific text color, otherwise fallback
                text_color = self.brand_info['text_color']
                bg_color = self.brand_info['bg_color']
                
                # Note: Currently visual_json only governs the COVER, but if it has background insights, we could use them.
                # For now, stick strictly to the User's brand guidelines identity.
                
                internal_paths = self.renderer.generate_carousel_slides(
                    slide_contents, 
                    bg_color_hex=bg_color,
                    text_color_hex=text_color,
                    handle=self.brand_info['handle']
                )
                all_image_paths.extend(internal_paths)

        # 5. Storage / Finalization 
        image_urls = self.storage.upload_files(all_image_paths)
        if not image_urls:
            logger.error("Failed to upload images. Aborting cascade.")
            return
            
        # Save to Content Queue
        try:
            queue_data = {
                "weekly_topic_id": topic['id'],
                "post_date": current_date.isoformat(),
                "platform": platform,
                "format": briefing['format'],
                "briefing_json": briefing,
                "visual_prompt": visual_json,
                "image_urls": image_urls,
                "caption": caption,
                "status": "pending_approval"
            }
            
            res = db.client.table("content_queue").insert(queue_data).execute()
            queue_id = res.data[0]['id']
            
            # 6. Telegram Notification
            msg = (
                f"🎨 <b>Novo Post Gerado!</b>\n\n"
                f"<b>Tema:</b> {theme['theme']}\n"
                f"<b>Tópico da Semana:</b> {topic['topic']}\n"
                f"<b>Formato:</b> {briefing['format']}\n\n"
                f"<b>Legenda (Preview):</b>\n<i>{caption[:150]}...</i>\n\n"
                f"<b>ID:</b> <code>{queue_id}</code>"
            )
            
            # Action buttons for the Telegram message
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "✅ Aprovar e Publicar", "callback_data": f"approve_{queue_id}"},
                        {"text": "❌ Rejeitar", "callback_data": f"reject_{queue_id}"}
                    ]
                ]
            }
            
            self.notifier.send_message(msg, reply_markup=keyboard)
            logger.info("🎉 Content queued and notified! Passing control to Approval Listener...")
            
            # 7. Wait for Telegram Approval inside this script
            await self._wait_for_approval_and_publish(queue_id, image_urls, caption, platform)
            
        except Exception as e:
            logger.error(f"Database error during finalization: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Run NetBot Content Cascade")
    parser.add_argument("--date", type=str, help="Target date YYYY-MM-DD", default=None)
    args = parser.parse_args()
    
    target = None
    if args.date:
        target = datetime.strptime(args.date, "%Y-%m-%d").date()
        
    orchestrator = ContentOrchestrator()
    await orchestrator.run_cascade(target_date=target)

if __name__ == "__main__":
    asyncio.run(main())

