-- Up
-- Migration: 013_multiple_images
-- Description: Alters the content_queue table to support multiple image URLs as a JSONB array.

ALTER TABLE content_queue 
DROP COLUMN IF EXISTS image_url;

ALTER TABLE content_queue 
ADD COLUMN IF NOT EXISTS image_urls JSONB DEFAULT '[]'::jsonb;

-- Down
-- ALTER TABLE content_queue DROP COLUMN IF EXISTS image_urls;
-- ALTER TABLE content_queue ADD COLUMN image_url TEXT;
