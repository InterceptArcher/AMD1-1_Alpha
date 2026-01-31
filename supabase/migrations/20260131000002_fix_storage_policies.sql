-- Fix storage policies for personalized-pdfs bucket
-- Drop old restrictive policies and create permissive ones

-- Drop old policies (if they exist)
DROP POLICY IF EXISTS "Allow authenticated uploads" ON storage.objects;
DROP POLICY IF EXISTS "Allow service role uploads" ON storage.objects;
DROP POLICY IF EXISTS "Allow public read" ON storage.objects;
DROP POLICY IF EXISTS "Allow service role delete" ON storage.objects;

-- Create permissive policies for the personalized-pdfs bucket
-- Allow all roles to upload PDFs (backend may use anon or service_role key)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE policyname = 'Allow all uploads to personalized-pdfs'
    ) THEN
        CREATE POLICY "Allow all uploads to personalized-pdfs" ON storage.objects
            FOR INSERT
            TO anon, authenticated, service_role
            WITH CHECK (bucket_id = 'personalized-pdfs');
    END IF;
END $$;

-- Allow public read access via signed URLs
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE policyname = 'Allow public read from personalized-pdfs'
    ) THEN
        CREATE POLICY "Allow public read from personalized-pdfs" ON storage.objects
            FOR SELECT
            TO anon, authenticated, service_role
            USING (bucket_id = 'personalized-pdfs');
    END IF;
END $$;

-- Allow deletion for cleanup
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE policyname = 'Allow delete from personalized-pdfs'
    ) THEN
        CREATE POLICY "Allow delete from personalized-pdfs" ON storage.objects
            FOR DELETE
            TO anon, authenticated, service_role
            USING (bucket_id = 'personalized-pdfs');
    END IF;
END $$;

-- Allow updates (for overwriting existing files)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE policyname = 'Allow update in personalized-pdfs'
    ) THEN
        CREATE POLICY "Allow update in personalized-pdfs" ON storage.objects
            FOR UPDATE
            TO anon, authenticated, service_role
            USING (bucket_id = 'personalized-pdfs');
    END IF;
END $$;
