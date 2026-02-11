-- Remove the overly restrictive unique constraint
ALTER TABLE content_ideas DROP CONSTRAINT IF EXISTS content_ideas_source_url_key;

-- Add a partial unique index to maintain deduplication for news flow (RSS)
-- This allows multiple 'cli' or 'project_config' source_urls while keeping news unique.
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_news_url ON content_ideas(source_url) WHERE (type = 'news');
