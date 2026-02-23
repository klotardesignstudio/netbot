-- Table: content_ideas
-- Stores potential content ideas fetched from RSS feeds or other sources.
CREATE TABLE IF NOT EXISTS content_ideas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_url TEXT NOT NULL UNIQUE,  -- URL of the original article/item
    title TEXT NOT NULL,              -- Title of the article
    summary TEXT,                     -- AI-generated summary/TLDR
    original_content TEXT,            -- Optional: raw content snippet (if needed)
    type TEXT NOT NULL DEFAULT 'news', -- 'news', 'trend', 'thought', etc.
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'rejected', 'published'
    metadata JSONB DEFAULT '{}'::JSONB, -- Extra info (AI reasoning, tags, source name)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster lookups by status
CREATE INDEX IF NOT EXISTS idx_content_ideas_status ON content_ideas(status);
CREATE INDEX IF NOT EXISTS idx_content_ideas_created_at ON content_ideas(created_at);
