"""
LLM Service: Generates personalization content (intro hook + CTA).
Uses Claude Haiku for fast inference (target <30s latency).
Implements structured output, validation, and retry logic.
"""

import logging
import json
import time
import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

import anthropic
from anthropic import APIError, APITimeoutError, RateLimitError

from app.config import settings

logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1.0
DEFAULT_MODEL = "claude-3-5-haiku-20241022"
OPUS_MODEL = "claude-opus-4-5-20251101"

# Output constraints
MAX_INTRO_LENGTH = 200  # characters
MAX_CTA_LENGTH = 150  # characters


@dataclass
class PersonalizationResult:
    """Result from personalization generation."""
    intro_hook: str
    cta: str
    model_used: str
    tokens_used: int
    latency_ms: int
    raw_response: Dict[str, Any]


class LLMService:
    """
    Generates personalized intro hook and CTA using Claude.
    - Uses Haiku for speed (default)
    - Falls back to Opus for complex cases
    - Implements structured output with JSON validation
    - Retry logic for transient failures
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LLM service.

        Args:
            api_key: Anthropic API key. If None, use environment variable.
        """
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.client = None

        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)
            logger.info("LLM service initialized with Anthropic client")
        else:
            logger.warning("LLM service initialized without API key (mock mode)")

    async def generate_personalization(
        self,
        normalized_profile: Dict[str, Any],
        use_opus: bool = False
    ) -> Dict[str, str]:
        """
        Generate intro hook and CTA from normalized profile.

        Args:
            normalized_profile: Normalized enrichment data
            use_opus: Whether to use Opus model for richer output

        Returns:
            Dict with 'intro_hook', 'cta', and metadata
        """
        if not self.client:
            return self._mock_response(normalized_profile)

        start_time = time.time()
        model = OPUS_MODEL if use_opus else DEFAULT_MODEL

        # Build the prompt
        prompt = self._build_prompt(normalized_profile)

        # Try with retries
        for attempt in range(MAX_RETRIES):
            try:
                response = self.client.messages.create(
                    model=model,
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}],
                    system=self._get_system_prompt()
                )

                # Parse response
                content = response.content[0].text
                parsed = self._parse_response(content)

                if parsed:
                    latency_ms = int((time.time() - start_time) * 1000)

                    result = {
                        "intro_hook": parsed["intro_hook"],
                        "cta": parsed["cta"],
                        "model_used": model,
                        "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                        "latency_ms": latency_ms,
                        "raw_response": {"content": content}
                    }

                    logger.info(
                        f"Generated personalization: model={model}, "
                        f"tokens={result['tokens_used']}, latency={latency_ms}ms"
                    )
                    return result

                # Parse failed, retry with fix prompt
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Parse failed, retrying with fix prompt (attempt {attempt + 1})")
                    prompt = self._build_fix_prompt(content)
                    continue

            except RateLimitError as e:
                logger.warning(f"Rate limited, retrying in {RETRY_DELAY_SECONDS}s: {e}")
                time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                continue

            except APITimeoutError as e:
                logger.warning(f"API timeout, retrying: {e}")
                continue

            except APIError as e:
                logger.error(f"API error: {e}")
                if attempt == MAX_RETRIES - 1:
                    raise

        # All retries failed, return fallback
        logger.error("All retries failed, returning fallback response")
        return self._fallback_response(normalized_profile)

    def _get_system_prompt(self) -> str:
        """Get the system prompt for personalization."""
        return """You are a B2B marketing copywriter creating personalized content for ebook landing pages.

Your task: Generate a personalized intro hook (1-2 sentences) and call-to-action (CTA) based on the prospect's profile.

Rules:
1. Be conversational and specific to their role/company
2. Reference their industry or company context when available
3. Keep intro under 200 characters
4. Keep CTA under 150 characters
5. Do NOT make unsubstantiated claims (no "guaranteed", "proven", "#1", etc.)
6. Do NOT use superlatives without evidence
7. Sound helpful, not salesy

Output ONLY valid JSON in this exact format:
{
  "intro_hook": "Your personalized intro here",
  "cta": "Your call to action here"
}

No other text before or after the JSON."""

    def _build_prompt(self, profile: Dict[str, Any]) -> str:
        """Build the user prompt from profile data."""
        parts = []

        # Extract key fields
        first_name = profile.get("first_name", "there")
        company = profile.get("company_name", "your company")
        title = profile.get("title", "professional")
        industry = profile.get("industry", "your industry")
        company_size = profile.get("company_size", "")
        company_context = profile.get("company_context", "")
        seniority = profile.get("seniority", "")

        parts.append(f"Create personalized content for this prospect:\n")
        parts.append(f"- First Name: {first_name}")
        parts.append(f"- Company: {company}")
        parts.append(f"- Title: {title}")
        parts.append(f"- Industry: {industry}")

        if company_size:
            parts.append(f"- Company Size: {company_size}")

        if seniority:
            parts.append(f"- Seniority: {seniority}")

        if company_context:
            parts.append(f"\nRecent company context: {company_context[:500]}")

        parts.append("\nGenerate the JSON response now.")

        return "\n".join(parts)

    def _build_fix_prompt(self, failed_response: str) -> str:
        """Build a prompt to fix malformed JSON."""
        return f"""The previous response was not valid JSON. Here's what was returned:

{failed_response}

Please fix this and return ONLY valid JSON in this exact format:
{{
  "intro_hook": "Your personalized intro here",
  "cta": "Your call to action here"
}}

No other text."""

    def _parse_response(self, content: str) -> Optional[Dict[str, str]]:
        """
        Parse LLM response to extract intro_hook and cta.

        Args:
            content: Raw LLM response text

        Returns:
            Dict with intro_hook and cta, or None if parse failed
        """
        # Try direct JSON parse
        try:
            # Find JSON in response (handle markdown code blocks)
            json_match = re.search(r'\{[^{}]*"intro_hook"[^{}]*"cta"[^{}]*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                intro = data.get("intro_hook", "").strip()
                cta = data.get("cta", "").strip()

                if intro and cta:
                    # Validate lengths
                    if len(intro) > MAX_INTRO_LENGTH:
                        intro = intro[:MAX_INTRO_LENGTH - 3] + "..."
                    if len(cta) > MAX_CTA_LENGTH:
                        cta = cta[:MAX_CTA_LENGTH - 3] + "..."

                    return {"intro_hook": intro, "cta": cta}

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")

        return None

    def _mock_response(self, profile: Dict[str, Any]) -> Dict[str, str]:
        """Generate mock response when API key not configured."""
        logger.info("LLM: Using mock response (no API key)")

        first_name = profile.get("first_name", "")
        company = profile.get("company", profile.get("company_name", ""))
        title = profile.get("title", "")
        industry = profile.get("industry", "Technology")
        company_size = profile.get("company_size", "")

        # Industry-specific hooks
        industry_hooks = {
            "Technology": "Technology professionals like you are constantly seeking strategic insights to drive innovation.",
            "Finance": "In the fast-paced world of finance, staying ahead means having the right insights at the right time.",
            "Healthcare": "Healthcare leaders face unique challenges that require innovative solutions and fresh perspectives.",
            "Marketing": "In today's competitive landscape, marketing leaders need data-driven strategies that deliver results.",
            "Sales": "Top-performing sales teams share common strategies that set them apart from the competition.",
            "Consulting": "As a consulting professional, you know that delivering value means staying ahead of industry trends.",
            "Manufacturing": "Manufacturing leaders are transforming their operations with cutting-edge strategies.",
            "Retail": "Retail is evolving rapidly, and the most successful leaders are those who adapt quickly.",
            "Education": "Education professionals are reshaping how we learn and grow in the modern world.",
        }

        # Size-specific context
        size_context = {
            "1-10": "growing startups",
            "11-50": "scaling companies",
            "50-200": "mid-size organizations",
            "201-500": "established enterprises",
            "500+": "large organizations",
        }

        # Build personalized intro
        base_hook = industry_hooks.get(industry, "Professionals in your field are discovering new ways to drive results.")

        if first_name and company:
            intro = f"{base_hook} At {company}, you're positioned to leverage these insights for real impact."
        elif first_name:
            intro = f"{base_hook} Discover how leading professionals are tackling today's challenges."
        else:
            intro = base_hook

        # Build personalized CTA
        size_phrase = size_context.get(company_size, "successful teams")
        if title:
            cta = f"Download your free ebook and see how other {title}s at {size_phrase} are driving results"
        else:
            cta = f"Get your free insights and unlock actionable strategies for your team"

        return {
            "intro_hook": intro[:MAX_INTRO_LENGTH],  # Truncate to max length
            "cta": cta[:MAX_CTA_LENGTH],
            "model_used": "mock",
            "tokens_used": 0,
            "latency_ms": 0,
            "raw_response": {"_mock": True}
        }

    def _fallback_response(self, profile: Dict[str, Any]) -> Dict[str, str]:
        """Generate safe fallback response on all failures."""
        logger.warning("Using fallback response due to LLM failures")

        first_name = profile.get("first_name", "")
        greeting = f"Hi {first_name}, " if first_name else ""

        return {
            "intro_hook": f"{greeting}This guide was created to help professionals like you navigate common challenges in your field.",
            "cta": "Download the guide and discover actionable insights for your team.",
            "model_used": "fallback",
            "tokens_used": 0,
            "latency_ms": 0,
            "raw_response": {"_fallback": True}
        }

    async def generate_intro_hook(
        self,
        normalized_profile: Dict[str, Any]
    ) -> str:
        """Generate just the intro hook."""
        result = await self.generate_personalization(normalized_profile)
        return result.get("intro_hook", "")

    async def generate_cta(
        self,
        normalized_profile: Dict[str, Any]
    ) -> str:
        """Generate just the CTA."""
        result = await self.generate_personalization(normalized_profile)
        return result.get("cta", "")

    def should_use_opus(self, profile: Dict[str, Any]) -> bool:
        """
        Determine if Opus should be used based on profile quality.

        Uses Opus for:
        - High data quality scores
        - VIP domains (can be configured)
        - Complex industry contexts

        Args:
            profile: Normalized profile data

        Returns:
            True if Opus should be used
        """
        quality_score = profile.get("data_quality_score", 0)

        # Use Opus for high-quality profiles
        if quality_score >= 0.8:
            return True

        # Check for VIP domains (example)
        vip_domains = ["google.com", "microsoft.com", "apple.com", "amazon.com"]
        domain = profile.get("domain", "")
        if domain in vip_domains:
            return True

        return False
