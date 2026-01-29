"""
Compliance service for validating personalization content.
Checks for:
  - Length constraints
  - Banned terms
  - Unsupported claims (superlatives, guarantees)
  - Brand safety issues
"""

import logging
import re
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Length constraints
MAX_INTRO_LENGTH = 200
MAX_CTA_LENGTH = 150

# Banned terms - words that should never appear
BANNED_TERMS = [
    # Unsubstantiated claims
    "guaranteed", "guarantee", "guarantees",
    "proven", "scientifically proven",
    "100%", "100 percent",
    "best in class", "best-in-class",
    "world's best", "world's leading",
    "industry leading", "industry-leading",
    "market leading", "market-leading",
    "#1", "number one", "number 1",
    "top rated", "top-rated",
    "award winning", "award-winning",
    "certified", "accredited",

    # Urgency/pressure tactics
    "act now", "limited time", "don't miss out",
    "once in a lifetime", "last chance",
    "expires soon", "hurry",

    # Exaggeration
    "revolutionary", "groundbreaking",
    "game-changing", "game changer",
    "unprecedented", "unparalleled",
    "unmatched", "unbeatable",

    # Absolute claims
    "always", "never", "everyone",
    "all companies", "every business",
    "no one else", "only solution",

    # Competitive attacks
    "unlike competitors", "better than",
    "competitors can't", "others fail",
]

# Superlative patterns - regex patterns for superlatives
SUPERLATIVE_PATTERNS = [
    r"\bmost\s+\w+\b",  # most powerful, most effective
    r"\bbest\s+\w+\b",  # best solution, best practice (context dependent)
    r"\beasiest\b",
    r"\bfastest\b",
    r"\bcheapest\b",
    r"\bsmartest\b",
    r"\bstrongest\b",
    r"\bbiggest\b",
    r"\blargest\b",
    r"\bfirst\s+ever\b",
    r"\bonly\s+(way|solution|choice)\b",
]

# Claim patterns that need evidence
CLAIM_PATTERNS = [
    (r"\d+%\s+(increase|decrease|improvement|reduction|growth)", "percentage claim"),
    (r"\d+x\s+(faster|better|more|improvement)", "multiplier claim"),
    (r"save\s+\$?\d+", "savings claim"),
    (r"in\s+just\s+\d+\s+(days?|weeks?|months?)", "time claim"),
    (r"over\s+\d+\s+(customers?|clients?|companies)", "customer count claim"),
]

# Safe fallback content
FALLBACK_INTROS = [
    "This guide was designed to help professionals like you tackle common challenges.",
    "We've compiled insights from industry experts to help you navigate this topic.",
    "This resource covers practical strategies for your team to consider.",
]

FALLBACK_CTAS = [
    "Download the guide to explore these insights.",
    "Get your copy and discover actionable strategies.",
    "Access the full guide for your team.",
]


@dataclass
class ComplianceResult:
    """Result of compliance check."""
    passed: bool
    issues: List[str] = field(default_factory=list)
    original_intro: str = ""
    original_cta: str = ""
    corrected_intro: Optional[str] = None
    corrected_cta: Optional[str] = None


