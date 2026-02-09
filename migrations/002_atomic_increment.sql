-- Migration: Add atomic increment function
-- Description: Creates a PostgreSQL function to safely increment interaction counts using UPSERT logic.

CREATE OR REPLACE FUNCTION increment_daily_stats(p_platform TEXT)
RETURNS VOID AS $$
BEGIN
    INSERT INTO daily_stats (date, platform, interaction_count, last_updated)
    VALUES (CURRENT_DATE, p_platform, 1, NOW())
    ON CONFLICT (date, platform)
    DO UPDATE SET 
        interaction_count = daily_stats.interaction_count + 1,
        last_updated = NOW();
END;
$$ LANGUAGE plpgsql;
