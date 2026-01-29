"""
Enrichment API integrations for RAD pipeline.
Real implementations for: Apollo, PDL, Hunter, Tavily, ZoomInfo.
All API keys loaded from environment variables.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
from abc import ABC, abstractmethod

from app.config import settings

logger = logging.getLogger(__name__)

# Default timeout for all API calls (seconds)
DEFAULT_TIMEOUT = 30.0


class EnrichmentAPIError(Exception):
    """Base exception for enrichment API errors."""

    def __init__(self, source: str, message: str, status_code: Optional[int] = None):
        self.source = source
        self.message = message
        self.status_code = status_code
        super().__init__(f"{source}: {message}")


class BaseEnrichmentAPI(ABC):
    """Base class for enrichment API integrations."""

    source_name: str = "unknown"

    @abstractmethod
    async def enrich(self, email: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """Enrich data for given email/domain."""
        pass

    def _handle_error(self, response: httpx.Response) -> None:
        """Handle API error response."""
        if response.status_code >= 400:
            raise EnrichmentAPIError(
                source=self.source_name,
                message=f"API returned {response.status_code}: {response.text[:200]}",
                status_code=response.status_code
            )


class ApolloAPI(BaseEnrichmentAPI):
    """
    Apollo.io People Enrichment API.
    Docs: https://apolloio.github.io/apollo-api-docs/
    """

    source_name = "apollo"
    base_url = "https://api.apollo.io/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.APOLLO_API_KEY
        if not self.api_key:
            logger.warning("Apollo API key not configured")

    async def enrich(self, email: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Enrich person data from Apollo.

        Args:
            email: Email address to look up
            domain: Company domain (optional)

        Returns:
            Enriched person data
        """
        if not self.api_key:
            return self._mock_response(email, domain)

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/people/match",
                    headers={"Content-Type": "application/json"},
                    json={
                        "api_key": self.api_key,
                        "email": email,
                        "reveal_personal_emails": False
                    }
                )

                self._handle_error(response)
                data = response.json()

                person = data.get("person", {})
                return {
                    "email": email,
                    "first_name": person.get("first_name"),
                    "last_name": person.get("last_name"),
                    "title": person.get("title"),
                    "linkedin_url": person.get("linkedin_url"),
                    "company_name": person.get("organization", {}).get("name"),
                    "domain": person.get("organization", {}).get("primary_domain"),
                    "industry": person.get("organization", {}).get("industry"),
                    "company_size": self._map_employee_count(
                        person.get("organization", {}).get("estimated_num_employees")
                    ),
                    "city": person.get("city"),
                    "state": person.get("state"),
                    "country": person.get("country"),
                    "seniority": person.get("seniority"),
                    "departments": person.get("departments", []),
                    "fetched_at": datetime.utcnow().isoformat()
                }

        except httpx.TimeoutException:
            logger.error(f"Apollo API timeout for {email}")
            raise EnrichmentAPIError(self.source_name, "Request timeout")
        except httpx.RequestError as e:
            logger.error(f"Apollo API request error for {email}: {e}")
            raise EnrichmentAPIError(self.source_name, str(e))

    def _mock_response(self, email: str, domain: Optional[str]) -> Dict[str, Any]:
        """Return mock data when API key not configured."""
        logger.info(f"Apollo: Using mock data for {email} (no API key)")
        username = email.split("@")[0]
        domain = domain or email.split("@")[1]
        return {
            "email": email,
            "first_name": username.split(".")[0].title() if "." in username else username.title(),
            "last_name": username.split(".")[-1].title() if "." in username else "User",
            "title": "Professional",
            "linkedin_url": f"https://linkedin.com/in/{username}",
            "company_name": f"Company at {domain}",
            "domain": domain,
            "industry": "Technology",
            "company_size": "50-200",
            "country": "US",
            "fetched_at": datetime.utcnow().isoformat(),
            "_mock": True
        }

    def _map_employee_count(self, count: Optional[int]) -> str:
        """Map employee count to size range."""
        if not count:
            return "Unknown"
        if count < 10:
            return "1-10"
        if count < 50:
            return "11-50"
        if count < 200:
            return "50-200"
        if count < 500:
            return "200-500"
        if count < 1000:
            return "500-1000"
        return "1000+"


