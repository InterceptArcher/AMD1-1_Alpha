"""
PDF Service: Generates personalized ebook PDFs.
Uses HTML templates with personalization slots.
Stores PDFs in Supabase Storage, returns signed URLs.
"""

import logging
import io
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from string import Template

from app.config import settings
from app.services.ebook_content import (
    EBOOK_SECTIONS,
    CASE_STUDIES,
    get_case_study_for_industry,
    get_buying_stage_context,
    get_persona_context
)

logger = logging.getLogger(__name__)

# PDF Configuration
PDF_EXPIRY_HOURS = 24 * 7  # 7 days


class PDFService:
    """
    Generates personalized PDF ebooks.
    - Uses HTML templates with personalization
    - Stores in Supabase Storage
    - Returns signed URLs for download
    """

    def __init__(self, supabase_client=None):
        """
        Initialize PDF service.

        Args:
            supabase_client: Optional Supabase client for storage
        """
        self.supabase = supabase_client
        self.storage_bucket = "personalized-pdfs"
        logger.info("PDF service initialized")

    async def generate_pdf(
        self,
        job_id: int,
        profile: Dict[str, Any],
        intro_hook: str,
        cta: str
    ) -> Dict[str, Any]:
        """
        Generate personalized PDF for a job.

        Args:
            job_id: Job ID for tracking
            profile: Normalized profile data
            intro_hook: Personalized intro hook
            cta: Personalized CTA

        Returns:
            Dict with pdf_url, storage_path, file_size
        """
        try:
            # Generate HTML content
            html_content = self._render_template(profile, intro_hook, cta)

            # Convert to PDF
            pdf_bytes = await self._html_to_pdf(html_content)

            if not pdf_bytes:
                raise ValueError("PDF generation returned empty content")

            # Generate unique filename
            email = profile.get("email", "unknown")
            filename = self._generate_filename(email, job_id)

            # Store in Supabase Storage (if available)
            if self.supabase:
                storage_path, pdf_url = await self._store_pdf(
                    pdf_bytes, filename
                )
            else:
                # Return base64 for testing
                import base64
                storage_path = f"local/{filename}"
                pdf_url = f"data:application/pdf;base64,{base64.b64encode(pdf_bytes).decode()}"

            result = {
                "pdf_url": pdf_url,
                "storage_path": storage_path,
                "file_size_bytes": len(pdf_bytes),
                "generated_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=PDF_EXPIRY_HOURS)).isoformat()
            }

            logger.info(f"Generated PDF for job {job_id}: {len(pdf_bytes)} bytes")
            return result

        except Exception as e:
            logger.error(f"PDF generation failed for job {job_id}: {e}")
            raise

    async def generate_amd_ebook(
        self,
        job_id: int,
        profile: Dict[str, Any],
        personalization: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate personalized AMD ebook with 3 personalization points.

        Args:
            job_id: Job ID for tracking
            profile: Normalized profile data
            personalization: Dict with personalized_hook, case_study_framing, personalized_cta
            user_context: User-provided context (goal, persona, industry)

        Returns:
            Dict with pdf_url, storage_path, file_size
        """
        try:
            user_context = user_context or {}

            # Get the appropriate case study based on industry
            industry = user_context.get("industry_input") or profile.get("industry", "technology")
            case_study = get_case_study_for_industry(industry)

            # Generate HTML content with AMD ebook template
            html_content = self._render_amd_ebook_template(
                profile=profile,
                personalized_hook=personalization.get("personalized_hook", ""),
                case_study=case_study,
                case_study_framing=personalization.get("case_study_framing", ""),
                personalized_cta=personalization.get("personalized_cta", ""),
                user_context=user_context
            )

            # Convert to PDF
            pdf_bytes = await self._html_to_pdf(html_content)

            if not pdf_bytes:
                raise ValueError("PDF generation returned empty content")

            # Generate unique filename
            email = profile.get("email", "unknown")
            filename = self._generate_filename(email, job_id)

            # Store in Supabase Storage (if available)
            if self.supabase:
                storage_path, pdf_url = await self._store_pdf(pdf_bytes, filename)
            else:
                import base64
                storage_path = f"local/{filename}"
                pdf_url = f"data:application/pdf;base64,{base64.b64encode(pdf_bytes).decode()}"

            result = {
                "pdf_url": pdf_url,
                "storage_path": storage_path,
                "file_size_bytes": len(pdf_bytes),
                "generated_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(hours=PDF_EXPIRY_HOURS)).isoformat(),
                "case_study_used": case_study["title"]
            }

            logger.info(f"Generated AMD ebook for job {job_id}: {len(pdf_bytes)} bytes, case study: {case_study['title']}")
            return result

        except Exception as e:
            logger.error(f"AMD ebook generation failed for job {job_id}: {e}")
            raise

    def _render_amd_ebook_template(
        self,
        profile: Dict[str, Any],
        personalized_hook: str,
        case_study: Dict[str, Any],
        case_study_framing: str,
        personalized_cta: str,
        user_context: Dict[str, Any]
    ) -> str:
        """Render AMD ebook HTML template with personalization."""
        template = Template(self._get_amd_ebook_template())

        variables = {
            "first_name": profile.get("first_name", "Reader"),
            "last_name": profile.get("last_name", ""),
            "company_name": profile.get("company_name") or profile.get("company", "your company"),
            "title": profile.get("title", "Professional"),
            "industry": user_context.get("industry_input") or profile.get("industry", "your industry"),
            "generated_date": datetime.utcnow().strftime("%B %d, %Y"),
            # Personalized sections
            "personalized_hook": personalized_hook,
            "case_study_framing": case_study_framing,
            "personalized_cta": personalized_cta,
            # Case study content
            "case_study_title": case_study["title"],
            "case_study_company": case_study["company"],
            "case_study_industry": case_study["industry"],
            "case_study_challenge": case_study["challenge"],
            "case_study_solution": case_study["solution"],
            "case_study_quote": case_study["quote"],
            "case_study_quote_author": case_study["quote_author"],
            "case_study_result": case_study["result"],
            # Static content
            "intro_section": EBOOK_SECTIONS["intro_section"],
            "three_stages_intro": EBOOK_SECTIONS["three_stages_intro"],
            "leaders_section": EBOOK_SECTIONS["leaders_section"],
            "challengers_section": EBOOK_SECTIONS["challengers_section"],
            "observers_section": EBOOK_SECTIONS["observers_section"],
            "path_to_leadership": EBOOK_SECTIONS["path_to_leadership"],
            "modernization_models": EBOOK_SECTIONS["modernization_models"],
            "why_amd": EBOOK_SECTIONS["why_amd"],
            "assessment_questions": EBOOK_SECTIONS["assessment_questions"],
        }

        return template.safe_substitute(variables)

    def _get_amd_ebook_template(self) -> str:
        """Get the AMD ebook HTML template - matching official AMD design."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>An Enterprise AI Readiness Framework</title>
    <style>
        @page {
            size: letter;
            margin: 0;
        }
        @font-face {
            font-family: 'AMD';
            src: local('Segoe UI'), local('Helvetica Neue'), local('Arial');
        }
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.5;
            color: #ffffff;
            background: #0a0a12;
            font-size: 10pt;
        }

        /* AMD Brand Colors */
        :root {
            --amd-cyan: #00c8aa;
            --amd-dark: #0a0a12;
            --amd-darker: #050508;
            --amd-gray: #1a1a2e;
            --amd-light-gray: #8a8a9a;
        }

        /* Cover Page */
        .cover-page {
            min-height: 100vh;
            background: linear-gradient(135deg, #0a0a12 0%, #0d1a2d 50%, #0a0a12 100%);
            padding: 60px 50px;
            position: relative;
            page-break-after: always;
        }
        .amd-logo {
            font-size: 24pt;
            font-weight: bold;
            letter-spacing: 2px;
            margin-bottom: 200px;
        }
        .cover-subtitle {
            color: var(--amd-cyan);
            font-size: 13pt;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 15px;
        }
        .cover-title {
            font-size: 42pt;
            font-weight: 800;
            line-height: 1.1;
            margin-bottom: 30px;
            text-transform: uppercase;
        }
        .cover-personalized {
            margin-top: 60px;
            padding: 25px 30px;
            background: rgba(0, 200, 170, 0.1);
            border: 1px solid var(--amd-cyan);
            border-radius: 4px;
            max-width: 400px;
        }
        .cover-personalized-label {
            font-size: 9pt;
            color: var(--amd-cyan);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        .cover-personalized-name {
            font-size: 18pt;
            font-weight: 700;
            margin-bottom: 5px;
        }
        .cover-personalized-role {
            font-size: 11pt;
            color: var(--amd-light-gray);
        }

        /* Content Pages */
        .content-page {
            background: var(--amd-dark);
            padding: 50px;
            min-height: 100vh;
            page-break-after: always;
        }
        .content-page:last-child {
            page-break-after: auto;
        }

        /* Section Headers */
        .section-header {
            margin-bottom: 30px;
        }
        .section-header h2 {
            font-size: 26pt;
            font-weight: 800;
            line-height: 1.2;
            margin-bottom: 20px;
            text-transform: uppercase;
        }
        .section-header::before {
            content: '';
            display: block;
            width: 60px;
            height: 4px;
            background: var(--amd-cyan);
            margin-bottom: 25px;
        }

        /* Personalized Hook Section */
        .personalized-hook {
            background: linear-gradient(135deg, rgba(0, 200, 170, 0.15) 0%, rgba(0, 200, 170, 0.05) 100%);
            border-left: 4px solid var(--amd-cyan);
            padding: 30px;
            margin: 30px 0;
            font-size: 12pt;
            line-height: 1.6;
        }
        .personalized-hook-label {
            color: var(--amd-cyan);
            font-size: 10pt;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 12px;
        }

        /* Statistics Grid */
        .stats-grid {
            display: flex;
            justify-content: space-between;
            gap: 30px;
            margin: 40px 0;
        }
        .stat-item {
            text-align: center;
            flex: 1;
        }
        .stat-number {
            font-size: 48pt;
            font-weight: 300;
            color: var(--amd-cyan);
            line-height: 1;
        }
        .stat-suffix {
            font-size: 24pt;
            color: var(--amd-cyan);
        }
        .stat-label {
            font-size: 9pt;
            color: var(--amd-light-gray);
            margin-top: 10px;
            line-height: 1.4;
        }

        /* Info Boxes */
        .info-box {
            background: rgba(0, 200, 170, 0.08);
            border: 1px solid rgba(0, 200, 170, 0.3);
            padding: 25px;
            margin: 25px 0;
        }
        .info-box-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        .info-box-icon {
            width: 40px;
            height: 40px;
            border: 2px solid var(--amd-cyan);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 15px;
            font-size: 16pt;
        }
        .info-box-title {
            font-size: 12pt;
            font-weight: 700;
            text-transform: uppercase;
        }

        /* Two Column Layout */
        .two-column {
            display: flex;
            gap: 40px;
        }
        .column {
            flex: 1;
        }
        .column-box {
            background: rgba(0, 200, 170, 0.05);
            border: 1px solid rgba(0, 200, 170, 0.2);
            padding: 25px;
            height: 100%;
        }
        .column-box h4 {
            color: var(--amd-cyan);
            font-size: 11pt;
            font-weight: 700;
            margin-bottom: 20px;
            text-transform: uppercase;
        }
        .column-item {
            margin-bottom: 20px;
        }
        .column-item-number {
            color: var(--amd-cyan);
            font-size: 14pt;
            font-weight: 300;
            margin-bottom: 5px;
        }
        .column-item-title {
            font-weight: 700;
            margin-bottom: 8px;
        }
        .column-item-text {
            font-size: 9pt;
            color: var(--amd-light-gray);
            line-height: 1.5;
        }

        /* Case Study */
        .case-study {
            background: linear-gradient(180deg, #0d1a2d 0%, var(--amd-dark) 100%);
            padding: 40px;
            margin: 30px 0;
            page-break-inside: avoid;
        }
        .case-study-label {
            color: var(--amd-cyan);
            font-size: 10pt;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }
        .case-study-title {
            font-size: 22pt;
            font-weight: 800;
            margin-bottom: 25px;
            text-transform: uppercase;
        }
        .case-study-framing {
            background: rgba(0, 200, 170, 0.1);
            border-left: 4px solid var(--amd-cyan);
            padding: 20px;
            margin-bottom: 25px;
            font-style: italic;
        }
        .case-study-framing strong {
            color: var(--amd-cyan);
            font-style: normal;
        }

        /* Quote Block */
        .quote-block {
            background: rgba(0, 0, 0, 0.3);
            padding: 30px 40px;
            margin: 30px 0;
            position: relative;
        }
        .quote-mark {
            font-size: 72pt;
            color: var(--amd-cyan);
            opacity: 0.3;
            position: absolute;
            top: -10px;
            left: 20px;
            font-family: Georgia, serif;
        }
        .quote-text {
            font-size: 14pt;
            line-height: 1.6;
            font-style: italic;
            margin-bottom: 20px;
            position: relative;
            z-index: 1;
        }
        .quote-author {
            color: var(--amd-cyan);
            font-weight: 700;
            font-style: normal;
        }
        .quote-role {
            color: var(--amd-light-gray);
            font-size: 10pt;
        }

        /* CTA Section */
        .cta-section {
            background: linear-gradient(135deg, #0d1a2d 0%, #0a2a3a 100%);
            padding: 50px;
            text-align: center;
            margin-top: 40px;
        }
        .cta-title {
            font-size: 20pt;
            font-weight: 700;
            margin-bottom: 20px;
        }
        .cta-personalized {
            font-size: 12pt;
            max-width: 600px;
            margin: 0 auto 30px;
            color: var(--amd-light-gray);
        }
        .cta-button {
            display: inline-block;
            background: var(--amd-cyan);
            color: var(--amd-dark);
            padding: 15px 40px;
            font-weight: 700;
            text-transform: uppercase;
            text-decoration: none;
            letter-spacing: 1px;
            transition: all 0.3s;
        }

        /* Footer Navigation */
        .page-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-top: 30px;
            margin-top: 40px;
            border-top: 1px solid rgba(255,255,255,0.1);
            font-size: 8pt;
            color: var(--amd-light-gray);
        }
        .footer-nav {
            display: flex;
            gap: 30px;
        }
        .footer-nav-item {
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .footer-nav-item.active {
            color: var(--amd-cyan);
            font-weight: 700;
        }
        .page-number {
            font-size: 10pt;
        }

        /* Paragraph Styles */
        p {
            margin-bottom: 15px;
            color: #d0d0d8;
        }
        strong {
            color: #ffffff;
        }

        /* List Styles */
        ul {
            margin: 15px 0;
            padding-left: 20px;
        }
        li {
            margin-bottom: 10px;
            color: #d0d0d8;
        }
        li::marker {
            color: var(--amd-cyan);
        }
    </style>
</head>
<body>
    <!-- COVER PAGE -->
    <div class="cover-page">
        <div class="amd-logo">AMD</div>
        <div class="cover-subtitle">From Observers to Leaders</div>
        <h1 class="cover-title">An<br>Enterprise<br>AI Readiness<br>Framework</h1>
        <div class="cover-personalized">
            <div class="cover-personalized-label">Prepared Exclusively For</div>
            <div class="cover-personalized-name">$first_name $last_name</div>
            <div class="cover-personalized-role">$title at $company_name</div>
        </div>
    </div>

    <!-- TABLE OF CONTENTS -->
    <div class="content-page">
        <div class="section-header">
            <h2>Table of Contents</h2>
        </div>
        <div class="stats-grid" style="margin-top: 50px;">
            <div class="stat-item">
                <div class="stat-number">3</div>
                <div class="stat-label"><strong>Redefining the Data Center</strong><br>AI Readiness in the Age of Acceleration</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">4</div>
                <div class="stat-label"><strong>Understanding the Three Stages</strong><br>Data Center Modernization Framework</div>
            </div>
        </div>
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-number">8</div>
                <div class="stat-label"><strong>The Path to Leadership</strong><br>Moving Through the Stages</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">9</div>
                <div class="stat-label"><strong>Modernization in Action</strong><br>Customer Success Snapshots</div>
            </div>
        </div>
        <div class="stats-grid" style="justify-content: flex-start;">
            <div class="stat-item" style="flex: 0 0 auto;">
                <div class="stat-number">15</div>
                <div class="stat-label"><strong>Why AMD</strong><br>Your Strategic Partner for AI Modernization</div>
            </div>
        </div>
    </div>

    <!-- PERSONALIZED INTRO -->
    <div class="content-page">
        <div class="section-header">
            <h2>Redefining the Data Center:<br>AI Readiness in the Age of Acceleration</h2>
        </div>

        <div class="personalized-hook">
            <div class="personalized-hook-label">A Message for $first_name</div>
            <p style="margin: 0; color: white;">$personalized_hook</p>
        </div>

        <p>$intro_section</p>

        <div class="stats-grid" style="margin-top: 50px;">
            <div class="stat-item">
                <div class="stat-number">97<span class="stat-suffix">%</span></div>
                <div class="stat-label">of the data center capacity was occupied as of March 2023 in the top North American markets.</div>
            </div>
        </div>
    </div>

    <!-- THREE STAGES -->
    <div class="content-page">
        <div class="section-header">
            <h2>Understanding the Three Stages of<br>Data Center Modernization</h2>
        </div>

        <p>$three_stages_intro</p>

        <div class="stats-grid" style="margin-top: 40px;">
            <div class="stat-item">
                <div class="stat-number">33<span class="stat-suffix">%</span></div>
                <div class="stat-label">of organizations—<br><strong>data center Leaders</strong>—<br>have fully modernized in the past two years</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">58<span class="stat-suffix">%</span></div>
                <div class="stat-label">of organizations—<br><strong>data center Challengers</strong>—<br>are currently undertaking modernization initiatives</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">9<span class="stat-suffix">%</span></div>
                <div class="stat-label">of organizations—<br><strong>data center Observers</strong>—<br>plan to modernize within the next two years</div>
            </div>
        </div>
    </div>

    <!-- LEADERS SECTION -->
    <div class="content-page">
        <div class="section-header">
            <h2>Data Center Leaders</h2>
        </div>

        <p>$leaders_section</p>

        <div class="two-column" style="margin-top: 30px;">
            <div class="column">
                <div class="column-box">
                    <h4>Advantages for Leaders</h4>
                    <div class="column-item">
                        <div class="column-item-number">01</div>
                        <div class="column-item-title">Efficiencies</div>
                        <div class="column-item-text">They can reduce operational costs by allocating more time and budget to innovation rather than system maintenance.</div>
                    </div>
                    <div class="column-item">
                        <div class="column-item-number">02</div>
                        <div class="column-item-title">Agility and competitive advantage</div>
                        <div class="column-item-text">AI helps widen the gap between the competition through enhanced decision-making, customer experiences, and innovative products.</div>
                    </div>
                </div>
            </div>
            <div class="column">
                <div class="column-box">
                    <h4>Risks</h4>
                    <div class="column-item">
                        <div class="column-item-number">01</div>
                        <div class="column-item-title">Unforeseen costs</div>
                        <div class="column-item-text">The top reason organizations overspend on digital infrastructure is technical debt.</div>
                    </div>
                    <div class="column-item">
                        <div class="column-item-number">02</div>
                        <div class="column-item-title">Integration challenges</div>
                        <div class="column-item-text">Integration is the most significant technical challenge for AI adoption across all organizations.</div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- CHALLENGERS & OBSERVERS -->
    <div class="content-page">
        <div class="section-header">
            <h2>Data Center Challengers</h2>
        </div>

        <p>$challengers_section</p>

        <div style="margin-top: 50px;">
            <div class="section-header">
                <h2>Data Center Observers</h2>
            </div>
            <p>$observers_section</p>
        </div>
    </div>

    <!-- PATH TO LEADERSHIP -->
    <div class="content-page">
        <div class="section-header">
            <h2>The Path to Leadership:<br>Moving Through the Stages</h2>
        </div>

        <p>$path_to_leadership</p>

        <div class="info-box" style="margin-top: 30px;">
            <div class="info-box-header">
                <div class="info-box-icon">⚙</div>
                <div class="info-box-title">Overcoming Barriers</div>
            </div>
            <p style="margin: 0;">As AI technology matures and organizations gain more experience, some early challenges are being solved. But significant barriers to adoption remain, including legacy infrastructure, skill gaps, and data security concerns.</p>
        </div>
    </div>

    <!-- MODERNIZATION MODELS -->
    <div class="content-page">
        <div class="section-header">
            <h2>Modernization Models</h2>
        </div>

        <p>$modernization_models</p>

        <div class="two-column" style="margin-top: 30px;">
            <div class="column">
                <div class="column-box">
                    <h4>Factors Driving In-Place Modernization</h4>
                    <ul>
                        <li>Lower capital expenditures</li>
                        <li>More predictable costs</li>
                        <li>Better control over sensitive data</li>
                        <li>Optimized existing investments</li>
                        <li>Reduced operational risk</li>
                    </ul>
                </div>
            </div>
            <div class="column">
                <div class="column-box">
                    <h4>Factors Driving Refactor-and-Shift</h4>
                    <ul>
                        <li>Accelerated innovation</li>
                        <li>Agile development</li>
                        <li>Faster AI tool integration</li>
                        <li>More efficient scalability</li>
                        <li>Personalized customer experiences</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>

    <!-- CASE STUDY -->
    <div class="content-page">
        <div class="case-study">
            <div class="case-study-label">Case Study</div>
            <h3 class="case-study-title">$case_study_title</h3>

            <div class="case-study-framing">
                <strong>Why this matters for $company_name:</strong><br>
                $case_study_framing
            </div>

            <p><strong>The Challenge:</strong> $case_study_challenge</p>
            <p><strong>The Solution:</strong> $case_study_solution</p>

            <div class="quote-block">
                <div class="quote-mark">"</div>
                <div class="quote-text">$case_study_quote</div>
                <div class="quote-author">$case_study_quote_author</div>
            </div>

            <p><strong>The Result:</strong> $case_study_result</p>
        </div>
    </div>

    <!-- ASSESSMENT QUESTIONS -->
    <div class="content-page">
        <div class="section-header">
            <h2>Where Do You Stand on the<br>Modernization Curve?</h2>
        </div>

        <p>$assessment_questions</p>
    </div>

    <!-- WHY AMD -->
    <div class="content-page">
        <div class="section-header">
            <h2>Why AMD: Your Strategic Partner<br>for Data Center and AI Modernization</h2>
        </div>

        <p>$why_amd</p>

        <div class="cta-section">
            <div class="cta-title">Ready to Accelerate Your AI Journey?</div>
            <div class="cta-personalized">$personalized_cta</div>
            <a href="https://www.amd.com/en/solutions/data-center.html" class="cta-button">Explore AMD AI Solutions →</a>
        </div>

        <div class="page-footer">
            <div style="font-size: 9pt;">
                <p style="margin: 0;">Personalized for <strong>$first_name</strong> at <strong>$company_name</strong></p>
                <p style="margin: 5px 0 0 0;">Generated on $generated_date</p>
            </div>
            <div style="font-size: 8pt; color: var(--amd-light-gray);">
                © 2025 Advanced Micro Devices, Inc.
            </div>
        </div>
    </div>
</body>
</html>'''

    def _get_case_study_for_profile(
        self,
        profile: Dict[str, Any],
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get appropriate case study based on profile industry."""
        industry = user_context.get("industry_input") or profile.get("industry", "technology")
        return get_case_study_for_industry(industry)

    def _render_template(
        self,
        profile: Dict[str, Any],
        intro_hook: str,
        cta: str
    ) -> str:
        """
        Render HTML template with personalization.

        Args:
            profile: Profile data
            intro_hook: Personalized intro
            cta: Personalized CTA

        Returns:
            Rendered HTML string
        """
        template = Template(self._get_ebook_template())

        # Prepare template variables
        variables = {
            "first_name": profile.get("first_name", "Reader"),
            "company_name": profile.get("company_name", "your company"),
            "title": profile.get("title", "Professional"),
            "industry": profile.get("industry", "your industry"),
            "intro_hook": intro_hook,
            "cta": cta,
            "generated_date": datetime.utcnow().strftime("%B %d, %Y"),
        }

        return template.safe_substitute(variables)

    def _get_ebook_template(self) -> str:
        """Get the HTML ebook template."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Personalized Guide</title>
    <style>
        @page {
            size: A4;
            margin: 2cm;
        }

        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px;
        }

        .cover {
            text-align: center;
            padding: 100px 0;
            page-break-after: always;
        }

        .cover h1 {
            font-size: 36px;
            color: #1a365d;
            margin-bottom: 20px;
        }

        .cover .subtitle {
            font-size: 18px;
            color: #4a5568;
            margin-bottom: 40px;
        }

        .personalized-intro {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin: 40px 0;
        }

        .personalized-intro h2 {
            margin-top: 0;
            font-size: 24px;
        }

        .personalized-intro p {
            font-size: 18px;
            margin-bottom: 0;
        }

        .chapter {
            page-break-before: always;
            padding-top: 40px;
        }

        .chapter h2 {
            color: #1a365d;
            font-size: 28px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }

        .chapter p {
            font-size: 14px;
            margin-bottom: 16px;
        }

        .callout {
            background: #f7fafc;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 20px 0;
        }

        .cta-section {
            background: #1a365d;
            color: white;
            padding: 40px;
            border-radius: 10px;
            text-align: center;
            margin-top: 60px;
        }

        .cta-section h2 {
            color: white;
            margin-top: 0;
        }

        .cta-section p {
            font-size: 18px;
        }

        .cta-button {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 15px 40px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: bold;
            margin-top: 20px;
        }

        .footer {
            text-align: center;
            margin-top: 60px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
            font-size: 12px;
            color: #718096;
        }
    </style>
</head>
<body>
    <div class="cover">
        <h1>Strategic Growth Guide</h1>
        <p class="subtitle">Personalized insights for $company_name</p>
        <p>Prepared for: $first_name</p>
        <p>$generated_date</p>
    </div>

    <div class="personalized-intro">
        <h2>A Message For You</h2>
        <p>$intro_hook</p>
    </div>

    <div class="chapter">
        <h2>Chapter 1: Understanding the Landscape</h2>
        <p>The $industry sector is evolving rapidly. Companies like $company_name are at the forefront of this transformation, and leaders in your position as $title play a crucial role in driving success.</p>

        <div class="callout">
            <strong>Key Insight:</strong> Organizations that adapt their strategies early see 40% better outcomes in competitive markets.
        </div>

        <p>In this guide, we'll explore actionable strategies tailored to your role and industry. Each section builds on proven methodologies that have helped similar organizations achieve their goals.</p>
    </div>

    <div class="chapter">
        <h2>Chapter 2: Strategic Frameworks</h2>
        <p>Effective strategy requires a structured approach. For $title roles in $industry, we recommend focusing on three key areas:</p>

        <p><strong>1. Alignment</strong> - Ensure your team's efforts connect directly to organizational objectives.</p>
        <p><strong>2. Measurement</strong> - Establish clear metrics that reflect true progress.</p>
        <p><strong>3. Iteration</strong> - Build feedback loops that enable continuous improvement.</p>

        <div class="callout">
            <strong>Pro Tip:</strong> Start with one area and expand. Trying to transform everything at once often leads to none succeeding.
        </div>
    </div>

    <div class="chapter">
        <h2>Chapter 3: Implementation Roadmap</h2>
        <p>Turning strategy into action requires careful planning. Here's a practical 90-day roadmap:</p>

        <p><strong>Days 1-30:</strong> Assessment and alignment. Understand current state and stakeholder needs.</p>
        <p><strong>Days 31-60:</strong> Pilot and learn. Test approaches with a controlled group.</p>
        <p><strong>Days 61-90:</strong> Scale and optimize. Expand what works, adjust what doesn't.</p>

        <p>Remember, $first_name, the goal isn't perfection—it's progress. Each step forward builds momentum for the next.</p>
    </div>

    <div class="cta-section">
        <h2>Ready to Take the Next Step?</h2>
        <p>$cta</p>
        <a href="#" class="cta-button">Schedule a Conversation</a>
    </div>

    <div class="footer">
        <p>This guide was personalized for $first_name at $company_name</p>
        <p>Generated on $generated_date</p>
    </div>
</body>
</html>
"""

    async def _html_to_pdf(self, html_content: str) -> bytes:
        """
        Convert HTML to PDF.

        Uses weasyprint if available, otherwise uses reportlab with extracted content.

        Args:
            html_content: HTML string to convert

        Returns:
            PDF bytes
        """
        try:
            # Try weasyprint first (preferred for production)
            from weasyprint import HTML
            pdf_bytes = HTML(string=html_content).write_pdf()
            logger.info("Generated PDF using weasyprint")
            return pdf_bytes
        except ImportError:
            logger.warning("weasyprint not available, using reportlab fallback")
        except Exception as e:
            logger.warning(f"weasyprint failed: {e}, using reportlab fallback")

        # Fallback: Generate PDF using reportlab with actual content
        try:
            return self._generate_reportlab_pdf(html_content)
        except Exception as e:
            logger.error(f"reportlab PDF generation failed: {e}")

        # Ultimate fallback: Return a minimal valid PDF
        logger.warning("No PDF library available, returning minimal PDF")
        return self._minimal_pdf()

    def _generate_reportlab_pdf(self, html_content: str) -> bytes:
        """Generate PDF using reportlab with content extracted from HTML."""
        import re
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor, white, black
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, PageBreak,
            Table, TableStyle, FrameBreak
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        # Define colors
        amd_red = HexColor('#ED1C24')
        dark_blue = HexColor('#1a1a2e')

        # Create styles
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=amd_red,
            spaceAfter=12,
            alignment=TA_CENTER
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=dark_blue,
            spaceBefore=20,
            spaceAfter=10
        )

        subheading_style = ParagraphStyle(
            'CustomSubheading',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=amd_red,
            spaceBefore=15,
            spaceAfter=8
        )

        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            spaceAfter=10
        )

        highlight_style = ParagraphStyle(
            'Highlight',
            parent=styles['Normal'],
            fontSize=12,
            leading=18,
            textColor=dark_blue,
            backColor=HexColor('#f5f5f5'),
            borderPadding=10,
            spaceAfter=15
        )

        # Extract content from HTML using regex
        def extract_text(pattern, default=""):
            match = re.search(pattern, html_content, re.DOTALL)
            if match:
                text = match.group(1)
                # Clean HTML tags
                text = re.sub(r'<[^>]+>', ' ', text)
                text = re.sub(r'\s+', ' ', text).strip()
                return text
            return default

        # Extract personalization variables
        first_name = extract_text(r'Prepared for</p>\s*<p[^>]*>([^<]+)</p>', 'Reader')
        company_name = extract_text(r'at ([^<]+)</p>', 'your company')
        personalized_hook = extract_text(r'<h3>A Message For You</h3>\s*<p>([^<]+)</p>', '')

        # Extract sections
        intro_section = extract_text(r'<h2>Redefining the Data Center[^<]*</h2>\s*<p>([^<]+)</p>', '')
        three_stages = extract_text(r'<h2>Understanding the Three Stages[^<]*</h2>\s*<p>([^<]+)</p>', '')
        leaders = extract_text(r'<h3>Data Center Leaders[^<]*</h3>\s*<p>([^<]+)</p>', '')
        challengers = extract_text(r'<h3>Data Center Challengers[^<]*</h3>\s*<p>([^<]+)</p>', '')
        observers = extract_text(r'<h3>Data Center Observers[^<]*</h3>\s*<p>([^<]+)</p>', '')
        path_to_leadership = extract_text(r'<h2>The Path to Leadership[^<]*</h2>\s*<p>([^<]+)</p>', '')
        modernization = extract_text(r'<h2>Modernization Models</h2>\s*<p>([^<]+)</p>', '')
        why_amd = extract_text(r'<h2>Why AMD[^<]*</h2>\s*<p>([^<]+)</p>', '')

        # Extract case study
        case_company = extract_text(r'<h3[^>]*>Customer Success: ([^<]+)</h3>', '')
        case_framing = extract_text(r'<strong>Why this matters[^<]*</strong><br>\s*([^<]+)</div>', '')
        case_challenge = extract_text(r'<strong>The Challenge:</strong>\s*([^<]+)</p>', '')
        case_solution = extract_text(r'<strong>The Solution:</strong>\s*([^<]+)</p>', '')
        case_quote = extract_text(r'"([^"]+)"', '')
        case_result = extract_text(r'<strong>The Result:</strong>\s*([^<]+)</p>', '')

        # Extract CTA
        personalized_cta = extract_text(r'<div class="personalized-cta">\s*([^<]+)</div>', '')

        # Build document
        story = []

        # Cover page
        story.append(Spacer(1, 2*inch))
        story.append(Paragraph("AMD", ParagraphStyle('AMDLogo', parent=title_style, fontSize=28, textColor=amd_red)))
        story.append(Spacer(1, 0.3*inch))
        story.append(Paragraph("FROM OBSERVERS TO<br/>ENTERPRISE AI READINESS", title_style))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph("A Strategic Guide to Data Center Modernization", body_style))
        story.append(Spacer(1, 1*inch))
        story.append(Paragraph(f"<b>Prepared for {first_name}</b>", ParagraphStyle('Personalized', parent=body_style, alignment=TA_CENTER, fontSize=14)))
        if company_name and company_name != 'your company':
            story.append(Paragraph(f"at {company_name}", ParagraphStyle('Company', parent=body_style, alignment=TA_CENTER)))
        story.append(PageBreak())

        # Personalized Hook
        if personalized_hook:
            story.append(Paragraph("A Message For You", subheading_style))
            story.append(Paragraph(personalized_hook, highlight_style))
            story.append(Spacer(1, 0.3*inch))

        # Intro section
        if intro_section:
            story.append(Paragraph("Redefining the Data Center: AI Readiness in the Age of Acceleration", heading_style))
            story.append(Paragraph(intro_section, body_style))
            story.append(Spacer(1, 0.2*inch))

        # Three Stages
        if three_stages:
            story.append(Paragraph("Understanding the Three Stages of Data Center Modernization", heading_style))
            story.append(Paragraph(three_stages, body_style))

        if leaders:
            story.append(Paragraph("Data Center Leaders (26%)", subheading_style))
            story.append(Paragraph(leaders, body_style))

        if challengers:
            story.append(Paragraph("Data Center Challengers (32%)", subheading_style))
            story.append(Paragraph(challengers, body_style))

        if observers:
            story.append(Paragraph("Data Center Observers (42%)", subheading_style))
            story.append(Paragraph(observers, body_style))

        # Path to Leadership
        if path_to_leadership:
            story.append(PageBreak())
            story.append(Paragraph("The Path to Leadership: Moving Through the Stages", heading_style))
            story.append(Paragraph(path_to_leadership, body_style))

        # Modernization Models
        if modernization:
            story.append(Paragraph("Modernization Models", heading_style))
            story.append(Paragraph(modernization, body_style))

        # Case Study
        if case_company:
            story.append(PageBreak())
            story.append(Paragraph(f"Customer Success: {case_company}", heading_style))
            if case_framing:
                story.append(Paragraph(f"<i>Why this matters for {company_name}: {case_framing}</i>", highlight_style))
            if case_challenge:
                story.append(Paragraph(f"<b>The Challenge:</b> {case_challenge}", body_style))
            if case_solution:
                story.append(Paragraph(f"<b>The Solution:</b> {case_solution}", body_style))
            if case_quote:
                story.append(Paragraph(f'<i>"{case_quote}"</i>', ParagraphStyle('Quote', parent=body_style, leftIndent=20, rightIndent=20)))
            if case_result:
                story.append(Paragraph(f"<b>The Result:</b> {case_result}", body_style))

        # Why AMD
        if why_amd:
            story.append(Paragraph("Why AMD: Your Strategic Partner", heading_style))
            story.append(Paragraph(why_amd, body_style))

        # CTA
        story.append(PageBreak())
        story.append(Paragraph("Ready to Take the Next Step?", heading_style))
        if personalized_cta:
            story.append(Paragraph(personalized_cta, highlight_style))
        story.append(Spacer(1, 0.5*inch))
        story.append(Paragraph(f"<b>This guide was personalized for {first_name}</b>", ParagraphStyle('Footer', parent=body_style, alignment=TA_CENTER)))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        logger.info("Generated PDF using reportlab fallback")
        return buffer.read()

    def _minimal_pdf(self) -> bytes:
        """Generate a minimal valid PDF file."""
        # Minimal PDF structure
        pdf = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (Personalized Ebook) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000206 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
300
%%EOF"""
        return pdf

    def _generate_filename(self, email: str, job_id: int) -> str:
        """Generate unique filename for PDF."""
        # Hash email for privacy
        email_hash = hashlib.md5(email.encode()).hexdigest()[:8]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"ebook_{email_hash}_{job_id}_{timestamp}.pdf"

    async def _store_pdf(
        self,
        pdf_bytes: bytes,
        filename: str
    ) -> tuple[str, str]:
        """
        Store PDF in Supabase Storage.

        Args:
            pdf_bytes: PDF content
            filename: Target filename

        Returns:
            Tuple of (storage_path, signed_url)
        """
        if not self.supabase:
            raise ValueError("Supabase client not configured")

        storage_path = f"{self.storage_bucket}/{filename}"

        # Handle mock mode - return mock URL without actual storage
        if getattr(self.supabase, 'mock_mode', False) or self.supabase.client is None:
            logger.info(f"[MOCK] Would store PDF at {storage_path}")
            mock_url = f"https://mock-storage.example.com/{storage_path}?token=mock-signed-url"
            return storage_path, mock_url

        try:
            # Upload to Supabase Storage
            self.supabase.client.storage.from_(self.storage_bucket).upload(
                filename,
                pdf_bytes,
                {"content-type": "application/pdf"}
            )

            # Generate signed URL
            signed_url = self.supabase.client.storage.from_(
                self.storage_bucket
            ).create_signed_url(
                filename,
                PDF_EXPIRY_HOURS * 3600  # Convert to seconds
            )

            return storage_path, signed_url.get("signedURL", "")

        except Exception as e:
            logger.error(f"Failed to store PDF: {e}")
            raise

    async def get_pdf_url(self, storage_path: str) -> Optional[str]:
        """
        Get signed URL for existing PDF.

        Args:
            storage_path: Storage path of the PDF

        Returns:
            Signed URL or None
        """
        if not self.supabase:
            return None

        # Handle mock mode
        if getattr(self.supabase, 'mock_mode', False) or self.supabase.client is None:
            return f"https://mock-storage.example.com/{storage_path}?token=mock-signed-url"

        try:
            filename = storage_path.split("/")[-1]
            signed_url = self.supabase.client.storage.from_(
                self.storage_bucket
            ).create_signed_url(
                filename,
                PDF_EXPIRY_HOURS * 3600
            )
            return signed_url.get("signedURL")
        except Exception as e:
            logger.error(f"Failed to get PDF URL: {e}")
            return None
