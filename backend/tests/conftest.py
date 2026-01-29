"""
Pytest configuration and fixtures.
Provides mocked Supabase client and FastAPI test client.
"""

import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

# Set mock mode BEFORE importing services
os.environ["MOCK_SUPABASE"] = "true"
os.environ["SUPABASE_URL"] = "http://localhost:54321"
os.environ["SUPABASE_KEY"] = "mock-test-key"

# Import app and services
from app.main import app
from app.services.supabase_client import SupabaseClient, get_supabase_client
from app.services.rad_orchestrator import RADOrchestrator
from app.services.llm_service import LLMService


@pytest.fixture
def mock_supabase():
    """
    Fixture: Supabase client in mock mode.
    Uses in-memory storage; no real Supabase connection.
    """
    # Create a fresh client instance (will use mock mode due to env vars)
    client = SupabaseClient()

    # Clear any existing mock data
    client._mock_raw_data = []
    client._mock_staging = []
    client._mock_finalize = []
    client._mock_jobs = []
    client._mock_outputs = []
    client._mock_pdfs = []

    return client


@pytest.fixture
def test_client(mock_supabase):
    """
    Fixture: FastAPI TestClient with mocked Supabase.
    """
    # Patch the get_supabase_client dependency
    def mock_get_supabase():
        return mock_supabase

    app.dependency_overrides[get_supabase_client] = mock_get_supabase

    client = TestClient(app)

    yield client

    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
async def mock_rad_orchestrator(mock_supabase):
    """Fixture: RADOrchestrator with mocked Supabase."""
    return RADOrchestrator(mock_supabase)


@pytest.fixture
def mock_llm_service():
    """Fixture: LLMService (mocked, no API calls)."""
    return LLMService(api_key="mock-key")
