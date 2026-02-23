import os
import time
import requests
from typing import List, Optional
from core.logger import logger

class InstagramPublisher:
    """
    Handles publishing of content to the Instagram Graph API.
    Required Env Vars:
      - IG_ACCESS_TOKEN (Long-lived Page Access Token)
      - IG_ACCOUNT_ID (The Native IG Account ID attached to the Facebook Page)
    """

    def __init__(self):
        self.access_token = os.environ.get("IG_ACCESS_TOKEN")
        self.ig_account_id = os.environ.get("IG_ACCOUNT_ID")
        self.base_url = "https://graph.facebook.com/v19.0"

    def _check_credentials(self) -> bool:
        if not self.access_token or not self.ig_account_id:
            logger.error("Missing IG_ACCESS_TOKEN or IG_ACCOUNT_ID in environment variables.")
            return False
        return True

    def publish_carousel(self, image_urls: List[str], caption: str) -> Optional[str]:
        """
        Executes the 3-step Instagram Carousel Publishing Flow.
        Returns the final Published Media ID if successful.
        """
        if not self._check_credentials():
            return None

        if len(image_urls) < 2:
            logger.error("A carousel requires at least 2 images.")
            return None

        logger.info(f"Starting API Carousel Publish Flow for {len(image_urls)} slides...")

        # Step 1: Create Item Containers
        item_container_ids = []
        for index, url in enumerate(image_urls):
            container_id = self._create_item_container(url)
            if not container_id:
                logger.error(f"Failed to create container for image {index + 1}. Aborting carousel publish.")
                return None
            item_container_ids.append(container_id)
            # Short sleep to respect rate limits
            time.sleep(1)

        # Step 2: Create Carousel Container
        carousel_container_id = self._create_carousel_container(item_container_ids, caption)
        if not carousel_container_id:
            logger.error("Failed to create the Carousel Container Object.")
            return None

        # Give FB servers a moment to process the containers before publishing
        logger.info("Waiting 10 seconds for Facebook servers to process containers...")
        time.sleep(10)

        # Step 3: Publish the Carousel
        published_id = self._publish_container(carousel_container_id)
        if published_id:
            logger.info(f"🎉 Successfully published Carousel to Instagram! ID: {published_id}")
            return published_id
        else:
            logger.error("Failed to publish the final Carousel Container.")
            return None

    def publish_single_image(self, image_url: str, caption: str) -> Optional[str]:
        """Publishes a standard fixed single image."""
        if not self._check_credentials():
            return None

        logger.info("Starting API Single Image Publish Flow...")
        
        # Step 1: Create Media Container
        endpoint = f"{self.base_url}/{self.ig_account_id}/media"
        payload = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.access_token
        }
        
        container_id = self._post_request(endpoint, payload, "Single Media Container")
        if not container_id:
            return None
            
        logger.info("Waiting 5 seconds for Facebook servers to process container...")
        time.sleep(5)
        
        # Step 2: Publish
        published_id = self._publish_container(container_id)
        if published_id:
            logger.info(f"🎉 Successfully published Post to Instagram! ID: {published_id}")
            return published_id
        
        return None

    # --- INTERNAL HTTP HELPERS ---
    
    def _create_item_container(self, image_url: str) -> Optional[str]:
        """Step 1: Creates an individual item container for a carousel slide."""
        endpoint = f"{self.base_url}/{self.ig_account_id}/media"
        payload = {
            "image_url": image_url,
            "is_carousel_item": True,
            "access_token": self.access_token
        }
        return self._post_request(endpoint, payload, "Carousel Item Container")

    def _create_carousel_container(self, children_ids: List[str], caption: str) -> Optional[str]:
        """Step 2: Groups item containers into a single Carousel container."""
        endpoint = f"{self.base_url}/{self.ig_account_id}/media"
        payload = {
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "caption": caption,
            "access_token": self.access_token
        }
        return self._post_request(endpoint, payload, "Carousel Group Container")

    def _publish_container(self, creation_id: str) -> Optional[str]:
        """Step 3: Publishes a previously created Media Container ID."""
        endpoint = f"{self.base_url}/{self.ig_account_id}/media_publish"
        payload = {
            "creation_id": creation_id,
            "access_token": self.access_token
        }
        return self._post_request(endpoint, payload, "Publish Container")

    def _post_request(self, url: str, payload: dict, operation_name: str) -> Optional[str]:
        """Wrapper for POST requests that parses the id from the response."""
        try:
            response = requests.post(url, data=payload)
            response_data = response.json()
            
            if response.status_code == 200 and "id" in response_data:
                item_id = response_data["id"]
                logger.debug(f"{operation_name} succeeded with ID: {item_id}")
                return item_id
            else:
                logger.error(f"{operation_name} failed. Status: {response.status_code}. Response: {response_data}")
                # Sometimes IG API gives a User-facing error message
                error_body = response_data.get("error", {})
                if "error_user_msg" in error_body:
                    logger.error(f"IG Human Error: {error_body['error_user_msg']}")
                return None
                
        except Exception as e:
            logger.error(f"HTTP Exception during {operation_name}: {e}")
            return None