class PDLAPI(BaseEnrichmentAPI):
    """
    People Data Labs API.
    Docs: https://docs.peopledatalabs.com/
    """

    source_name = "pdl"
    base_url = "https://api.peopledatalabs.com/v5"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.PDL_API_KEY
        if not self.api_key:
            logger.warning("PDL API key not configured")

    async def enrich(self, email: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Enrich person data from People Data Labs.

        Args:
            email: Email address to look up
            domain: Company domain (optional)

        Returns:
            Enriched person data
        """
        if not self.api_key:
            return self._mock_response(email, domain)

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.get(
                    f"{self.base_url}/person/enrich",
                    headers={"X-Api-Key": self.api_key},
                    params={"email": email}
                )

                self._handle_error(response)
                data = response.json()

                return {
                    "email": email,
                    "first_name": data.get("first_name"),
                    "last_name": data.get("last_name"),
                    "full_name": data.get("full_name"),
                    "linkedin_url": data.get("linkedin_url"),
                    "job_title": data.get("job_title"),
                    "job_company_name": data.get("job_company_name"),
                    "job_company_industry": data.get("job_company_industry"),
                    "job_company_size": data.get("job_company_size"),
                    "location_country": data.get("location_country"),
                    "location_region": data.get("location_region"),
                    "location_locality": data.get("location_locality"),
                    "skills": data.get("skills", [])[:10],  # Limit skills
                    "interests": data.get("interests", [])[:10],
                    "experience": self._extract_recent_experience(data.get("experience", [])),
                    "fetched_at": datetime.utcnow().isoformat()
                }

        except httpx.TimeoutException:
            logger.error(f"PDL API timeout for {email}")
            raise EnrichmentAPIError(self.source_name, "Request timeout")
        except httpx.RequestError as e:
            logger.error(f"PDL API request error for {email}: {e}")
            raise EnrichmentAPIError(self.source_name, str(e))

    def _mock_response(self, email: str, domain: Optional[str]) -> Dict[str, Any]:
        """Return mock data when API key not configured."""
        logger.info(f"PDL: Using mock data for {email} (no API key)")
        return {
            "email": email,
            "location_country": "United States",
            "job_company_industry": "Software",
            "job_company_size": "51-200",
            "skills": ["Sales", "Marketing", "Strategy"],
            "fetched_at": datetime.utcnow().isoformat(),
            "_mock": True
        }

    def _extract_recent_experience(self, experience: List[Dict]) -> List[Dict]:
        """Extract recent work experience (last 3 positions)."""
        return experience[:3] if experience else []


class HunterAPI(BaseEnrichmentAPI):
    """
    Hunter.io Email Verification API.
    Docs: https://hunter.io/api-documentation/v2
    """

    source_name = "hunter"
    base_url = "https://api.hunter.io/v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.HUNTER_API_KEY
        if not self.api_key:
            logger.warning("Hunter API key not configured")

    async def enrich(self, email: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Verify email and get additional data from Hunter.

        Args:
            email: Email address to verify
            domain: Company domain (optional)

        Returns:
            Email verification data
        """
        if not self.api_key:
            return self._mock_response(email, domain)

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.get(
                    f"{self.base_url}/email-verifier",
                    params={
                        "email": email,
                        "api_key": self.api_key
                    }
                )

                self._handle_error(response)
                data = response.json().get("data", {})

                return {
                    "email": email,
                    "status": data.get("status"),  # valid, invalid, accept_all, webmail, disposable, unknown
                    "result": data.get("result"),  # deliverable, undeliverable, risky, unknown
                    "score": data.get("score"),  # 0-100
                    "regexp": data.get("regexp"),
                    "gibberish": data.get("gibberish"),
                    "disposable": data.get("disposable"),
                    "webmail": data.get("webmail"),
                    "mx_records": data.get("mx_records"),
                    "smtp_server": data.get("smtp_server"),
                    "smtp_check": data.get("smtp_check"),
                    "accept_all": data.get("accept_all"),
                    "block": data.get("block"),
                    "fetched_at": datetime.utcnow().isoformat()
                }

        except httpx.TimeoutException:
            logger.error(f"Hunter API timeout for {email}")
            raise EnrichmentAPIError(self.source_name, "Request timeout")
        except httpx.RequestError as e:
            logger.error(f"Hunter API request error for {email}: {e}")
            raise EnrichmentAPIError(self.source_name, str(e))

    def _mock_response(self, email: str, domain: Optional[str]) -> Dict[str, Any]:
        """Return mock data when API key not configured."""
        logger.info(f"Hunter: Using mock data for {email} (no API key)")
        return {
            "email": email,
            "status": "valid",
            "result": "deliverable",
            "score": 90,
            "disposable": False,
            "webmail": "@gmail" in email or "@yahoo" in email or "@hotmail" in email,
            "fetched_at": datetime.utcnow().isoformat(),
            "_mock": True
        }


class TavilyAPI(BaseEnrichmentAPI):
    """
    Tavily Search API for company news and context.
    Docs: https://docs.tavily.com/
    """

    source_name = "tavily"
    base_url = "https://api.tavily.com"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.TAVILY_API_KEY
        if not self.api_key:
            logger.warning("Tavily API key not configured")

    async def enrich(self, email: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for company news and context using Tavily.

        Args:
            email: Email address (used to extract domain if not provided)
            domain: Company domain

        Returns:
            Search results and company context
        """
        if not self.api_key:
            return self._mock_response(email, domain)

        domain = domain or email.split("@")[1]

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    headers={"Content-Type": "application/json"},
                    json={
                        "api_key": self.api_key,
                        "query": f"{domain} company news funding",
                        "search_depth": "basic",
                        "include_answer": True,
                        "max_results": 5
                    }
                )

                self._handle_error(response)
                data = response.json()

                return {
                    "domain": domain,
                    "answer": data.get("answer"),
                    "results": [
                        {
                            "title": r.get("title"),
                            "url": r.get("url"),
                            "content": r.get("content", "")[:500],
                            "score": r.get("score")
                        }
                        for r in data.get("results", [])[:5]
                    ],
                    "result_count": len(data.get("results", [])),
                    "fetched_at": datetime.utcnow().isoformat()
                }

        except httpx.TimeoutException:
            logger.error(f"Tavily API timeout for {domain}")
            raise EnrichmentAPIError(self.source_name, "Request timeout")
        except httpx.RequestError as e:
            logger.error(f"Tavily API request error for {domain}: {e}")
            raise EnrichmentAPIError(self.source_name, str(e))

    def _mock_response(self, email: str, domain: Optional[str]) -> Dict[str, Any]:
        """Return mock data when API key not configured."""
        domain = domain or email.split("@")[1]
        logger.info(f"Tavily: Using mock data for {domain} (no API key)")
        return {
            "domain": domain,
            "answer": f"Company at {domain} is a technology company.",
            "results": [],
            "result_count": 0,
            "fetched_at": datetime.utcnow().isoformat(),
            "_mock": True
        }


class ZoomInfoAPI(BaseEnrichmentAPI):
    """
    ZoomInfo Company Enrichment API.
    Docs: https://api-docs.zoominfo.com/
    """

    source_name = "zoominfo"
    base_url = "https://api.zoominfo.com"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ZOOMINFO_API_KEY
        if not self.api_key:
            logger.warning("ZoomInfo API key not configured")

    async def enrich(self, email: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Enrich company data from ZoomInfo.

        Args:
            email: Email address (used to extract domain if not provided)
            domain: Company domain

        Returns:
            Company data from ZoomInfo
        """
        if not self.api_key:
            return self._mock_response(email, domain)

        domain = domain or email.split("@")[1]

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                # ZoomInfo requires OAuth token, simplified here
                response = await client.post(
                    f"{self.base_url}/search/company",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "matchCompanyInput": [{"companyWebsite": domain}],
                        "outputFields": [
                            "id", "name", "website", "industry", "subIndustry",
                            "employeeCount", "revenue", "city", "state", "country",
                            "description", "foundedYear", "techStackIds"
                        ]
                    }
                )

                self._handle_error(response)
                data = response.json()
                company = data.get("data", [{}])[0] if data.get("data") else {}

                return {
                    "domain": domain,
                    "company_name": company.get("name"),
                    "website": company.get("website"),
                    "industry": company.get("industry"),
                    "sub_industry": company.get("subIndustry"),
                    "employee_count": company.get("employeeCount"),
                    "revenue": company.get("revenue"),
                    "city": company.get("city"),
                    "state": company.get("state"),
                    "country": company.get("country"),
                    "description": company.get("description"),
                    "founded_year": company.get("foundedYear"),
                    "tech_stack": company.get("techStackIds", []),
                    "fetched_at": datetime.utcnow().isoformat()
                }

        except httpx.TimeoutException:
            logger.error(f"ZoomInfo API timeout for {domain}")
            raise EnrichmentAPIError(self.source_name, "Request timeout")
        except httpx.RequestError as e:
            logger.error(f"ZoomInfo API request error for {domain}: {e}")
            raise EnrichmentAPIError(self.source_name, str(e))

    def _mock_response(self, email: str, domain: Optional[str]) -> Dict[str, Any]:
        """Return mock data when API key not configured."""
        domain = domain or email.split("@")[1]
        logger.info(f"ZoomInfo: Using mock data for {domain} (no API key)")
        return {
            "domain": domain,
            "company_name": f"Company at {domain}",
            "industry": "Technology",
            "employee_count": 100,
            "country": "United States",
            "fetched_at": datetime.utcnow().isoformat(),
            "_mock": True
        }


# Convenience factory function
def get_enrichment_apis() -> Dict[str, BaseEnrichmentAPI]:
    """
    Get all configured enrichment API clients.

    Returns:
        Dict mapping source name to API client
    """
    return {
        "apollo": ApolloAPI(),
        "pdl": PDLAPI(),
        "hunter": HunterAPI(),
        "tavily": TavilyAPI(),
        "zoominfo": ZoomInfoAPI()
    }
