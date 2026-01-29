"""
Tests for Supabase client data access layer.
Uses SupabaseClient in mock mode (in-memory storage).
"""

import pytest
from datetime import datetime

from app.services.supabase_client import SupabaseClient


class TestSupabaseClient:
    """Tests for SupabaseClient wrapper."""

    @pytest.fixture
    def supabase_client(self, mock_supabase):
        """Fixture: Supabase client in mock mode."""
        return mock_supabase

    def test_store_raw_data(self, supabase_client):
        """store_raw_data: Should insert record into raw_data table."""
        result = supabase_client.store_raw_data(
            email="john@acme.com",
            source="apollo",
            payload={"name": "John Doe", "title": "VP Sales"}
        )

        assert result["email"] == "john@acme.com"
        assert result["source"] == "apollo"
        assert result["payload"]["name"] == "John Doe"
        assert "id" in result
        assert "fetched_at" in result

    def test_get_raw_data_for_email(self, supabase_client):
        """get_raw_data_for_email: Should retrieve all raw_data records."""
        # First store some data
        supabase_client.store_raw_data(
            email="john@acme.com",
            source="apollo",
            payload={"name": "John"}
        )
        supabase_client.store_raw_data(
            email="john@acme.com",
            source="pdl",
            payload={"company": "Acme"}
        )

        result = supabase_client.get_raw_data_for_email("john@acme.com")

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(r["email"] == "john@acme.com" for r in result)

    def test_create_staging_record(self, supabase_client):
        """create_staging_record: Should create staging_normalized record."""
        normalized = {
            "first_name": "John",
            "last_name": "Doe",
            "company": "Acme"
        }

        result = supabase_client.create_staging_record(
            email="john@acme.com",
            normalized_fields=normalized,
            status="resolving"
        )

        assert result["email"] == "john@acme.com"
        assert result["status"] == "resolving"
        assert result["normalized_fields"]["first_name"] == "John"

    def test_update_staging_record(self, supabase_client):
        """update_staging_record: Should update existing staging record."""
        # First create a record
        supabase_client.create_staging_record(
            email="john@acme.com",
            normalized_fields={"first_name": "John"},
            status="resolving"
        )

        # Then update it
        result = supabase_client.update_staging_record(
            email="john@acme.com",
            normalized_fields={"first_name": "John", "title": "VP Sales"},
            status="ready"
        )

        assert result["status"] == "ready"

    def test_write_finalize_data(self, supabase_client):
        """write_finalize_data: Should write final profile to finalize_data."""
        normalized = {
            "first_name": "John",
            "last_name": "Doe",
            "company": "Acme"
        }

        result = supabase_client.write_finalize_data(
            email="john@acme.com",
            normalized_data=normalized,
            intro="Hi John...",
            cta="Let's connect!",
            data_sources=["apollo", "pdl"]
        )

        assert result["email"] == "john@acme.com"
        assert result["normalized_data"]["first_name"] == "John"
        assert result["personalization_intro"] == "Hi John..."
        assert result["personalization_cta"] == "Let's connect!"

    def test_get_finalize_data_found(self, supabase_client):
        """get_finalize_data: Should retrieve finalized profile."""
        # First write some data
        supabase_client.write_finalize_data(
            email="john@acme.com",
            normalized_data={"first_name": "John"},
            intro="Hello!",
            cta="Connect now"
        )

        result = supabase_client.get_finalize_data("john@acme.com")

        assert result is not None
        assert result["email"] == "john@acme.com"
        assert result["personalization_intro"] == "Hello!"

    def test_get_finalize_data_not_found(self, supabase_client):
        """get_finalize_data: Should return None if not found."""
        result = supabase_client.get_finalize_data("nonexistent@example.com")
        assert result is None

    def test_health_check(self, supabase_client):
        """health_check: Should return True in mock mode."""
        result = supabase_client.health_check()
        assert result is True


class TestRawDataOperations:
    """Additional tests for raw data operations."""

    @pytest.fixture
    def supabase_client(self, mock_supabase):
        return mock_supabase

    def test_store_multiple_sources(self, supabase_client):
        """Should store data from multiple sources for same email."""
        supabase_client.store_raw_data("user@test.com", "apollo", {"data": "a"})
        supabase_client.store_raw_data("user@test.com", "pdl", {"data": "b"})
        supabase_client.store_raw_data("user@test.com", "hunter", {"data": "c"})

        records = supabase_client.get_raw_data_for_email("user@test.com")

        assert len(records) == 3
        sources = [r["source"] for r in records]
        assert "apollo" in sources
        assert "pdl" in sources
        assert "hunter" in sources


class TestFinalizationOperations:
    """Additional tests for finalization operations."""

    @pytest.fixture
    def supabase_client(self, mock_supabase):
        return mock_supabase

    def test_write_finalize_requires_normalized_data(self, supabase_client):
        """write_finalize_data: normalized_data is required."""
        result = supabase_client.write_finalize_data(
            email="test@test.com",
            normalized_data={"first_name": "Test"},
            intro=None,
            cta=None
        )

        assert result["email"] == "test@test.com"
        assert result["normalized_data"]["first_name"] == "Test"

    def test_finalize_personalization_optional(self, supabase_client):
        """write_finalize_data: intro and cta are optional."""
        result = supabase_client.write_finalize_data(
            email="test@test.com",
            normalized_data={"name": "Test User"}
        )

        assert result["email"] == "test@test.com"
        assert result["personalization_intro"] is None
        assert result["personalization_cta"] is None

    def test_get_finalize_latest_record(self, supabase_client):
        """get_finalize_data: Should return most recent record."""
        # Write two records
        supabase_client.write_finalize_data(
            email="user@test.com",
            normalized_data={"version": "old"}
        )
        supabase_client.write_finalize_data(
            email="user@test.com",
            normalized_data={"version": "new"}
        )

        result = supabase_client.get_finalize_data("user@test.com")

        # Should get the latest one
        assert result["normalized_data"]["version"] == "new"
