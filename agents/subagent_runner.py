from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional, Any

from agents.application import ApplicationAgent
from agents.config import PolicyConfig, ApplicantProfile, load_policy, load_profile
from agents.discovery import DiscoveryAgent
from agents.evaluation import EvaluationAgent
from agents.gemini_engine import GeminiEngine
from agents.models import ApplicationResult, EvaluationResult, JobListing, RoutingDecision, ApplicationStatus

logger = logging.getLogger("regional_subagent")


class RegionalSubAgent:
    """Independent Sub-Agent that manages job discovery, evaluation, and application for a specific region."""

    def __init__(
        self,
        region: str,
        policy: Optional[PolicyConfig] = None,
        profile: Optional[ApplicantProfile] = None,
        headless: bool = True,
        dry_run: bool = True,
        gemini: Optional[GeminiEngine] = None,
    ):
        self.region = region
        self.policy = policy or load_policy()
        self.profile = profile or load_profile()
        self.headless = headless
        self.dry_run = dry_run
        self.gemini = gemini or GeminiEngine()

        self.discovery = DiscoveryAgent(policy=self.policy, headless=headless)
        self.evaluator = EvaluationAgent(policy=self.policy)
        self.application = ApplicationAgent(
            policy=self.policy,
            profile=self.profile,
            headless=headless,
            dry_run=dry_run,
        )

    async def run_pipeline(
        self,
        sources: Optional[List[str]] = None,
        urls: Optional[List[str]] = None,
        max_discover: int = 10,
        apply_limit: int = 3,
    ) -> Dict[str, Any]:
        logger.info(f"[{self.region} Sub-Agent] Starting pipeline execution...")
        discovered_jobs: List[JobListing] = []

        if urls:
            direct_jobs = self.discovery.discover_from_urls(urls, region=self.region)
            discovered_jobs.extend(direct_jobs)

        if sources:
            source_jobs = await self.discovery.discover(sources=sources, max_results=max_discover, region=self.region)
            discovered_jobs.extend(source_jobs)

        for job in discovered_jobs:
            job.region = self.region

        evaluations: List[EvaluationResult] = self.evaluator.evaluate_batch(discovered_jobs)

        apply_targets = [
            (job, ev) for job, ev in zip(discovered_jobs, evaluations)
            if ev.routing == RoutingDecision.AUTO_APPLY and job.status != ApplicationStatus.CLOSED
        ][:apply_limit]

        application_results: List[ApplicationResult] = []
        for job, ev in apply_targets:
            result = await self.application.apply(job, ev)
            application_results.append(result)
            await asyncio.sleep(1)

        logger.info(f"[{self.region} Sub-Agent] Discovered {len(discovered_jobs)} jobs, applied to {len(application_results)}")

        return {
            "region": self.region,
            "jobs": discovered_jobs,
            "evaluations": evaluations,
            "applications": application_results,
        }
