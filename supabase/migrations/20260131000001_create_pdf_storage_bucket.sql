-- Create storage bucket for personalized PDFs
-- This bucket stores generated PDF ebooks for delivery

-- Create the storage bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'personalized-pdfs',
    'personalized-pdfs',
    true,  -- Public bucket for signed URL access
    52428800,  -- 50MB max file size
    ARRAY['application/pdf']
)
ON CONFLICT (id) DO NOTHING;

-- Allow all roles to upload PDFs (backend may use anon or service_role key)
CREATE POLICY "Allow all uploads to personalized-pdfs" ON storage.objects
    FOR INSERT
    TO anon, authenticated, service_role
    WITH CHECK (bucket_id = 'personalized-pdfs');

-- Allow public read access via signed URLs
CREATE POLICY "Allow public read from personalized-pdfs" ON storage.objects
    FOR SELECT
    TO anon, authenticated, service_role, public
    USING (bucket_id = 'personalized-pdfs');

-- Allow deletion for cleanup
CREATE POLICY "Allow delete from personalized-pdfs" ON storage.objects
    FOR DELETE
    TO anon, authenticated, service_role
    USING (bucket_id = 'personalized-pdfs');

-- Allow updates (for overwriting existing files)
CREATE POLICY "Allow update in personalized-pdfs" ON storage.objects
    FOR UPDATE
    TO anon, authenticated, service_role
    USING (bucket_id = 'personalized-pdfs');
