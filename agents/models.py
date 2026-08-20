from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json


class RoutingDecision(str, Enum):
    AUTO_APPLY = "Auto-apply"
    HOLD_FOR_REVIEW = "Hold for review"
    STOP = "Stop and request review"
    SKIP = "Skip"


class ApplicationStatus(str, Enum):
    NEW = "New"
    HELD_FOR_REVIEW = "Held for review"
    READY_TO_APPLY = "Ready to apply"
    APPLIED = "Applied"
    NEEDS_FIX = "Failed - Needs Script Fix"
    REFERRAL_REQUESTED = "Referral requested"
    INTERVIEW = "Interview"
    REJECTED = "Rejected"
    OFFER = "Offer"
    CLOSED = "Closed"


@dataclass
class JobListing:
    company: str
    role_title: str
    role_family: str
    job_url: str
    portal: str = "Other"
    location: str = ""
    work_arrangement: str = ""
    region: str = "India"
    date_posted: Optional[date] = None
    description: str = ""
    job_id: str = ""
    match_score: float = 0.0
    routing: RoutingDecision = RoutingDecision.HOLD_FOR_REVIEW
    status: ApplicationStatus = ApplicationStatus.NEW
    notes: str = ""
    discovered_at: Optional[str] = None
    attempt_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["routing"] = self.routing.value
        d["status"] = self.status.value
        d["date_posted"] = self.date_posted.isoformat() if self.date_posted else None
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobListing":
        routing = data.get("routing", RoutingDecision.HOLD_FOR_REVIEW.value)
        status = data.get("status", ApplicationStatus.NEW.value)
        posted = data.get("date_posted")
        return cls(
            company=data.get("company", ""),
            role_title=data.get("role_title", ""),
            role_family=data.get("role_family", ""),
            job_url=data.get("job_url", ""),
            portal=data.get("portal", "Other"),
            location=data.get("location", ""),
            work_arrangement=data.get("work_arrangement", ""),
            region=data.get("region", "India"),
            date_posted=date.fromisoformat(posted) if posted else None,
            description=data.get("description", ""),
            job_id=data.get("job_id", ""),
            match_score=float(data.get("match_score", 0.0)),
            routing=RoutingDecision(routing) if routing in [r.value for r in RoutingDecision] else RoutingDecision.HOLD_FOR_REVIEW,
            status=ApplicationStatus(status) if status in [s.value for s in ApplicationStatus] else ApplicationStatus.NEW,
            notes=data.get("notes", ""),
            discovered_at=data.get("discovered_at"),
            attempt_count=int(data.get("attempt_count", 0)),
        )


@dataclass
class EvaluationResult:
    job: JobListing
    match_score: float
    routing: RoutingDecision
    is_priority_company: bool
    age_days: Optional[int]
    current_ctc: float
    expected_ctc: float
    reasons: List[str] = field(default_factory=list)
    recommended_project: str = ""


@dataclass
class ApplicationResult:
    job: JobListing
    success: bool
    stopped: bool = False
    stop_reason: str = ""
    fields_filled: List[str] = field(default_factory=list)
    screenshot_path: str = ""
    notes: str = ""


def save_jobs(path: str, jobs: List[JobListing]) -> None:
    payload = [j.to_dict() for j in jobs]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_jobs(path: str) -> List[JobListing]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    return [JobListing.from_dict(item) for item in data]
