from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "job_application_policy.md"
PROFILE_PATH = ROOT / "profile.json"
DATA_DIR = ROOT / "data"
JOBS_PATH = DATA_DIR / "jobs.json"
BROWSER_STATE_DIR = ROOT / ".browser-state"
RESUME_PATH = ROOT / "output" / "pdf" / "Pushp_Raj_Resume_Revised.pdf"
TRACKER_PATH = ROOT / "outputs" / "job_application_tracker" / "Pushp_Raj_Job_Application_Tracker.xlsx"


@dataclass
class CompensationBand:
    current_ctc: float
    expected_ctc: float


@dataclass
class PolicyConfig:
    role_families: List[str] = field(default_factory=list)
    priority_companies: List[str] = field(default_factory=list)
    auto_apply_age_days: int = 7
    compensation: Dict[str, CompensationBand] = field(default_factory=dict)
    content_rules: Dict[str, str] = field(default_factory=dict)
    stop_triggers: List[str] = field(default_factory=list)


@dataclass
class ApplicantProfile:
    name: str
    email: str
    phone: str
    linkedin: str
    location: str
    notice_period_days: int
    total_experience_years: float
    resume_path: str
    experience_stories: Dict[str, str] = field(default_factory=dict)


def _extract_bullet_items(text: str, section_header: str) -> List[str]:
    pattern = rf"{re.escape(section_header)}\s*\n((?:- .+\n?)+)"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return []
    return [line[2:].strip() for line in match.group(1).splitlines() if line.startswith("- ")]


def load_policy(path: Optional[Path] = None) -> PolicyConfig:
    path = path or POLICY_PATH
    text = path.read_text(encoding="utf-8")

    role_families = _extract_bullet_items(text, "## Target roles")
    priority_companies = []
    priority_match = re.search(r"## Priority-review companies\s*\n\n(.+?)(?:\n##|\Z)", text, re.DOTALL)
    if priority_match:
        priority_companies = [c.strip() for c in re.split(r",\s*|\band\b", priority_match.group(1).strip()) if c.strip()]

    compensation = {
        "apm_analyst": CompensationBand(current_ctc=22, expected_ctc=25),
        "pm_level": CompensationBand(current_ctc=25, expected_ctc=27),
    }

    content_rules = {}
    if "Tailor" in text:
        content_rules["why_join"] = (
            "Connect the company's product, users, growth stage, and role to fintech/edtech experience, "
            "experimentation, AI-enabled products, and 0-to-1 work."
        )
    content_rules["fintech_project"] = "Navi Account Aggregator, pre-purchase conversion, or payment-funnel optimization."
    content_rules["edtech_project"] = "Voyage Math, AI quiz generation, or Interactive Video adoption."
    content_rules["analytics_project"] = "SquadStack customer-acquisition and retention insights."

    stop_triggers = [
        "captcha", "assessment", "coding test", "hackerrank", "codility",
        "unverified factual", "legal question", "verify you are human",
    ]

    return PolicyConfig(
        role_families=role_families,
        priority_companies=priority_companies,
        auto_apply_age_days=7,
        compensation=compensation,
        content_rules=content_rules,
        stop_triggers=stop_triggers,
    )


def load_profile(path: Optional[Path] = None) -> ApplicantProfile:
    path = path or PROFILE_PATH
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return ApplicantProfile(
            name=data["name"],
            email=data["email"],
            phone=data["phone"],
            linkedin=data.get("linkedin", ""),
            location=data.get("location", "Bengaluru, India"),
            notice_period_days=int(data.get("notice_period_days", 30)),
            total_experience_years=float(data.get("total_experience_years", 3.5)),
            resume_path=data.get("resume_path", str(RESUME_PATH)),
            experience_stories=data.get("experience_stories", {}),
        )

    return ApplicantProfile(
        name="Pushp Raj",
        email="rajpushp1609@gmail.com",
        phone="+91 7368089031",
        linkedin="",
        location="Bengaluru, India",
        notice_period_days=30,
        total_experience_years=3.5,
        resume_path=str(RESUME_PATH),
        experience_stories={
            "fintech": "At Navi, I built a large-scale Account Aggregator experience supporting 50K+ daily users and improved pre-purchase conversion by 20-25% through funnel analysis and A/B experiments.",
            "edtech": "At Wayground, I scaled Voyage Math to 5K monthly active teachers within four months and improved AI quiz publish rate from 65% to 75% via experimentation.",
            "analytics": "At SquadStack, I generated acquisition and retention insights contributing to $3M annual revenue and reduced turnaround time by 32%.",
        },
    )


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BROWSER_STATE_DIR.mkdir(parents=True, exist_ok=True)
