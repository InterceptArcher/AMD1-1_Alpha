# AMD1-1_Alpha: Personalization Pipeline

**A production-ready post-click personalization system for LinkedIn ebooks.**

## Overview

This system transforms visitor emails into personalized ebook experiences through:

1. **Multi-source Enrichment** - Apollo, PDL, Hunter, Tavily, ZoomInfo APIs
2. **Smart Resolution** - Priority-based field merging with fallback logic
3. **LLM Personalization** - Claude Haiku/Opus generates intro hooks + CTAs
4. **Compliance Validation** - Banned terms, claim checking, auto-correction
5. **PDF Generation** - Personalized ebook with signed download URLs
6. **Async Job Queue** - Supabase Edge Functions + polling

**Target SLA**: End-to-end in <60 seconds

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLOUDFLARE (DNS/WAF)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌──────────────────────────────┐    ┌──────────────────────────────────────┐
│     VERCEL (Next.js)         │    │        SUPABASE                      │
│  • Landing page + UTM parse  │───▶│  • Edge Functions (submit/status)   │
│  • Email + consent form      │    │  • PostgreSQL (jobs, outputs, data) │
│  • Loading states            │◀───│  • Storage (PDF bucket)             │
│  • Personalized content      │    │  • Queues (job processing)          │
└──────────────────────────────┘    └──────────────────────────────────────┘
                                                    │
                                                    ▼
                                    ┌──────────────────────────────────────┐
                                    │        RAILWAY (FastAPI)             │
                                    │  • /rad/enrich - orchestration       │
                                    │  • /rad/profile - data retrieval     │
                                    │  • /rad/pdf - ebook generation       │
                                    │                                      │
                                    │  Services:                           │
                                    │  • RADOrchestrator (5 API sources)   │
                                    │  • LLMService (Haiku/Opus)           │
                                    │  • ComplianceService                 │
                                    │  • PDFService                        │
                                    └──────────────────────────────────────┘
                                                    │
                    ┌───────────────┬───────────────┼───────────────┬───────────────┐
                    ▼               ▼               ▼               ▼               ▼
                 Apollo           PDL           Hunter          Tavily         ZoomInfo
                (People)       (People)        (Email)        (Search)       (Company)
```

### Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **CDN/WAF** | Cloudflare | DNS routing, DDoS protection |
| **Frontend** | Next.js 14 + TypeScript | Landing page, forms, polling |
| **Edge Functions** | Supabase Deno | Form submission, job status |
| **Backend** | FastAPI + Python | Enrichment, LLM, PDF generation |
| **Database** | Supabase PostgreSQL | Jobs, outputs, profiles |
| **Storage** | Supabase Storage | PDF file hosting |
| **LLM** | Claude Haiku/Opus | Personalization generation |

---

## Project Structure

```
/
├── frontend/                    # Next.js application
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx      # Root layout
│   │   │   ├── globals.css     # Tailwind styles
│   │   │   └── page.tsx        # Landing page with polling
│   │   └── components/
│   │       ├── EmailConsentForm.tsx
│   │       ├── LoadingSpinner.tsx
│   │       └── PersonalizedContent.tsx
│   └── __tests__/              # Jest tests (22 tests)
│
├── backend/                     # FastAPI application
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── routes/
│       │   └── enrichment.py   # /rad/* endpoints
│       └── services/
│           ├── supabase_client.py    # DB operations
│           ├── rad_orchestrator.py   # Multi-source enrichment
│           ├── enrichment_apis.py    # Apollo, PDL, Hunter, Tavily, ZoomInfo
│           ├── llm_service.py        # Anthropic SDK integration
│           ├── compliance.py         # Content validation
│           └── pdf_service.py        # Ebook generation
│
├── supabase/
│   ├── config.toml             # Supabase configuration
│   ├── migrations/             # Database schema
│   │   ├── 20260127..._create_rad_tables.sql
│   │   └── 20260129..._add_personalization_tables.sql
│   └── functions/              # Edge Functions
│       ├── submit-form/        # POST form handler
│       └── get-job-status/     # GET polling endpoint
│
├── scripts/
│   ├── deploy-frontend-vercel.sh
│   ├── deploy-backend-railway.sh
│   ├── setup-supabase.sh
│   └── deploy-all.sh
│
└── docs/                        # Feature specifications
```

---

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.10+
- Supabase project
- API keys (see Environment Variables)

### Local Development

```bash
# 1. Frontend
cd frontend
npm install
npm run dev              # http://localhost:3000

# 2. Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Run migrations
supabase link --project-ref YOUR_PROJECT_REF
supabase db push
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/rad/enrich` | POST | Start enrichment + personalization |
| `/rad/profile/{email}` | GET | Retrieve finalized profile |
| `/rad/pdf/{email}` | POST | Generate personalized PDF |
| `/rad/health` | GET | Service health check |

**Example: Enrich an email**
```bash
curl -X POST http://localhost:8000/rad/enrich \
  -H "Content-Type: application/json" \
  -d '{"email": "john@acme.com"}'
