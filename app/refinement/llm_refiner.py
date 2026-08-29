"""LLM Refinement Scaffold / Stub Module.

NOTE: Real LLM refinement logic is intentionally NOT implemented yet.
This module provides the toggle scaffolding, placeholder/stub branch, and fallback-on-failure
safety wrapper to ensure zero-risk integration with the extraction pipeline.
"""

from typing import Any
from app.core.logging import get_logger
from app.models.normalized_job import NormalizedJob

logger = get_logger(__name__)


class LLMOutputRefinerStub:
    """Placeholder/stub refinement handler with forced-failure simulation and fallback safety."""

    def __init__(self, force_failure: bool = False):
        self.force_failure = force_failure
        self.invoked = False

    async def refine_jobs(
        self, jobs: list[NormalizedJob]
    ) -> tuple[list[NormalizedJob], int, int]:
        """
        Placeholder/stub refinement function.
        Returns: (jobs, refined_count, failed_count)
        """
        self.invoked = True
        if not jobs:
            return jobs, 0, 0

        try:
            if self.force_failure:
                raise RuntimeError("Simulated forced failure in LLM refinement stub")

            # Stub behavior: mark description_refined with placeholder indicator or preserve
            refined_count = 0
            for job in jobs:
                if job.description:
                    # In this stub phase, we mark description_refined as a copy of description
                    job.description_refined = job.description
                    refined_count += 1

            logger.info(f"LLM refinement stub executed successfully on {refined_count} jobs.")
            return jobs, refined_count, 0

        except Exception as e:
            logger.warning(f"LLM refinement stub encountered an error: {e}. Falling back to original output.")
            # Fallback: preserve original unrefined jobs without modifying or dropping any job
            for job in jobs:
                job.description_refined = None
            return jobs, 0, len(jobs)
