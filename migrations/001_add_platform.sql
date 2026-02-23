-- Migration: Add platform support
-- Description: Adds 'platform' column to interactions and daily_stats tables to support multiple social networks.

-- 1. Add platform column to interactions table
ALTER TABLE interactions 
ADD COLUMN platform VARCHAR(50) NOT NULL DEFAULT 'instagram';

-- Optional: Add an index for faster querying by platform
CREATE INDEX idx_interactions_platform ON interactions(platform);
CREATE INDEX idx_interactions_post_id_platform ON interactions(post_id, platform);

-- 2. Update daily_stats to track limits per platform
-- First, add the column
ALTER TABLE daily_stats 
ADD COLUMN platform VARCHAR(50) NOT NULL DEFAULT 'instagram';

-- If there is a unique constraint on 'date', we need to drop it and create a composite one
-- assuming the constraint name. If unknown, you might need to check standard naming or just run the add constraint.
-- ALTER TABLE daily_stats DROP CONSTRAINT daily_stats_date_key; -- Uncomment if needed matching your schema

-- Add unique constraint for date + platform
ALTER TABLE daily_stats 
ADD CONSTRAINT daily_stats_date_platform_key UNIQUE (date, platform);
