-- Create projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    stack TEXT,
    phase TEXT,
    recent_challenge TEXT,
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

-- Allow anonymous access (assuming temporary for local dev/CLI)
CREATE POLICY "Allow all access to projects for now" ON projects
    FOR ALL USING (true) WITH CHECK (true);
