-- Up
-- Migration: 011_fix_rls_cascade
-- Description: Fix RLS policies to allow the Supabase Python client (using anon key) to read/write cascade tables.

CREATE POLICY "Allow anon access to monthly_themes" ON monthly_themes FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "Allow anon access to weekly_topics" ON weekly_topics FOR ALL TO anon USING (true) WITH CHECK (true);
CREATE POLICY "Allow anon access to content_queue" ON content_queue FOR ALL TO anon USING (true) WITH CHECK (true);

-- Down
-- DROP POLICY IF EXISTS "Allow anon access to monthly_themes" ON monthly_themes;
-- DROP POLICY IF EXISTS "Allow anon access to weekly_topics" ON weekly_topics;
-- DROP POLICY IF EXISTS "Allow anon access to content_queue" ON content_queue;