class ComplianceService:
    """
    Validates personalization content for compliance.
    Checks length, banned terms, unsupported claims.
    Can auto-correct or return fallback content.
    """

    def __init__(
        self,
        max_intro_length: int = MAX_INTRO_LENGTH,
        max_cta_length: int = MAX_CTA_LENGTH,
        custom_banned_terms: Optional[List[str]] = None
    ):
        """
        Initialize compliance service.

        Args:
            max_intro_length: Maximum intro hook length
            max_cta_length: Maximum CTA length
            custom_banned_terms: Additional banned terms
        """
        self.max_intro_length = max_intro_length
        self.max_cta_length = max_cta_length
        self.banned_terms = BANNED_TERMS.copy()

        if custom_banned_terms:
            self.banned_terms.extend(custom_banned_terms)

        # Compile regex patterns for efficiency
        self.superlative_patterns = [
            re.compile(p, re.IGNORECASE) for p in SUPERLATIVE_PATTERNS
        ]
        self.claim_patterns = [
            (re.compile(p, re.IGNORECASE), desc) for p, desc in CLAIM_PATTERNS
        ]

        logger.info(f"Compliance service initialized with {len(self.banned_terms)} banned terms")

    def check(
        self,
        intro_hook: str,
        cta: str,
        auto_correct: bool = True
    ) -> ComplianceResult:
        """
        Check content for compliance issues.

        Args:
            intro_hook: Generated intro hook
            cta: Generated CTA
            auto_correct: Whether to attempt auto-correction

        Returns:
            ComplianceResult with pass/fail and any issues
        """
        result = ComplianceResult(
            passed=True,
            original_intro=intro_hook,
            original_cta=cta
        )

        # Check intro
        intro_issues = self._check_content(intro_hook, "intro")
        intro_length_ok = len(intro_hook) <= self.max_intro_length

        if not intro_length_ok:
            result.issues.append(f"Intro exceeds max length ({len(intro_hook)}/{self.max_intro_length})")

        result.issues.extend(intro_issues)

        # Check CTA
        cta_issues = self._check_content(cta, "cta")
        cta_length_ok = len(cta) <= self.max_cta_length

        if not cta_length_ok:
            result.issues.append(f"CTA exceeds max length ({len(cta)}/{self.max_cta_length})")

        result.issues.extend(cta_issues)

        # Determine if passed
        if result.issues:
            result.passed = False

            if auto_correct:
                result.corrected_intro, result.corrected_cta = self._auto_correct(
                    intro_hook, cta, result.issues
                )

                # Re-check corrected content
                if result.corrected_intro and result.corrected_cta:
                    corrected_intro_issues = self._check_content(result.corrected_intro, "intro")
                    corrected_cta_issues = self._check_content(result.corrected_cta, "cta")

                    if not corrected_intro_issues and not corrected_cta_issues:
                        result.passed = True
                        logger.info("Content auto-corrected and passed compliance")

        logger.info(f"Compliance check: passed={result.passed}, issues={len(result.issues)}")
        return result

    def _check_content(self, content: str, content_type: str) -> List[str]:
        """
        Check a single piece of content for issues.

        Args:
            content: Text to check
            content_type: 'intro' or 'cta' for logging

        Returns:
            List of issue descriptions
        """
        issues = []
        content_lower = content.lower()

        # Check banned terms
        for term in self.banned_terms:
            if term.lower() in content_lower:
                issues.append(f"{content_type}: Contains banned term '{term}'")

        # Check superlatives
        for pattern in self.superlative_patterns:
            matches = pattern.findall(content)
            for match in matches:
                # Allow some context-appropriate superlatives
                if not self._is_allowed_superlative(match, content):
                    issues.append(f"{content_type}: Contains superlative '{match}'")

        # Check claims that need evidence
        for pattern, desc in self.claim_patterns:
            if pattern.search(content):
                issues.append(f"{content_type}: Contains unsupported {desc}")

        return issues

    def _is_allowed_superlative(self, match: str, context: str) -> bool:
        """
        Check if a superlative is allowed in context.

        Some superlatives are OK:
        - "best practices" (common phrase)
        - References to user's own achievements

        Args:
            match: The matched superlative
            context: Full content for context

        Returns:
            True if allowed
        """
        allowed_phrases = [
            "best practices",
            "best fit",
            "best suited",
            "most common",
            "most important",
        ]

        match_lower = match.lower()
        for phrase in allowed_phrases:
            if phrase in context.lower():
                return True

        return False

    def _auto_correct(
        self,
        intro: str,
        cta: str,
        issues: List[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Attempt to auto-correct content issues.

        Strategy:
        1. Try to remove/replace problematic terms
        2. If too many issues, fall back to safe content

        Args:
            intro: Original intro
            cta: Original CTA
            issues: List of issues found

        Returns:
            Tuple of (corrected_intro, corrected_cta) or (None, None) if can't fix
        """
        # If too many issues, use fallback
        if len(issues) > 3:
            logger.warning(f"Too many issues ({len(issues)}), using fallback content")
            return self._get_fallback_content()

        corrected_intro = intro
        corrected_cta = cta

        # Try to fix specific issues
        for issue in issues:
            if "banned term" in issue:
                # Extract the term
                term_match = re.search(r"'([^']+)'", issue)
                if term_match:
                    term = term_match.group(1)
                    # Remove the term and clean up
                    corrected_intro = self._remove_term(corrected_intro, term)
                    corrected_cta = self._remove_term(corrected_cta, term)

            elif "exceeds max length" in issue:
                # Truncate
                if "Intro" in issue:
                    corrected_intro = corrected_intro[:self.max_intro_length - 3] + "..."
                else:
                    corrected_cta = corrected_cta[:self.max_cta_length - 3] + "..."

        # Validate corrections aren't empty or too short
        if len(corrected_intro.strip()) < 20 or len(corrected_cta.strip()) < 10:
            return self._get_fallback_content()

        return corrected_intro, corrected_cta

    def _remove_term(self, content: str, term: str) -> str:
        """Remove a term from content while preserving readability."""
        # Simple removal with cleanup
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        result = pattern.sub('', content)

        # Clean up double spaces
        result = re.sub(r'\s+', ' ', result).strip()

        # Clean up orphaned punctuation
        result = re.sub(r'\s+([,.])', r'\1', result)
        result = re.sub(r'([,.])\s*([,.])', r'\1', result)

        return result

    def _get_fallback_content(self) -> Tuple[str, str]:
        """Get safe fallback content."""
        import random
        return (
            random.choice(FALLBACK_INTROS),
            random.choice(FALLBACK_CTAS)
        )

    def get_safe_intro(self, profile: Optional[Dict[str, Any]] = None) -> str:
        """
        Get a safe intro that will always pass compliance.

        Args:
            profile: Optional profile for light personalization

        Returns:
            Safe intro text
        """
        if profile and profile.get("first_name"):
            name = profile["first_name"]
            return f"Hi {name}, this guide was designed to help professionals like you."

        return FALLBACK_INTROS[0]

    def get_safe_cta(self, profile: Optional[Dict[str, Any]] = None) -> str:
        """
        Get a safe CTA that will always pass compliance.

        Args:
            profile: Optional profile (unused, for interface consistency)

        Returns:
            Safe CTA text
        """
        return FALLBACK_CTAS[0]


# Convenience function
def validate_personalization(
    intro_hook: str,
    cta: str,
    auto_correct: bool = True
) -> ComplianceResult:
    """
    Validate personalization content.

    Args:
        intro_hook: Generated intro hook
        cta: Generated CTA
        auto_correct: Whether to attempt fixes

    Returns:
        ComplianceResult
    """
    service = ComplianceService()
    return service.check(intro_hook, cta, auto_correct)
