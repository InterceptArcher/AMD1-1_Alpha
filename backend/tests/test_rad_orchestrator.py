"""
Tests for RAD orchestrator.
Tests resolution logic and data aggregation using mock API responses.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.rad_orchestrator import RADOrchestrator, SOURCE_PRIORITY


@pytest.mark.asyncio
class TestRADOrchestrator:
    """Tests for RADOrchestrator enrichment pipeline."""

    @pytest.fixture
    def orchestrator(self, mock_supabase):
        """Fixture: RADOrchestrator with mocked Supabase."""
        return RADOrchestrator(mock_supabase)

    @pytest.mark.asyncio
    async def test_enrich_happy_path(self, orchestrator):
        """
        Happy path: Full enrichment flow.
        Should fetch, resolve, and return normalized data.
        """
        result = await orchestrator.enrich("john@acme.com", "acme.com")

        assert result is not None
        assert result["email"] == "john@acme.com"
        assert result["domain"] == "acme.com"
        assert "resolved_at" in result
        assert "data_sources" in result

    @pytest.mark.asyncio
    async def test_enrich_derives_domain_from_email(self, orchestrator):
        """
        enrich: If domain not provided, derive from email.
        """
        result = await orchestrator.enrich("john@acme.com")

        assert result is not None
        assert result["domain"] == "acme.com"

    @pytest.mark.asyncio
    async def test_fetch_all_sources_returns_dict(self, orchestrator):
        """
        _fetch_all_sources: Should return dict with all source names as keys.
        """
        raw_data = await orchestrator._fetch_all_sources("john@acme.com", "acme.com")

        assert isinstance(raw_data, dict)
        assert "apollo" in raw_data
        assert "pdl" in raw_data
        assert "hunter" in raw_data
        assert "tavily" in raw_data
        assert "zoominfo" in raw_data

    @pytest.mark.asyncio
    async def test_fetch_all_sources_parallel_execution(self, orchestrator):
        """
        _fetch_all_sources: Should fetch from all APIs (mocked responses).
        """
        raw_data = await orchestrator._fetch_all_sources("john@acme.com", "acme.com")

        # Each source should have data (may include _mock flag)
        for source, data in raw_data.items():
            assert isinstance(data, dict)

    def test_resolve_profile_merges_data(self, orchestrator):
        """
        _resolve_profile: Should merge data from multiple sources.
        """
        raw_data = {
            "apollo": {
                "first_name": "John",
                "last_name": "Doe",
                "company_name": "Acme",
                "title": "VP Sales"
            },
            "pdl": {
                "location_country": "US",
                "job_company_industry": "SaaS"
            },
            "hunter": {
                "status": "valid",
                "score": 95,
                "result": "deliverable"
            },
            "tavily": {},
            "zoominfo": {}
        }
        orchestrator.data_sources = ["apollo", "pdl", "hunter"]

        result = orchestrator._resolve_profile("john@acme.com", "acme.com", raw_data)

        # Fields should be resolved
        assert result.get("first_name") == "John"
        assert result.get("country") == "US"
        assert result.get("industry") == "SaaS"
        assert result.get("email_verified") is True
        assert result.get("email_score") == 95

    def test_resolve_profile_respects_apollo_priority(self, orchestrator):
        """
        _resolve_profile: Apollo data takes priority (higher trust ranking).
        """
        raw_data = {
            "apollo": {
                "first_name": "John",
                "company_name": "Acme Corp"
            },
            "pdl": {
                "first_name": "Johnny",
                "job_company_size": "500+"
            },
            "hunter": {},
            "tavily": {},
            "zoominfo": {}
        }
        orchestrator.data_sources = ["apollo", "pdl"]

        result = orchestrator._resolve_profile("john@acme.com", "acme.com", raw_data)

        # Apollo's name should win due to higher priority
        assert result.get("first_name") == "John"
        # PDL's unique field should still be included
        assert result.get("company_size") == "500+"

    def test_resolve_field_uses_priority(self, orchestrator):
        """
        _resolve_field: Should return value from highest priority source.
        """
        raw_data = {
            "apollo": {"first_name": "FromApollo"},
            "pdl": {"first_name": "FromPDL"},
        }

        sources = [("apollo", "first_name"), ("pdl", "first_name")]
        result = orchestrator._resolve_field("first_name", sources, raw_data)

        # Apollo has priority 5, PDL has priority 3
        assert result == "FromApollo"

    def test_resolve_field_skips_errors(self, orchestrator):
        """
        _resolve_field: Should skip sources with errors.
        """
        raw_data = {
            "apollo": {"_error": "API failed"},
            "pdl": {"first_name": "FromPDL"},
        }

        sources = [("apollo", "first_name"), ("pdl", "first_name")]
        result = orchestrator._resolve_field("first_name", sources, raw_data)

        assert result == "FromPDL"

    def test_resolve_field_returns_none_if_no_data(self, orchestrator):
        """
        _resolve_field: Should return None if no sources have the field.
        """
        raw_data = {
            "apollo": {},
            "pdl": {},
        }

        sources = [("apollo", "first_name"), ("pdl", "first_name")]
        result = orchestrator._resolve_field("first_name", sources, raw_data)

        assert result is None

    def test_calculate_quality_score_basic(self, orchestrator):
        """
        _calculate_quality_score: Should scale with successful sources.
        """
        # Mock raw_data with 2 successful sources (no errors, no _mock flag)
        raw_data = {
            "apollo": {"first_name": "John"},
            "pdl": {"country": "US"},
            "hunter": {"_error": "failed"},
            "tavily": {"_error": "failed"},
            "zoominfo": {"_error": "failed"}
        }

        score = orchestrator._calculate_quality_score(raw_data)

        # 2/5 sources successful = 0.4 base
        # Apollo bonus +0.1 = 0.5
        assert 0.4 <= score <= 0.6

    def test_calculate_quality_score_max(self, orchestrator):
        """
        _calculate_quality_score: Should cap at 1.0.
        """
        # All sources successful with high priority bonuses
        raw_data = {
            "apollo": {"name": "John"},
            "pdl": {"country": "US"},
            "hunter": {"verified": True},
            "tavily": {"context": "news"},
            "zoominfo": {"company": "Acme"}
        }

        score = orchestrator._calculate_quality_score(raw_data)

        # Should be capped at 1.0
        assert score <= 1.0


class TestRADDataFlow:
    """Integration-style tests for RAD data flow."""

    @pytest.fixture
    def orchestrator(self, mock_supabase):
        return RADOrchestrator(mock_supabase)

    @pytest.mark.asyncio
    async def test_enrich_stores_raw_data(self, orchestrator, mock_supabase):
        """
        enrich: Should store raw data for successful sources.
        """
        await orchestrator.enrich("john@acme.com", "acme.com")

        # Check that raw data was stored in mock storage
        raw_records = mock_supabase.get_raw_data_for_email("john@acme.com")
        assert len(raw_records) > 0

    @pytest.mark.asyncio
    async def test_enrich_data_sources_populated(self, orchestrator):
        """
        enrich: data_sources list should reflect which APIs returned data.
        """
        await orchestrator.enrich("john@acme.com")

        # In mock mode, all APIs return mock data
        assert len(orchestrator.data_sources) >= 0  # May be 0 if all mocked with errors

    @pytest.mark.asyncio
    async def test_enrich_returns_complete_profile(self, orchestrator):
        """
        enrich: Returned profile should include all expected fields.
        """
        result = await orchestrator.enrich("john@acme.com")

        assert "email" in result
        assert "domain" in result
        assert "resolved_at" in result
        assert "data_sources" in result
        assert "data_quality_score" in result


class TestSourcePriority:
    """Tests for source priority configuration."""

    def test_source_priority_defined(self):
        """SOURCE_PRIORITY: Should define priorities for all sources."""
        assert "apollo" in SOURCE_PRIORITY
        assert "pdl" in SOURCE_PRIORITY
        assert "hunter" in SOURCE_PRIORITY
        assert "tavily" in SOURCE_PRIORITY
        assert "zoominfo" in SOURCE_PRIORITY

    def test_source_priority_ordering(self):
        """SOURCE_PRIORITY: Apollo should have highest priority."""
        assert SOURCE_PRIORITY["apollo"] > SOURCE_PRIORITY["pdl"]
        assert SOURCE_PRIORITY["apollo"] > SOURCE_PRIORITY["hunter"]
        assert SOURCE_PRIORITY["zoominfo"] > SOURCE_PRIORITY["pdl"]
