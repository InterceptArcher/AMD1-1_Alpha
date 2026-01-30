"""
LLM Service: Generates personalization content (intro hook + CTA).
Multi-provider support with fallback: Anthropic → OpenAI → Gemini → mock.
Implements structured output, validation, and retry logic.
"""

import logging
import json
import time
import re
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass

import anthropic
from anthropic import APIError as AnthropicAPIError, APITimeoutError as AnthropicTimeoutError, RateLimitError as AnthropicRateLimitError

from app.config import settings

logger = logging.getLogger(__name__)

# Try to import optional providers
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.info("OpenAI not installed, skipping as fallback")

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.info("Google Generative AI not installed, skipping as fallback")

# Constants
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 1.0

# Model names per provider
ANTHROPIC_MODEL = "claude-3-5-haiku-20241022"
ANTHROPIC_OPUS = "claude-opus-4-5-20251101"
OPENAI_MODEL = "gpt-4o-mini"
GEMINI_MODEL = "gemini-1.5-flash"

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
    Generates personalized intro hook and CTA using LLMs.
    Multi-provider support: Anthropic → OpenAI → Gemini → mock fallback.
    - Tries providers in order until one succeeds
    - Implements structured output with JSON validation
    - Retry logic for transient failures
    """

    def __init__(self):
        """
        Initialize LLM service with all available providers.
        Providers are tried in order: Anthropic → OpenAI → Gemini.
        """
        self.providers: List[Dict[str, Any]] = []

        # Initialize Anthropic
        if settings.ANTHROPIC_API_KEY:
            try:
                client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
                self.providers.append({
                    "name": "anthropic",
                    "client": client,
                    "model": ANTHROPIC_MODEL
                })
                logger.info("Anthropic provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic: {e}")

        # Initialize OpenAI
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            try:
                client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                self.providers.append({
                    "name": "openai",
                    "client": client,
                    "model": OPENAI_MODEL
                })
                logger.info("OpenAI provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI: {e}")

        # Initialize Gemini
        if GEMINI_AVAILABLE and settings.GEMINI_API_KEY:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.providers.append({
                    "name": "gemini",
                    "client": genai,
                    "model": GEMINI_MODEL
                })
                logger.info("Gemini provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")

        if not self.providers:
            logger.warning("No LLM providers available - will use mock responses")
        else:
            logger.info(f"LLM service initialized with providers: {[p['name'] for p in self.providers]}")

    def _call_provider(
        self,
        provider: Dict[str, Any],
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 500
    ) -> Optional[str]:
        """
        Call a specific LLM provider and return the response text.

        Args:
            provider: Provider config dict with name, client, model
            system_prompt: System prompt
            user_prompt: User prompt
            max_tokens: Max tokens for response

        Returns:
            Response text or None if failed
        """
        name = provider["name"]
        client = provider["client"]
        model = provider["model"]

        try:
            if name == "anthropic":
                response = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": user_prompt}],
                    system=system_prompt
                )
                return response.content[0].text

            elif name == "openai":
                response = client.chat.completions.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                return response.choices[0].message.content

            elif name == "gemini":
                model_instance = client.GenerativeModel(model)
                # Gemini combines system + user in one prompt
                combined = f"{system_prompt}\n\n{user_prompt}"
                response = model_instance.generate_content(combined)
                return response.text

        except Exception as e:
            logger.warning(f"{name} provider failed: {type(e).__name__}: {e}")
            return None

        return None

    def _call_with_fallback(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 500
    ) -> Tuple[Optional[str], str]:
        """
        Try each provider in order until one succeeds.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            max_tokens: Max tokens

        Returns:
            Tuple of (response_text, provider_name) or (None, "none")
        """
        for provider in self.providers:
            for attempt in range(MAX_RETRIES):
                result = self._call_provider(provider, system_prompt, user_prompt, max_tokens)
                if result:
                    return result, provider["name"]
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY_SECONDS)

        return None, "none"

    async def generate_personalization(
        self,
        normalized_profile: Dict[str, Any],
        use_opus: bool = False,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Generate intro hook and CTA from normalized profile.
        Uses multi-provider fallback: Anthropic → OpenAI → Gemini → mock.

        Args:
            normalized_profile: Normalized enrichment data
            use_opus: Whether to use Opus model (Anthropic only)
            user_context: User-provided context (goal, persona, industry)

        Returns:
            Dict with 'intro_hook', 'cta', and metadata
        """
        if not self.providers:
            return self._mock_response(normalized_profile, user_context)

        start_time = time.time()
        prompt = self._build_prompt(normalized_profile, user_context)
        system_prompt = self._get_system_prompt()

        # Try with fallback
        content, provider_name = self._call_with_fallback(system_prompt, prompt, max_tokens=500)

        if content:
            parsed = self._parse_response(content)

            if parsed:
                latency_ms = int((time.time() - start_time) * 1000)

                result = {
                    "intro_hook": parsed["intro_hook"],
                    "cta": parsed["cta"],
                    "model_used": provider_name,
                    "tokens_used": 0,  # Not tracking across providers
                    "latency_ms": latency_ms,
                    "raw_response": {"content": content}
                }

                logger.info(
                    f"Generated personalization: provider={provider_name}, latency={latency_ms}ms"
                )
                return result

        # All providers failed, return mock response
        logger.warning("All LLM providers failed, returning mock response")
        return self._mock_response(normalized_profile, user_context)

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

    def _build_prompt(self, profile: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None) -> str:
        """Build the user prompt from profile data and user-provided context."""
        parts = []
        user_context = user_context or {}

        # Extract key fields from enrichment
        first_name = profile.get("first_name", "there")
        company = profile.get("company_name", "your company")
        title = profile.get("title", "professional")
        industry = profile.get("industry", "your industry")
        company_size = profile.get("company_size", "")
        company_context = profile.get("company_context", "")
        seniority = profile.get("seniority", "")

        # Extract user-provided context (more reliable than API data)
        user_goal = user_context.get("goal", "")
        user_persona = user_context.get("persona", "")
        user_industry = user_context.get("industry_input", "")

        # Goal mapping for more natural language
        goal_descriptions = {
            "exploring": "exploring modernization options and doing early research",
            "evaluating": "comparing different approaches for their organization",
            "learning": "learning about best practices and industry trends",
            "building_case": "building a business case to present internally"
        }

        # Persona mapping for richer context
        persona_descriptions = {
            "executive": "an executive leader (C-suite or VP level) focused on strategic decisions",
            "it_infrastructure": "an IT/Infrastructure professional managing technical operations",
            "security": "a security professional focused on protecting systems and data",
            "data_ai": "a data/AI engineer working on analytics and machine learning",
            "sales_gtm": "a sales or GTM leader driving revenue growth",
            "hr_people": "an HR/People Ops professional managing talent and culture",
            "other": "a professional seeking industry insights"
        }

        # Industry-specific angles
        industry_angles = {
            "healthcare": "compliance, patient outcomes, and operational efficiency",
            "financial_services": "risk management, regulatory compliance, and digital transformation",
            "technology": "innovation velocity, scalability, and technical excellence",
            "gaming_media": "user engagement, content delivery, and real-time performance",
            "manufacturing": "operational efficiency, supply chain optimization, and IoT",
            "retail": "customer experience, omnichannel strategy, and inventory management",
            "government": "security, compliance, and citizen services modernization",
            "energy": "grid modernization, sustainability, and operational resilience",
            "telecommunications": "network performance, 5G adoption, and customer experience"
        }

        parts.append(f"Create personalized content for this prospect:\n")
        parts.append(f"- First Name: {first_name}")
        parts.append(f"- Company: {company}")
        parts.append(f"- Title: {title}")

        # Prefer user-provided industry if available
        effective_industry = user_industry or industry
        parts.append(f"- Industry: {effective_industry}")

        if company_size:
            parts.append(f"- Company Size: {company_size}")

        if seniority:
            parts.append(f"- Seniority: {seniority}")

        # Add user-provided context for better personalization
        if user_goal:
            goal_desc = goal_descriptions.get(user_goal, user_goal)
            parts.append(f"\nThis person is currently {goal_desc}.")

        if user_persona:
            persona_desc = persona_descriptions.get(user_persona, user_persona)
            parts.append(f"They are {persona_desc}.")

        if effective_industry in industry_angles:
            parts.append(f"In their industry, key concerns include {industry_angles[effective_industry]}.")

        if company_context:
            parts.append(f"\nRecent company context: {company_context[:500]}")

        parts.append("\nGenerate content that speaks directly to their role, goals, and industry context.")
        parts.append("Make it specific and actionable, not generic.")
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

    def _mock_response(self, profile: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Generate mock response when API key not configured."""
        logger.info("LLM: Using mock response (no API key)")
        user_context = user_context or {}

        first_name = profile.get("first_name", "")
        company = profile.get("company", profile.get("company_name", ""))
        title = profile.get("title", "")
        industry = profile.get("industry", "Technology")
        company_size = profile.get("company_size", "")

        # Use user-provided context if available
        user_goal = user_context.get("goal", "")
        user_persona = user_context.get("persona", "")
        user_industry = user_context.get("industry_input", "")

        # Prefer user-provided industry
        effective_industry = user_industry or industry

        # Industry-specific hooks (tailored for AMD use case)
        industry_hooks = {
            "healthcare": "Healthcare organizations are modernizing their infrastructure to improve patient outcomes while maintaining strict compliance.",
            "financial_services": "Financial services leaders are balancing regulatory requirements with the need for digital transformation and innovation.",
            "technology": "Tech companies like yours are pushing the boundaries of what's possible with modern infrastructure and AI workloads.",
            "gaming_media": "Gaming and media companies need infrastructure that delivers real-time performance at massive scale.",
            "manufacturing": "Manufacturing leaders are leveraging smart infrastructure to optimize operations and drive efficiency.",
            "retail": "Retail organizations are transforming customer experiences through modern, scalable technology.",
            "government": "Government agencies are modernizing citizen services while maintaining the highest security standards.",
            "energy": "Energy companies are building resilient, sustainable infrastructure for the future.",
            "telecommunications": "Telecom providers are building next-generation networks to meet growing connectivity demands.",
        }

        # Goal-specific intros
        goal_intros = {
            "exploring": "You're taking the right first step by exploring your options.",
            "evaluating": "Making the right infrastructure decision requires careful evaluation.",
            "learning": "Staying informed on best practices gives you a strategic advantage.",
            "building_case": "Building a compelling business case starts with the right insights.",
        }

        # Persona-specific CTAs
        persona_ctas = {
            "executive": "Get the executive summary with ROI insights for your board",
            "it_infrastructure": "Download the technical deep-dive with architecture patterns",
            "security": "Access the security-focused guide with compliance frameworks",
            "data_ai": "Get the data infrastructure guide optimized for AI workloads",
            "sales_gtm": "Download strategies to accelerate your digital sales motion",
            "hr_people": "Learn how tech modernization impacts talent and culture",
        }

        # Build personalized intro
        base_hook = industry_hooks.get(effective_industry, "Organizations like yours are discovering new ways to modernize and scale.")
        goal_hook = goal_intros.get(user_goal, "")

        if first_name and company:
            intro = f"{goal_hook} {base_hook}".strip()
            if len(intro) < 50:
                intro = f"{intro} At {company}, these insights can drive real impact."
        elif first_name:
            intro = f"{goal_hook} {base_hook}".strip()
        else:
            intro = base_hook

        # Build personalized CTA based on persona
        if user_persona and user_persona in persona_ctas:
            cta = persona_ctas[user_persona]
        elif title:
            cta = f"Get your free ebook with actionable insights for {title}s like you"
        else:
            cta = "Download your personalized guide and unlock strategies for your team"

        return {
            "intro_hook": intro[:MAX_INTRO_LENGTH],
            "cta": cta[:MAX_CTA_LENGTH],
            "model_used": "mock",
            "tokens_used": 0,
            "latency_ms": 0,
            "raw_response": {"_mock": True, "user_context": user_context}
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

    async def generate_ebook_personalization(
        self,
        profile: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None,
        company_news: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate personalized content for AMD ebook - 3 sections:
        1. Hook/Intro - Based on role, buying stage, company news
        2. Case Study Framing - Context for why selected case study is relevant
        3. CTA - Based on buying stage and role

        Uses multi-provider fallback: Anthropic → OpenAI → Gemini → mock.

        Args:
            profile: Normalized enrichment data
            user_context: User-provided context (goal, persona, industry)
            company_news: Recent company news from Tavily

        Returns:
            Dict with personalized_hook, case_study_framing, personalized_cta
        """
        if not self.providers:
            return self._mock_ebook_response(profile, user_context)

        user_context = user_context or {}
        start_time = time.time()

        prompt = self._build_ebook_prompt(profile, user_context, company_news)
        system_prompt = self._get_ebook_system_prompt()

        # Try with fallback
        content, provider_name = self._call_with_fallback(system_prompt, prompt, max_tokens=1000)

        if content:
            parsed = self._parse_ebook_response(content)

            if parsed:
                latency_ms = int((time.time() - start_time) * 1000)
                parsed["model_used"] = provider_name
                parsed["tokens_used"] = 0
                parsed["latency_ms"] = latency_ms
                logger.info(f"Generated ebook personalization: provider={provider_name}, latency={latency_ms}ms")
                return parsed

        # All providers failed
        logger.warning("All LLM providers failed for ebook personalization, using mock")
        return self._mock_ebook_response(profile, user_context)

    def _get_ebook_system_prompt(self) -> str:
        """System prompt for AMD ebook personalization."""
        return """You are a B2B marketing expert creating personalized content for AMD's enterprise AI readiness ebook.

Your task: Generate 3 personalized sections based on the prospect's profile, buying stage, and company context.

The ebook is about data center modernization and AI readiness. It covers:
- Three stages: Leaders (fully modernized), Challengers (in progress), Observers (planning)
- Modernization strategies: "modernize in place" vs "refactor and shift"
- Case studies: KT Cloud (telecom/AI), Smurfit Westrock (manufacturing/sustainability), PQR (IT services)
- AMD solutions: EPYC CPUs, Instinct GPUs, Pensando DPUs

Rules:
1. Hook should be 2-3 sentences, directly addressing their situation
2. Reference their company/industry when relevant
3. Case study framing should explain why the selected case study is relevant to them
4. CTA should be specific to their buying stage and role
5. Sound helpful and consultative, not salesy
6. No unsubstantiated claims ("guaranteed", "proven", "#1")

Output ONLY valid JSON:
{
  "personalized_hook": "Your personalized opening...",
  "case_study_framing": "Why this case study matters for you...",
  "personalized_cta": "Your specific call to action..."
}"""

    def _build_ebook_prompt(
        self,
        profile: Dict[str, Any],
        user_context: Dict[str, Any],
        company_news: Optional[str]
    ) -> str:
        """Build prompt for ebook personalization."""
        parts = ["Generate personalized AMD ebook content for this prospect:\n"]

        # Profile data
        parts.append(f"Name: {profile.get('first_name', 'Reader')} {profile.get('last_name', '')}")
        parts.append(f"Company: {profile.get('company_name', 'their company')}")
        parts.append(f"Title: {profile.get('title', 'Professional')}")
        parts.append(f"Industry: {user_context.get('industry_input') or profile.get('industry', 'Technology')}")

        if profile.get('company_size'):
            parts.append(f"Company Size: {profile.get('company_size')}")

        # User context
        goal = user_context.get('goal', '')
        persona = user_context.get('persona', '')

        goal_map = {
            "exploring": "early research phase, discovering what's possible with AI infrastructure",
            "evaluating": "actively comparing solutions and building a shortlist",
            "learning": "deepening expertise on best practices and implementation",
            "building_case": "preparing an internal business case for investment"
        }

        persona_map = {
            "executive": "C-suite/VP level, focused on strategic outcomes and ROI",
            "it_infrastructure": "IT/Infrastructure professional, focused on technical implementation",
            "security": "Security professional, focused on compliance and data protection",
            "data_ai": "Data/AI engineer, focused on model performance and compute efficiency",
            "sales_gtm": "Sales/GTM leader, focused on revenue impact and competitive advantage",
            "hr_people": "HR/People Ops, focused on workforce enablement"
        }

        if goal:
            parts.append(f"\nBuying Stage: {goal_map.get(goal, goal)}")
        if persona:
            parts.append(f"Role Focus: {persona_map.get(persona, persona)}")

        # Company news context
        if company_news:
            parts.append(f"\nRecent Company News: {company_news[:500]}")

        # Case study selection hint
        industry = (user_context.get('industry_input') or profile.get('industry', '')).lower()
        if 'telecom' in industry or 'tech' in industry or 'gaming' in industry:
            parts.append("\nMost relevant case study: KT Cloud (AI/GPU cloud services)")
        elif 'manufact' in industry or 'retail' in industry or 'energy' in industry:
            parts.append("\nMost relevant case study: Smurfit Westrock (cost optimization, sustainability)")
        else:
            parts.append("\nMost relevant case study: PQR (IT services, security, automation)")

        parts.append("\nGenerate the personalized JSON now.")
        return "\n".join(parts)

    def _parse_ebook_response(self, content: str) -> Optional[Dict[str, str]]:
        """Parse ebook personalization response."""
        try:
            json_match = re.search(
                r'\{[^{}]*"personalized_hook"[^{}]*"case_study_framing"[^{}]*"personalized_cta"[^{}]*\}',
                content,
                re.DOTALL
            )
            if json_match:
                data = json.loads(json_match.group())
                if all(k in data for k in ["personalized_hook", "case_study_framing", "personalized_cta"]):
                    return data
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error for ebook response: {e}")
        return None

    def _mock_ebook_response(
        self,
        profile: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate mock ebook personalization when API not available."""
        user_context = user_context or {}
        first_name = profile.get('first_name', 'Reader')
        company = profile.get('company_name', 'your organization')
        title = profile.get('title', 'leader')
        industry = user_context.get('industry_input') or profile.get('industry', 'your industry')
        goal = user_context.get('goal', 'exploring')
        persona = user_context.get('persona', 'executive')

        # Hook based on buying stage
        hooks = {
            "exploring": f"As {company} begins exploring AI infrastructure options, understanding where you stand on the modernization curve is the first step. This guide will help you assess your current state and identify the path forward.",
            "evaluating": f"You're evaluating AI infrastructure solutions for {company}—a critical decision that will shape your competitive position. This guide provides the framework and proof points you need to make an informed choice.",
            "learning": f"Staying ahead of AI infrastructure trends is essential for {title}s in {industry}. This guide distills the latest research and real-world examples into actionable insights for {company}.",
            "building_case": f"Building a compelling business case for AI infrastructure investment at {company} requires solid data and clear ROI projections. This guide provides the evidence and frameworks you need."
        }

        # CTA based on persona and stage
        ctas = {
            ("executive", "exploring"): "Discover where your organization stands on the AI readiness curve—and what Leaders do differently.",
            ("executive", "evaluating"): "See the business impact metrics that helped similar organizations justify their AI infrastructure investments.",
            ("executive", "building_case"): "Access the executive brief with ROI data and board-ready insights for your AI infrastructure proposal.",
            ("it_infrastructure", "exploring"): "Explore the technical architectures that distinguish AI-ready data centers from legacy environments.",
            ("it_infrastructure", "evaluating"): "Compare the modernization approaches: in-place upgrades vs. cloud migration—with technical trade-offs.",
            ("data_ai", "exploring"): "Learn how AMD Instinct accelerators deliver the compute performance your AI workloads demand.",
            ("data_ai", "evaluating"): "See the benchmark data: throughput, cost-per-training-run, and energy efficiency comparisons.",
            ("security", "exploring"): "Understand how modern AI infrastructure addresses security and compliance requirements.",
            ("security", "evaluating"): "Review the security architectures used by regulated industries adopting AI at scale.",
        }

        # Case study framing based on industry
        industry_lower = industry.lower() if industry else ""
        if 'telecom' in industry_lower or 'tech' in industry_lower:
            case_framing = f"KT Cloud faced challenges similar to {company}—scaling AI compute while managing costs. Their approach with AMD Instinct accelerators offers a blueprint for your AI infrastructure strategy."
        elif 'manufact' in industry_lower or 'retail' in industry_lower:
            case_framing = f"Smurfit Westrock's journey mirrors the challenges facing {industry} organizations: balancing cost optimization with sustainability goals. Their 25% cost reduction while cutting emissions shows what's possible."
        else:
            case_framing = f"PQR's transformation demonstrates how organizations in {industry} can modernize infrastructure while enhancing security. Their automation-first approach delivers both efficiency and protection."

        hook = hooks.get(goal, hooks["exploring"])
        cta_key = (persona, goal)
        cta = ctas.get(cta_key, ctas.get((persona, "exploring"), "Explore how AMD can accelerate your AI infrastructure journey."))

        return {
            "personalized_hook": hook,
            "case_study_framing": case_framing,
            "personalized_cta": cta,
            "model_used": "mock",
            "tokens_used": 0,
            "latency_ms": 0
        }
