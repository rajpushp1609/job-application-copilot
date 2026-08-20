from __future__ import annotations

import re
from datetime import date
from typing import List, Optional, Tuple

from agents.config import PolicyConfig, load_policy
from agents.models import ApplicationResult, ApplicationStatus, EvaluationResult, JobListing, RoutingDecision


APM_ANALYST_ROLES = {
    "product analyst",
    "associate product manager / apm",
    "associate product manager",
    "apm",
}


class EvaluationAgent:
    def __init__(self, policy: Optional[PolicyConfig] = None):
        self.policy = policy or load_policy()

    def evaluate(self, job: JobListing, today: Optional[date] = None) -> EvaluationResult:
        today = today or date.today()
        reasons: List[str] = []
        role_family = job.role_family.strip()
        role_title = job.role_title.strip()

        # Check if job listing is expired or 404 closed page
        desc_lower = job.description.lower()
        if any(term in desc_lower for term in ("404", "couldn't find anything here", "no longer accepting applications", "job posting has expired", "job closed")):
            job.status = ApplicationStatus.CLOSED
            job.routing = RoutingDecision.SKIP
            return EvaluationResult(
                job=job,
                match_score=0.0,
                routing=RoutingDecision.SKIP,
                is_priority_company=False,
                age_days=self._age_days(job, today),
                current_ctc=0,
                expected_ctc=0,
                reasons=["Listing is closed or returned 404."],
            )

        if not self._matches_target_role(role_family, role_title):
            return EvaluationResult(
                job=job,
                match_score=0.0,
                routing=RoutingDecision.SKIP,
                is_priority_company=False,
                age_days=self._age_days(job, today),
                current_ctc=0,
                expected_ctc=0,
                reasons=["Role does not match target role families."],
            )

        match_score = self._score_match(role_family, role_title, job.description)
        is_priority = self._is_priority_company(job.company)
        age_days = self._age_days(job, today)
        current_ctc, expected_ctc = self._compensation(role_family)
        recommended_project = self._recommended_project(role_family, role_title, job.description)

        routing = RoutingDecision.AUTO_APPLY
        reasons.append("Matching target role — eligible for auto-apply across India, SEA, and International regions.")

        job.match_score = match_score
        job.routing = routing

        return EvaluationResult(
            job=job,
            match_score=match_score,
            routing=routing,
            is_priority_company=is_priority,
            age_days=age_days,
            current_ctc=current_ctc,
            expected_ctc=expected_ctc,
            reasons=reasons,
            recommended_project=recommended_project,
        )

    def evaluate_batch(self, jobs: List[JobListing]) -> List[EvaluationResult]:
        return [self.evaluate(job) for job in jobs]

    def _matches_target_role(self, role_family: str, role_title: str) -> bool:
        haystack = f"{role_family} {role_title}".lower()
        for family in self.policy.role_families:
            tokens = [t.strip().lower() for t in re.split(r"/|,|\(|\)", family) if t.strip()]
            for token in tokens:
                if token and token in haystack:
                    return True
        keywords = [
            "product manager", "product analyst", "product owner", "product ops",
            "product operations", "strategy analyst", "growth analyst", "growth product",
            "apm", "product generalist", "product strategy",
        ]
        return any(k in haystack for k in keywords)

    def _score_match(self, role_family: str, role_title: str, description: str) -> float:
        text = f"{role_family} {role_title} {description}".lower()
        score = 0.40  # Base match score for target role families

        domain_keywords = {
            "fintech": 0.08, "payments": 0.08, "lending": 0.06, "edtech": 0.08,
            "experiment": 0.06, "a/b": 0.06, "analytics": 0.06, "growth": 0.06,
            "ai": 0.05, "0-to-1": 0.05, "0 to 1": 0.05, "consumer": 0.04,
            "saas": 0.04, "product ops": 0.05,
        }
        score += min(0.40, sum(weight for kw, weight in domain_keywords.items() if kw in text))

        location_keywords = ["india", "bengaluru", "bangalore", "remote", "hybrid", "gurugram", "mumbai", "singapore", "thailand", "philippines", "malaysia"]
        if any(k in text for k in location_keywords):
            score += 0.1

        if "senior" in text and "product analyst" in text:
            score += 0.05

        return round(min(score, 1.0), 2)

    def _is_priority_company(self, company: str) -> bool:
        company_lower = company.lower().strip()
        for priority in self.policy.priority_companies:
            if priority.lower() in company_lower or company_lower in priority.lower():
                return True
        return False

    def _age_days(self, job: JobListing, today: date) -> Optional[int]:
        if not job.date_posted:
            return None
        return (today - job.date_posted).days

    def _compensation(self, role_family: str) -> Tuple[float, float]:
        normalized = role_family.lower().strip()
        if normalized in APM_ANALYST_ROLES or "product analyst" in normalized or "apm" in normalized:
            band = self.policy.compensation["apm_analyst"]
        else:
            band = self.policy.compensation["pm_level"]
        return band.current_ctc, band.expected_ctc

    def _recommended_project(self, role_family: str, role_title: str, description: str) -> str:
        text = f"{role_family} {role_title} {description}".lower()
        if any(k in text for k in ("fintech", "payments", "lending", "bank", "wallet", "upi")):
            return self.policy.content_rules.get("fintech_project", "")
        if any(k in text for k in ("edtech", "education", "learning", "teacher", "quiz")):
            return self.policy.content_rules.get("edtech_project", "")
        if any(k in text for k in ("analytics", "strategy", "operations", "ops")):
            return self.policy.content_rules.get("analytics_project", "")
        return self.policy.content_rules.get("edtech_project", "")
