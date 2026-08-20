from __future__ import annotations

import difflib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

from agents.config import ApplicantProfile, PolicyConfig, load_policy, load_profile
from agents.gemini_engine import GeminiEngine
from agents.models import JobListing

logger = logging.getLogger("answer_generator")

QUESTION_BANK_PATH = Path(__file__).resolve().parent.parent / "data" / "question_bank.json"


def _clean_human_text(text: str) -> str:
    """Strips markdown syntax (**bold**, *italic*, headers, code blocks, quotes) and AI prefixes."""
    if not text:
        return ""
    # Strip markdown headers/bold/italic/code
    clean = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    clean = re.sub(r'#{1,6}\s*', '', clean)
    clean = re.sub(r'`{1,3}[^`]*`{1,3}', '', clean)
    clean = re.sub(r'^\s*[-*+]\s+', '', clean, flags=re.MULTILINE)
    # Strip AI meta-commentary or prompt headers
    clean = re.sub(r'^(here is a response|screening answer|common screening question|why are you a good fit)[:\s]*', '', clean, flags=re.IGNORECASE)
    return clean.strip().strip('"\'')


class QuestionBank:
    """Persistent question bank with fuzzy string matching."""

    def __init__(self, filepath: Optional[Path] = None):
        self.filepath = filepath or QUESTION_BANK_PATH
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.questions: Dict[str, str] = self._load()

    def _load(self) -> Dict[str, str]:
        if self.filepath.exists():
            try:
                return json.loads(self.filepath.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning(f"Could not load question bank from {self.filepath}: {exc}")
        return {}

    def save(self) -> None:
        try:
            self.filepath.write_text(json.dumps(self.questions, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            logger.warning(f"Could not save question bank to {self.filepath}: {exc}")

    def find_answer(self, question: str, threshold: float = 0.70) -> Optional[str]:
        q_clean = re.sub(r'\s+', ' ', question.lower().strip())
        if not q_clean:
            return None

        # 1. Exact match
        if q_clean in self.questions:
            return self.questions[q_clean]

        # 2. Fuzzy match via SequenceMatcher
        best_match = None
        best_ratio = 0.0

        for stored_q, answer in self.questions.items():
            ratio = difflib.SequenceMatcher(None, q_clean, stored_q).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = answer

        if best_ratio >= threshold and best_match:
            logger.info(f"Fuzzy match found for '{question[:30]}...' with ratio {best_ratio:.2f}")
            return best_match

        return None

    def store_answer(self, question: str, answer: str) -> None:
        q_clean = re.sub(r'\s+', ' ', question.lower().strip())
        if q_clean and answer:
            self.questions[q_clean] = answer
            self.save()


class AnswerGenerator:
    """Generates tailored screening answers using Gemini LLM, fuzzy Question Bank, or policy fallbacks."""

    def __init__(
        self,
        policy: Optional[PolicyConfig] = None,
        profile: Optional[ApplicantProfile] = None,
        gemini: Optional[GeminiEngine] = None,
    ):
        self.policy = policy or load_policy()
        self.profile = profile or load_profile()
        self.gemini = gemini or GeminiEngine()
        self.q_bank = QuestionBank()

    def get_ctc_answers(self, job: JobListing, hint: str) -> Dict[str, str]:
        """Resolves Current & Expected CTC according to LPA vs absolute integer clause and SEA currency conversion."""
        h = hint.lower()
        is_lpa = any(k in h for k in ("lpa", "lakh", "lakhs", "lacs", "in lpa"))

        region = (getattr(job, "region", "") or "").lower()
        loc = (getattr(job, "location", "") or "").lower()

        # SEA regional conversions (Base INR: 25L current / 27L expected)
        if any(c in region or c in loc for c in ("singapore", "sg")):
            curr_val, exp_val = 40000, 43000
        elif any(c in region or c in loc for c in ("malaysia", "myr", "my")):
            curr_val, exp_val = 135000, 146000
        elif any(c in region or c in loc for c in ("philippines", "php", "ph")):
            curr_val, exp_val = 1700000, 1830000
        elif any(c in region or c in loc for c in ("thailand", "thb", "th")):
            curr_val, exp_val = 1080000, 1160000
        elif any(c in region or c in loc for c in ("indonesia", "idr", "id")):
            curr_val, exp_val = 460000000, 500000000
        elif any(c in region or c in loc for c in ("vietnam", "vnd", "vn")):
            curr_val, exp_val = 750000000, 810000000
        else: # India / Default INR
            if is_lpa:
                curr_val, exp_val = 25, 27
            else:
                curr_val, exp_val = 2500000, 2700000

        return {
            "current_ctc": str(curr_val),
            "expected_ctc": str(exp_val),
        }

    def why_join(self, job: JobListing) -> str:
        if self.gemini.is_available:
            ai_ans = self.gemini.generate_screening_answer(
                question=f"Why do you want to join {job.company} as a {job.role_title}?",
                job_info={"company": job.company, "role_title": job.role_title, "region": getattr(job, "region", "India"), "description": job.description},
                profile_info={"name": self.profile.name, "stories": self.profile.experience_stories},
                policy_info={"rules": self.policy.content_rules},
            )
            if ai_ans:
                return _clean_human_text(ai_ans)

        company = job.company
        role = job.role_title
        ans = (
            f"I am excited about {company} because the {role} role sits at the intersection of product impact "
            f"and user-centric problem solving — areas where I have delivered measurable outcomes in fintech and edtech. "
            f"At Wayground, I led 0-to-1 product work (Voyage Math) and AI-enabled workflows; at Navi, I improved "
            f"conversion and payment success through analytics-led experimentation. I want to bring that same rigor "
            f"to {company}'s product, users, and growth stage."
        )
        return _clean_human_text(ans)

    def impactful_project(self, job: JobListing, project_hint: str = "") -> str:
        if self.gemini.is_available:
            ai_ans = self.gemini.generate_screening_answer(
                question="Describe a recent high-impact project or accomplishment relevant to this role.",
                job_info={"company": job.company, "role_title": job.role_title, "region": getattr(job, "region", "India"), "description": f"{job.description} {project_hint}"},
                profile_info={"name": self.profile.name, "stories": self.profile.experience_stories},
                policy_info={"rules": self.policy.content_rules},
            )
            if ai_ans:
                return _clean_human_text(ai_ans)

        text = f"{job.role_title} {job.description} {project_hint}".lower()
        if any(k in text for k in ("fintech", "payments", "lending", "bank")):
            story = self.profile.experience_stories.get("fintech", "")
        elif any(k in text for k in ("edtech", "education", "ai", "consumer")):
            story = self.profile.experience_stories.get("edtech", "")
        else:
            story = self.profile.experience_stories.get("analytics", "")

        ans = (
            f"At my previous role, I took ownership of a critical user journey aligned with this domain. "
            f"{story} This delivered measurable gains in adoption, conversion, and operational efficiency."
        )
        return _clean_human_text(ans)

    def common_fields(self) -> dict:
        name_parts = self.profile.name.split()
        return {
            "full_name": self.profile.name,
            "first_name": name_parts[0],
            "last_name": name_parts[-1] if len(name_parts) > 1 else "",
            "email": self.profile.email,
            "phone": self.profile.phone,
            "location": self.profile.location,
            "notice_period_days": str(self.profile.notice_period_days),
            "total_experience_years": str(self.profile.total_experience_years),
            "linkedin": self.profile.linkedin,
        }

    def answer_for_question(self, question: str, job: JobListing, evaluation_hint: str = "") -> Optional[str]:
        if not question or not question.strip():
            return None

        # 1. Check persistent question bank with fuzzy matching
        fuzzy_ans = self.q_bank.find_answer(question)
        if fuzzy_ans:
            return _clean_human_text(fuzzy_ans)

        q = question.lower()

        # 2. Known pattern resolution
        if any(k in q for k in ("why", "join", "interested", "motivat")):
            ans = self.why_join(job)
            self.q_bank.store_answer(question, ans)
            return ans

        if any(k in q for k in ("project", "impact", "achievement", "proud")):
            ans = self.impactful_project(job, evaluation_hint)
            self.q_bank.store_answer(question, ans)
            return ans

        if any(k in q for k in ("retention", "engagement", "churn")):
            return "At Wayground, I focused on reducing activation friction for teachers during onboarding. By analyzing cohort drop-offs in Amplitude, we introduced guided AI prompt templates which improved weekly active teacher retention."

        if any(k in q for k in ("prioritize", "roadmap", "feature selection")):
            return "I evaluate roadmap items based on user impact versus engineering effort. I combine quantitative funnel analytics with direct customer feedback to prioritize high-leverage growth experiments first."

        if any(k in q for k in ("collaborate", "engineering", "designer", "stakeholder")):
            return "I write clear PRDs with defined user flows and acceptance criteria, while prototyping early concepts using Claude Code. I run short daily syncs to remove blockers and keep alignment tight."

        if any(k in q for k in ("ai tool", "ai tools", "ai workflow", "ai product", "ai experience", "claude", "chatgpt", "generative ai", "llm")):
            ans = "I use Claude Code, ChatGPT, Cursor, and Gemini daily. At Wayground, I used Claude Code for vibe-coding 0-to-1 feature prototypes, drafting PRDs, and testing AI quiz generation workflows."
            self.q_bank.store_answer(question, ans)
            return ans

        if any(k in q for k in ("0-to-1", "0 to 1", "from scratch", "build new")):
            return "At Wayground, I led the 0-to-1 development of Voyage Math. I defined the product specs, ran user interviews with teachers, and launched the initial version, scaling it to 5,000 active teachers in four months."

        if any(k in q for k in ("paywall", "subscription", "iap", "checkout", "monetiz")):
            return "Yes. At Wayground, I built the subscription paywall and checkout flow for our premium teacher tier. We gated advanced AI quiz creation and higher student seat limits behind a tiered paywall, integrating payment gateways to enable self-serve upgrades."

        if any(k in q for k in ("amplitude", "mixpanel", "clevertap", "firebase", "sql")):
            return "I regularly use SQL, Amplitude, and Firebase for product analytics, funnel tracking, and user behavior segmentation."

        if any(k in q for k in ("a/b test", "ab test", "experiment")):
            return "Yes. At Navi, I led A/B testing for the Account Aggregator onboarding funnel to reduce friction. By testing simplified consent steps against the control, we improved conversion by over 20%."

        if any(k in q for k in ("something you built", "link to", "portfolio link", "github")):
            return "https://www.linkedin.com/in/pushpraj-6a4a4916a"

        if any(k in q for k in ("product management according to you", "what is pm", "definition of pm")):
            return "Product management is defining customer problems, establishing data-driven metrics, and executing cross-functional solutions that balance user impact with business growth."

        if any(k in q for k in ("how soon", "when can you join", "start date")):
            return "30 days"

        if any(k in q for k in ("last comp", "current comp", "previous salary")):
            return "2500000"

        if "notice" in q:
            return str(self.profile.notice_period_days)
        if ("experience" in q or "exp" in q or "years" in q) and not any(k in q for k in ("ai", "tool", "software", "tech")):
            return str(self.profile.total_experience_years)
        if "salary" in q or "ctc" in q or "compensation" in q:
            if "expected" in q:
                return "2700000"
            return "2500000"
        if "visa" in q or "sponsor" in q or "bot" in q or "robot" in q:
            return "No"
        if "authorized" in q or "eligible" in q or "work in" in q or "relocate" in q:
            return "Yes"
        if "education" in q or "degree" in q or "qualification" in q or "college" in q:
            return "Bachelor of Technology (B.Tech) - IIT Kharagpur"

        # 3. Call Gemini LLM if available
        if self.gemini.is_available:
            try:
                ai_ans = self.gemini.generate_screening_answer(
                    question=question,
                    job_info={"company": job.company, "role_title": job.role_title, "description": f"{job.description} {evaluation_hint}"},
                    profile_info={"name": self.profile.name, "skills": getattr(self.profile, "skills_summary", ""), "stories": self.profile.experience_stories},
                    policy_info={"rules": self.policy.content_rules},
                )
                if ai_ans:
                    clean_ans = _clean_human_text(ai_ans)
                    self.q_bank.store_answer(question, clean_ans)
                    return clean_ans
            except Exception as exc:
                logger.warning(f"Gemini answer generation failed: {exc}")

        # 4. Reliable default template fallback
        default_ans = (
            f"I have {self.profile.total_experience_years} years of hands-on product management experience "
            f"driving end-to-end product strategy, user growth, and data analytics across high-scale products."
        )
        self.q_bank.store_answer(question, default_ans)
        return default_ans