```

---

## Features

### Enrichment Sources (5 APIs)

| Source | Data Type | Priority |
|--------|-----------|----------|
| **Apollo** | People: name, title, company, LinkedIn | 5 (highest) |
| **ZoomInfo** | Company: size, revenue, industry, tech stack | 4 |
| **PDL** | People: skills, experience, location | 3 |
| **Hunter** | Email: verification, deliverability | 2 |
| **Tavily** | Context: company news, search results | 1 |

### LLM Personalization

- **Model**: Claude Haiku (default) or Opus (high-quality profiles)
- **Output**: JSON with `intro_hook` + `cta`
- **Constraints**: Intro ≤200 chars, CTA ≤150 chars
- **Retry**: Auto-fixes malformed JSON

### Compliance Layer

**Blocked content:**
- Unsubstantiated claims ("guaranteed", "proven", "#1")
- Superlatives without evidence ("best", "fastest")
- Urgency tactics ("act now", "limited time")
- Competitive attacks

**Auto-correction:** Removes terms or falls back to safe copy.

### PDF Generation

- HTML template with personalization slots
- Uses WeasyPrint or ReportLab
- Stored in Supabase Storage
- Signed URLs with 7-day expiry

---

## Environment Variables

### Vercel (Frontend)
```bash
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE=eyJ...          # Server-side only
```

### Railway (Backend)
```bash
# Required
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...                   # service_role key
ANTHROPIC_API_KEY=sk-ant-...

# Enrichment APIs (optional - uses mocks if missing)
APOLLO_API_KEY=...
PDL_API_KEY=...
HUNTER_API_KEY=...
TAVILY_API_KEY=...
ZOOMINFO_API_KEY=...
```

### Supabase (Edge Functions)
```bash
SUPABASE_URL           # Auto-set
SUPABASE_SERVICE_ROLE_KEY  # Auto-set
RAILWAY_BACKEND_URL=https://your-backend.railway.app
```

---

## Database Schema

### Core Tables

```sql
-- Job tracking
personalization_jobs (id, email, domain, cta, status, created_at, completed_at)

-- LLM outputs
personalization_outputs (job_id, intro_hook, cta, model_used, tokens_used, compliance_passed)

-- PDF delivery
pdf_deliveries (job_id, pdf_url, storage_path, delivery_status)

-- Enrichment data
raw_data (email, source, payload, fetched_at)
staging_normalized (email, normalized_fields, status)
finalize_data (email, normalized_data, personalization_intro, personalization_cta)
```

Run migrations:
```bash
supabase db push
```

---

## Deployment

### Automated Deployment

```bash
# Deploy everything
./scripts/deploy-all.sh

# Or individually
./scripts/setup-supabase.sh
./scripts/deploy-backend-railway.sh
./scripts/deploy-frontend-vercel.sh
```

### Manual Deployment

**Vercel:**
```bash
cd frontend
vercel --prod
```

**Railway:**
```bash
cd backend
railway up
```

---

## Testing

### Frontend (Jest)
```bash
cd frontend
npm test              # 22 tests
npm run test:coverage
```

### Backend (Pytest)
```bash
cd backend
pytest                # All tests
pytest --cov=app      # With coverage
```

---

## Roadmap

### Phase 1 - Alpha (Complete)
- ✅ Next.js frontend with email form
- ✅ FastAPI backend with /rad/* endpoints
- ✅ Multi-source enrichment (5 APIs)
- ✅ Real Anthropic SDK integration
- ✅ Compliance validation layer
- ✅ PDF generation service
- ✅ Supabase Edge Functions
- ✅ Deployment scripts

### Phase 2 - Beta
- [ ] Supabase Queues for durable jobs
- [ ] Batch enrichment endpoint
- [ ] Rate limiting + circuit breakers
- [ ] OpenTelemetry instrumentation
- [ ] Marketing automation webhook

### Phase 3 - Production
- [ ] A/B testing for LLM prompts
- [ ] Multi-language support
- [ ] Advanced PDF templates
- [ ] Chaos testing suite
- [ ] Cost optimization dashboard

---

## Security

Per [CLAUDE.md](CLAUDE.md):

- ✅ No secrets in code
- ✅ No `.env` files committed
- ✅ Input validation (Pydantic + email regex)
- ✅ Parameterized queries (Supabase SDK)
- ✅ Compliance checks on LLM output

---

## Contributing

1. Follow [CLAUDE.md](CLAUDE.md) rules
2. Write tests first (TDD)
3. Keep code simple and focused
4. Document new features in README

---

## License

ISC
