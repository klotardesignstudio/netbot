import os
from datetime import datetime
from core.database import db
from core.logger import logger

class StorageManager:
    """Handles uploading generated content into Supabase Storage."""
    
    def __init__(self, bucket_name: str = "instagram-drafts"):
        self.bucket_name = bucket_name

    def upload_file(self, file_path: str, destination_path: str = None) -> str:
        """
        Uploads a local file to Supabase Storage and returns the public URL.
        """
        if not os.path.exists(file_path):
            logger.error(f"Storage Error: File not found at {file_path}")
            return None

        # Build destination path if not provided
        if not destination_path:
            filename = os.path.basename(file_path)
            today = datetime.now().strftime("%Y-%m-%d")
            destination_path = f"insta_posts/{today}/{filename}"

        try:
            with open(file_path, "rb") as f:
                res = db.client.storage.from_(self.bucket_name).upload(
                    path=destination_path,
                    file=f,
                    file_options={"content-type": "image/png", "upsert": "true"}
                )
            
            # Construct public URL
            public_url = db.client.storage.from_(self.bucket_name).get_public_url(destination_path)
            logger.info(f"✅ File uploaded to Storage: {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"Error uploading file {file_path} to Storage: {e}")
            return None

    def upload_files(self, file_paths: list) -> list:
        """Uploads multiple files and returns their public URLs."""
        urls = []
        for path in file_paths:
            url = self.upload_file(path)
            if url:
                urls.append(url)
        return urls
