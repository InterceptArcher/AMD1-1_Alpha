-- Personalization Job Tracking Tables (Spec 007)
-- personalization_jobs: Tracks personalization requests
-- personalization_outputs: Stores LLM-generated outputs

-- ============================================================================
-- personalization_jobs table
-- ============================================================================
CREATE TABLE IF NOT EXISTS personalization_jobs (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    created_at TIMESTAMP DEFAULT NOW(),
    email VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    cta VARCHAR(50),
    persona VARCHAR(50),
    buyer_stage VARCHAR(50),
    company_name VARCHAR(255),
    industry VARCHAR(100),
    company_size VARCHAR(50),
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_email ON personalization_jobs(email);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON personalization_jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON personalization_jobs(created_at DESC);

-- ============================================================================
-- personalization_outputs table
-- ============================================================================
CREATE TABLE IF NOT EXISTS personalization_outputs (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    job_id BIGINT REFERENCES personalization_jobs(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    output_json JSONB NOT NULL,
    intro_hook TEXT,
    cta TEXT,
    model_used VARCHAR(100),
    tokens_used INTEGER,
    latency_ms INTEGER,
    compliance_passed BOOLEAN DEFAULT TRUE,
    compliance_issues TEXT[]
);

CREATE INDEX IF NOT EXISTS idx_outputs_job_id ON personalization_outputs(job_id);

-- ============================================================================
-- pdf_deliveries table (for PDF generation tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS pdf_deliveries (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    job_id BIGINT REFERENCES personalization_jobs(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    pdf_url TEXT,
    storage_path TEXT,
    file_size_bytes INTEGER,
    delivered_at TIMESTAMP,
    delivery_status VARCHAR(50) DEFAULT 'pending',
    delivery_channel VARCHAR(50),
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_pdf_job_id ON pdf_deliveries(job_id);
CREATE INDEX IF NOT EXISTS idx_pdf_status ON pdf_deliveries(delivery_status);
