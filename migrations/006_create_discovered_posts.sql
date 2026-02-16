-- Migration: Create discovered_posts table for advanced discovery flow
-- Description: Stores all posts found by collectors with their metrics and status history.

CREATE TABLE IF NOT EXISTS discovered_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    hashtag_source TEXT,
    metrics JSONB DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'seen',
    ai_reasoning TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent duplicate processing of the same post on the same platform
    CONSTRAINT unique_post_per_platform UNIQUE(external_id, platform)
);

-- Index for high-performance JSONB filtering on metrics (e.g., "likes > 10")
CREATE INDEX IF NOT EXISTS idx_discovered_posts_metrics ON discovered_posts USING GIN (metrics);

-- Index for fast status lookups (e.g., "Give me all 'seen' posts")
CREATE INDEX IF NOT EXISTS idx_discovered_posts_status ON discovered_posts(status);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_discovered_posts_updated_at
    BEFORE UPDATE ON discovered_posts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
