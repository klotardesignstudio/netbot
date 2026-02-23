-- Up
-- Migration: 012_storage_rls
-- Description: Creates RLS policies for the instagram-drafts bucket

-- Enable RLS on storage.objects if not already (usually enabled by default)
-- ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Allow anyone to upload files to this specific bucket
CREATE POLICY "Allow public uploads to instagram-drafts"
ON storage.objects FOR INSERT TO public
WITH CHECK (bucket_id = 'instagram-drafts');

-- Allow anyone to update existing files in this bucket
CREATE POLICY "Allow public updates to instagram-drafts"
ON storage.objects FOR UPDATE TO public
USING (bucket_id = 'instagram-drafts');

-- Allow anyone to read files from this bucket
CREATE POLICY "Allow public reads on instagram-drafts"
ON storage.objects FOR SELECT TO public
USING (bucket_id = 'instagram-drafts');

-- Down
-- DROP POLICY IF EXISTS "Allow public reads on instagram-drafts" ON storage.objects;
-- DROP POLICY IF EXISTS "Allow public updates to instagram-drafts" ON storage.objects;
-- DROP POLICY IF EXISTS "Allow public uploads to instagram-drafts" ON storage.objects;
