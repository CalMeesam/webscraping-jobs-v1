"""LLM Output Refiner module for post-processing job descriptions."""

import asyncio
import os
import re
from typing import Any
from app.core.logging import get_logger
from app.models.normalized_job import NormalizedJob

logger = get_logger(__name__)

MAX_LLM_REFINE_JOBS = int(os.getenv("MAX_LLM_REFINE_JOBS", "5"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "3.0"))

REFINEMENT_SYSTEM_PROMPT = """You are a precise text-cleaning post-processor for job descriptions.
Your ONLY task is to clean up formatting artifacts in already-extracted job description text.

STRICT RULES:
1. Strip residual HTML tags, HTML entities (e.g., &amp;, &nbsp;, &gt;, &lt;), and raw markup remnants.
2. Clean garbled whitespace, repeated blank lines, awkward line wraps, or mid-word spaces caused by HTML parsing.
3. DO NOT change job titles, locations, requirements, qualifications, or company details.
4. DO NOT summarize, paraphrase, or omit real sentences or paragraphs.
5. DO NOT invent or add any new information not present in the input text.
6. Return ONLY the cleaned text string. Do not include markdown code fence blocks or introductory remarks.
"""


class LLMOutputRefiner:
    """Post-processing LLM output refiner for normalized job descriptions."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        self._client = None

        if self.api_key:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize AsyncOpenAI client for refinement: {e}")

    async def _clean_single_description(self, raw_description: str) -> str:
        """Call LLM to refine a single description string with timeout."""
        if not self._client or not raw_description or not raw_description.strip():
            return raw_description

        try:
            response = await asyncio.wait_for(
                self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": REFINEMENT_SYSTEM_PROMPT},
                        {"role": "user", "content": raw_description[:4000]},  # Bounded input length
                    ],
                    temperature=0.0,
                    max_tokens=1500,
                ),
                timeout=LLM_TIMEOUT_SECONDS,
            )
            cleaned_text = response.choices[0].message.content.strip()
            # Remove any markdown code fences if model accidentally wrapped output
            cleaned_text = re.sub(r"^```[a-z]*\n?", "", cleaned_text)
            cleaned_text = re.sub(r"\n?```$", "", cleaned_text)
            return cleaned_text.strip()
        except Exception as err:
            logger.warning(f"LLM refinement API call failed or timed out: {err}")
            raise err

    def fallback_regex_clean(self, text: str) -> str:
        """Deterministic regex fallback cleaning when LLM API is disabled or unavailable."""
        if not text:
            return text
        # Strip residual HTML tags
        clean = re.sub(r"<[^>]+>", " ", text)
        # Unescape common HTML entities
        clean = clean.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
        # Normalize double/multiple spaces
        clean = re.sub(r"[ \t]+", " ", clean)
        # Normalize excessive newlines
        clean = re.sub(r"\n{3,}", "\n\n", clean)
        return clean.strip()

    async def refine_jobs(
        self, jobs: list[NormalizedJob]
    ) -> tuple[list[NormalizedJob], int, int]:
        """
        Refine description field of up to MAX_LLM_REFINE_JOBS normalized jobs.
        Returns: (jobs, refined_count, failed_count)
        """
        if not jobs:
            return jobs, 0, 0

        refined_count = 0
        failed_count = 0

        # Bound jobs to refine to MAX_LLM_REFINE_JOBS
        jobs_to_process = jobs[:MAX_LLM_REFINE_JOBS]

        for job in jobs_to_process:
            if not job.description or not job.description.strip():
                continue

            if self._client:
                try:
                    refined_text = await self._clean_single_description(job.description)
                    job.description_refined = refined_text
                    refined_count += 1
                except Exception as e:
                    logger.warning(f"LLM refinement failed for job title='{job.title}': {e}. Falling back.")
                    # Soft degradation fallback using deterministic regex clean
                    job.description_refined = self.fallback_regex_clean(job.description)
                    failed_count += 1
            else:
                # API Key not provided: perform soft regex cleanup fallback as description_refined
                job.description_refined = self.fallback_regex_clean(job.description)
                refined_count += 1

        return jobs, refined_count, failed_count
