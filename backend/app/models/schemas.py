"""
Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, EmailStr, Field


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class EnrichmentRequest(BaseModel):
    """
    POST /rad/enrich request body.
    Includes email, optional domain, and user-provided context for personalization.
    """
    email: EmailStr = Field(..., description="Email address to enrich")
    domain: Optional[str] = Field(None, description="Company domain (optional; derived from email if absent)")
    # User-provided info (more reliable than API enrichment)
    firstName: Optional[str] = Field(None, description="User's first name")
    lastName: Optional[str] = Field(None, description="User's last name")
    company: Optional[str] = Field(None, description="User's company name")
    # User-provided context for better personalization
    goal: Optional[str] = Field(None, description="Buying stage (awareness, consideration, decision, implementation)")
    persona: Optional[str] = Field(None, description="User's role (c_suite, vp_director, it_infrastructure, engineering, data_ai, security, procurement)")
    industry: Optional[str] = Field(None, description="User's industry (technology, financial_services, healthcare, retail_ecommerce, manufacturing, etc.)")
    cta: Optional[str] = Field(None, description="Campaign CTA context")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "john@acme.com",
                "firstName": "John",
                "lastName": "Smith",
                "company": "Acme Corp",
                "domain": "acme.com",
                "goal": "consideration",
                "persona": "c_suite",
                "industry": "technology"
            }
        }


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class RawDataRecord(BaseModel):
    """
    Raw data pulled from external APIs (Apollo, PDL, GNews, etc).
    In alpha, this is a placeholder; real data is mocked.
    """
    source: str = Field(..., description="API source (apollo, pdl, hunter, gnews)")
    data: Dict[str, Any] = Field(default_factory=dict, description="Raw response data")
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class NormalizedProfile(BaseModel):
    """
    Normalized profile after RAD resolution logic.
    These fields are written to finalize_data table.
    """
    email: str
    domain: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    country: Optional[str] = None
    linkedin_url: Optional[str] = None
    data_quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class PersonalizationContent(BaseModel):
    """
    LLM-generated personalization content.
    These will be used in the ebook rendering.
    """
    intro_hook: str = Field(..., description="1-2 sentence personalized introduction")
    cta: str = Field(..., description="Call-to-action tailored to buyer stage")


class ProfileResponse(BaseModel):
    """
    GET /rad/profile/{email} response.
    Returns the normalized profile + personalization content from finalize_data.
    """
    email: str
    normalized_profile: NormalizedProfile
    personalization: Optional[PersonalizationContent] = None
    last_updated: datetime


class EnrichmentResponse(BaseModel):
    """
    POST /rad/enrich response.
    Returns job ID and status for async tracking.
    """
    job_id: str = Field(..., description="Unique enrichment job ID")
    email: str
    status: str = Field(default="queued", description="Job status: queued, processing, completed, failed")
    created_at: datetime


# ============================================================================
# ERROR RESPONSES
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


# ============================================================================
# INTERNAL SCHEMAS (DB models)
# ============================================================================

class FinalizationData(BaseModel):
    """
    Internal representation of finalize_data table row.
    """
    email: str
    normalized_data: Dict[str, Any]
    personalization_intro: Optional[str] = None
    personalization_cta: Optional[str] = None
    resolved_at: datetime
    data_sources: list = Field(default_factory=list, description="List of APIs that contributed")
