import sys
import json
import csv
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from agents.gemini_engine import GeminiEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend_server")

app = FastAPI(title="Job Application Command Center API")

# Enable CORS for Chrome Extensions and Web Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_header(request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


engine = GeminiEngine()

DATA_DIR = ROOT_DIR / "data"
JOBS_FILE = DATA_DIR / "jobs.json"
CSV_FILE = DATA_DIR / "jobs_export.csv"
QBANK_FILE = DATA_DIR / "question_bank.json"
PROFILE_FILE = ROOT_DIR / "profile.json"


class AnswerRequest(BaseModel):
    question: str
    company: Optional[str] = ""
    role: Optional[str] = ""


class QBankUpdateRequest(BaseModel):
    question: str
    answer: str


class JobApplyRequest(BaseModel):
    url: str
    company: Optional[str] = ""
    role: Optional[str] = ""


@app.get("/api/health")
def health_check():
    return {"status": "ok", "llm_available": engine.is_available}


@app.get("/api/profile")
def get_profile():
    if PROFILE_FILE.exists():
        return json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    return {}


@app.get("/api/jobs")
def get_jobs():
    if JOBS_FILE.exists():
        try:
            return json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


@app.post("/api/generate-answer")
def generate_answer(req: AnswerRequest):
    if not req.question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    q_lower = req.question.strip().lower()
    job_info = {"company": req.company, "role_title": req.role}

    # 1. ALWAYS call Gemini AI Engine for company motivation & open-ended screening questions
    if any(kw in q_lower for kw in ["why", "join", "work", "interested", "describe", "tell us", "built", "looking for", "role", "experience", "how do you"]):
        logger.info(f"Generating Tailored Gemini AI Answer for: '{req.question[:35]}...'")
        ans = engine.generate_screening_answer(question=req.question, job_info=job_info, profile_info={}, policy_info={})
        if ans:
            return {"answer": ans, "source": "Tailored Gemini AI"}

    # 2. Check local Question Bank for factual static questions
    if QBANK_FILE.exists():
        try:
            qbank = json.loads(QBANK_FILE.read_text(encoding="utf-8"))
            for key, val in qbank.items():
                k_clean = key.lower().replace("*", "").strip()
                if k_clean in q_lower or q_lower in k_clean:
                    logger.info(f"Question Bank Match for '{req.question[:30]}...'")
                    return {"answer": val, "source": "Question Bank"}
        except Exception as exc:
            logger.warning(f"QBank search error: {exc}")

    # 3. Fallback Gemini AI execution
    ans = engine.generate_screening_answer(question=req.question, job_info=job_info, profile_info={}, policy_info={})
    if ans:
        return {"answer": ans, "source": "Tailored Gemini AI"}
    
    return {"answer": "I bring 3.5 years of product management experience scaling 0-to-1 products, paywalls, and A/B testing funnels across edtech, fintech, and consumer products.", "source": "Fallback Profile Summary"}


@app.get("/api/qbank")
def get_qbank():
    if QBANK_FILE.exists():
        try:
            return json.loads(QBANK_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


@app.post("/api/question-bank/update")
def update_question_bank(req: QBankUpdateRequest):
    if not req.question or not req.answer:
        raise HTTPException(status_code=400, detail="Question and answer required")

    qbank = {}
    if QBANK_FILE.exists():
        try:
            qbank = json.loads(QBANK_FILE.read_text(encoding="utf-8"))
        except Exception:
            qbank = {}

    qbank[req.question.strip()] = req.answer.strip()
    QBANK_FILE.write_text(json.dumps(qbank, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Updated Question Bank with '{req.question[:30]}...'")
    return {"status": "success", "total_questions": len(qbank)}


def clean_url_base(url_str):
    if not url_str: return ""
    return url_str.split("?")[0].rstrip("/").lower()


def find_matching_job(jobs, req: JobApplyRequest):
    req_url = req.url or ""
    req_base = clean_url_base(req_url)
    req_comp = (req.company or "").strip().lower()
    req_role = (req.role or "").strip().lower()

    # Pass 1: Exact URL or clean URL base match
    if req_url or req_base:
        for job in jobs:
            j_url = job.get("job_url", "")
            j_base = clean_url_base(j_url)
            if (req_url and req_url == j_url) or (req_base and req_base == j_base):
                return job

    # Pass 2: Company AND Role Title match
    if req_comp:
        for job in jobs:
            j_comp = job.get("company", "").strip().lower()
            j_role = job.get("role_title", "").strip().lower()
            if req_comp == j_comp and (not req_role or req_role in j_role or j_role in req_role):
                return job

    return None


@app.post("/api/jobs/apply")
def mark_job_applied(req: JobApplyRequest):
    if not req.url and not req.company:
        raise HTTPException(status_code=400, detail="URL or company required")

    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    jobs = []
    if JOBS_FILE.exists():
        try:
            jobs = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        except Exception:
            jobs = []

    target_job = find_matching_job(jobs, req)
    if target_job:
        target_job["status"] = "Applied"
        target_job["applied_at"] = now_str
    else:
        jobs.append({
            "company": req.company or "Unknown Company",
            "role_title": req.role or "Product Manager",
            "job_url": req.url,
            "status": "Applied",
            "applied_at": now_str
        })

    JOBS_FILE.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")

    # Update CSV export
    try:
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Company", "Role Title", "Job URL", "Status", "Applied At"])
            for j in jobs:
                writer.writerow([j.get("company"), j.get("role_title"), j.get("job_url"), j.get("status"), j.get("applied_at", "")])
    except Exception as exc:
        logger.warning(f"Error updating CSV export: {exc}")

    return {"status": "success", "url": req.url, "company": req.company, "role": req.role, "updated": True}


@app.post("/api/jobs/hold")
def mark_job_hold(req: JobApplyRequest):
    if not req.url and not req.company:
        raise HTTPException(status_code=400, detail="URL or company required")

    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    jobs = []
    if JOBS_FILE.exists():
        try:
            jobs = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        except Exception:
            jobs = []

    target_job = find_matching_job(jobs, req)
    if target_job:
        target_job["status"] = "On Hold"
        target_job["on_hold_at"] = now_str
    else:
        jobs.append({
            "company": req.company or "Unknown Company",
            "role_title": req.role or "Product Manager",
            "job_url": req.url,
            "status": "On Hold",
            "on_hold_at": now_str
        })

    JOBS_FILE.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "success", "url": req.url, "company": req.company, "role": req.role, "status_set": "On Hold"}


@app.post("/api/jobs/unhold")
def unhold_job(req: JobApplyRequest):
    if not req.url and not req.company:
        raise HTTPException(status_code=400, detail="URL or company required")

    jobs = []
    if JOBS_FILE.exists():
        try:
            jobs = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        except Exception:
            jobs = []

    target_job = find_matching_job(jobs, req)
    if target_job:
        target_job["status"] = "Qualified"
        if "on_hold_at" in target_job:
            del target_job["on_hold_at"]

    JOBS_FILE.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"status": "success", "url": req.url, "company": req.company, "role": req.role, "status_set": "Qualified"}


ARCHIVED_JOBS_FILE = DATA_DIR / "archived_jobs.json"


def get_all_archived_jobs():
    if ARCHIVED_JOBS_FILE.exists():
        try:
            return json.loads(ARCHIVED_JOBS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_archived_jobs(jobs):
    ARCHIVED_JOBS_FILE.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")


def generate_curated_job_candidates():
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Comprehensive target pool for PM, APM, Growth PM, Product Analyst & AI PM in India, SEA & Remote
    candidates = [
        {"company": "Razorpay", "role_title": "Product Manager - Growth & Checkout", "location": "Bengaluru, India", "job_url": "https://jobs.lever.co/razorpay/pm-growth-checkout-2026", "match_score": 0.94, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "Swiggy", "role_title": "Associate Product Manager - Instamart", "location": "Bengaluru, India", "job_url": "https://careers.swiggy.com/jobs/apm-instamart-2026", "match_score": 0.91, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "Zepto", "role_title": "Growth Product Manager - Monetization", "location": "Mumbai, India", "job_url": "https://jobs.lever.co/zepto/growth-pm-monetization-2026", "match_score": 0.95, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "CRED", "role_title": "Product Manager - CRED Pay & Rewards", "location": "Bengaluru, India", "job_url": "https://cred.club/careers/pm-pay-rewards-2026", "match_score": 0.93, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "Grab", "role_title": "Product Manager - Driver Growth & Retention", "location": "Singapore", "job_url": "https://sg.linkedin.com/jobs/view/pm-driver-growth-at-grab-4447101", "match_score": 0.92, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "Shopee", "role_title": "Associate Product Manager - Buyer Funnel", "location": "Singapore", "job_url": "https://careers.shopee.sg/jobs/apm-buyer-funnel-2026", "match_score": 0.90, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "Postman", "role_title": "AI Product Manager - Developer Workflows", "location": "Bengaluru, India", "job_url": "https://jobs.ashbyhq.com/postman/ai-pm-developer-workflows", "match_score": 0.96, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "BrowserStack", "role_title": "Product Manager - Automate Platform", "location": "Mumbai, India", "job_url": "https://browserstack.com/careers/pm-automate-2026", "match_score": 0.89, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "Postman", "role_title": "Growth Product Manager - Self-Serve SaaS", "location": "Remote, Global", "job_url": "https://jobs.ashbyhq.com/postman/growth-pm-self-serve", "match_score": 0.94, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "Hasura", "role_title": "Product Manager - GraphQL & AI Engine", "location": "Remote, Global", "job_url": "https://jobs.lever.co/hasura/pm-graphql-ai-2026", "match_score": 0.95, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "PhonePe", "role_title": "Product Analyst - Merchant Acquisition", "location": "Bengaluru, India", "job_url": "https://phonepe.com/careers/product-analyst-merchant", "match_score": 0.87, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "InMobi", "role_title": "Product Manager - AdTech Monetization", "location": "Bengaluru, India", "job_url": "https://jobs.lever.co/inmobi/pm-adtech-monetization-2026", "match_score": 0.91, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "Pine Labs", "role_title": "Product Manager - POS & Subscriptions", "location": "Gurugram / NCR, India", "job_url": "https://pinelabs.com/careers/pm-subscriptions-2026", "match_score": 0.88, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "Atlassian", "role_title": "Associate Product Manager - Jira Cloud", "location": "Bengaluru, India", "job_url": "https://atlassian.com/careers/apm-jira-cloud-2026", "match_score": 0.92, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "Elastic", "role_title": "Product Manager - Search & AI", "location": "Remote, Global", "job_url": "https://elastic.co/careers/pm-search-ai-2026", "match_score": 0.95, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "Datadog", "role_title": "Product Manager - Observability Analytics", "location": "Remote, Global", "job_url": "https://datadoghq.com/careers/pm-observability-2026", "match_score": 0.93, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "Urban Company", "role_title": "Growth PM - Partner Monetization", "location": "Gurugram / NCR, India", "job_url": "https://urbancompany.com/careers/growth-pm-partner", "match_score": 0.90, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "Jio Financial", "role_title": "Product Manager - WealthTech", "location": "Mumbai, India", "job_url": "https://jio.com/careers/pm-wealthtech-2026", "match_score": 0.89, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "MakeMyTrip", "role_title": "Product Manager - Flights & Funnel Growth", "location": "Gurugram / NCR, India", "job_url": "https://makemytrip.com/careers/pm-flights-funnel", "match_score": 0.88, "discovered_at": now_str, "status": "Ready to apply"},
        {"company": "Lenskart", "role_title": "Growth Product Manager - International", "location": "Singapore", "job_url": "https://lenskart.sg/careers/growth-pm-international", "match_score": 0.91, "discovered_at": now_str, "status": "Ready to apply"}
    ]
    return candidates


from agents.job_scraper import discover_fresh_jobs_batch


@app.post("/api/jobs/refresh")
def refresh_jobs_feed():
    from datetime import datetime

    jobs = []
    if JOBS_FILE.exists():
        try:
            jobs = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        except Exception:
            jobs = []

    # Enforce 100 active jobs ceiling rule
    if len(jobs) >= 100:
        return {
            "status": "blocked",
            "message": "Feed is at maximum capacity (100 jobs). Please archive applied jobs first.",
            "total_jobs": len(jobs)
        }

    archived = get_all_archived_jobs()
    batch_limit = min(15, 100 - len(jobs))

    new_added = discover_fresh_jobs_batch(jobs, archived, batch_size=batch_limit)

    if new_added:
        jobs = new_added + jobs  # Newest discovered jobs at top
        JOBS_FILE.write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")

        # Update CSV export
        try:
            with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Company", "Role Title", "Job URL", "Status", "Applied At"])
                for j in jobs:
                    writer.writerow([j.get("company"), j.get("role_title"), j.get("job_url"), j.get("status"), j.get("applied_at", "")])
        except Exception as exc:
            logger.warning(f"Error updating CSV export: {exc}")

    return {
        "status": "success",
        "added_count": len(new_added),
        "total_jobs": len(jobs),
        "message": f"Successfully scraped & added {len(new_added)} fresh qualified roles to feed!" if new_added else "All available candidate jobs are already in database or archived."
    }


@app.post("/api/jobs/archive")
def archive_applied_jobs(batch_size: int = 15):
    jobs = []
    if JOBS_FILE.exists():
        try:
            jobs = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        except Exception:
            jobs = []

    applied_jobs = [j for j in jobs if j.get("status") == "Applied"]
    if not applied_jobs:
        return {
            "status": "warning",
            "archived_count": 0,
            "message": "No applied jobs available to archive."
        }

    to_archive = applied_jobs[:batch_size]
    to_archive_urls = {j.get("job_url") for j in to_archive}

    remaining_jobs = [j for j in jobs if j.get("job_url") not in to_archive_urls]

    archived_list = get_all_archived_jobs()
    archived_list.extend(to_archive)
    save_archived_jobs(archived_list)

    JOBS_FILE.write_text(json.dumps(remaining_jobs, indent=2, ensure_ascii=False), encoding="utf-8")

    # Update CSV export
    try:
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Company", "Role Title", "Job URL", "Status", "Applied At"])
            for j in remaining_jobs:
                writer.writerow([j.get("company"), j.get("role_title"), j.get("job_url"), j.get("status"), j.get("applied_at", "")])
    except Exception as exc:
        logger.warning(f"Error updating CSV export: {exc}")

    return {
        "status": "success",
        "archived_count": len(to_archive),
        "remaining_active": len(remaining_jobs),
        "total_archived": len(archived_list),
        "message": f"Archived {len(to_archive)} applied jobs to data/archived_jobs.json!"
    }


@app.get("/api/jobs/archived")
def get_archived_jobs():
    return get_all_archived_jobs()


@app.post("/api/jobs/hold/rerun")
def rerun_on_hold_jobs():
    from agents.job_scraper import strict_evaluate_job_url

    jobs = []
    if JOBS_FILE.exists():
        try:
            jobs = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        except Exception:
            jobs = []

    hold_jobs = [j for j in jobs if j.get("status") == "On Hold"]
    if not hold_jobs:
        return {
            "status": "warning",
            "total_checked": 0,
            "valid_restored": 0,
            "invalid_dumped": 0,
            "message": "No jobs currently marked On Hold to re-run."
        }

    restored_count = 0
    dumped_count = 0
    remaining_jobs = []

    for j in jobs:
        if j.get("status") == "On Hold":
            url = j.get("job_url", "")
            eval_res = strict_evaluate_job_url(url)
            if eval_res["valid"]:
                # Valid active posting -> Restore to Qualified!
                j["status"] = "Qualified"
                if "on_hold_at" in j:
                    del j["on_hold_at"]
                restored_count += 1
                remaining_jobs.append(j)
            else:
                # Broken / Closed posting -> Dump / Purge from active feed!
                logger.info(f"Dumped invalid On Hold job ({j.get('company')}): {eval_res['reason']}")
                dumped_count += 1
        else:
            remaining_jobs.append(j)

    JOBS_FILE.write_text(json.dumps(remaining_jobs, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "status": "success",
        "total_checked": len(hold_jobs),
        "valid_restored": restored_count,
        "invalid_dumped": dumped_count,
        "message": f"Strict Evaluated {len(hold_jobs)} On Hold jobs: Restored {restored_count} valid postings to Qualified feed, dumped {dumped_count} broken/closed postings."
    }


@app.post("/api/jobs/dump")
def dump_job(req: JobApplyRequest):
    if not req.url and not req.company:
        raise HTTPException(status_code=400, detail="URL or company required")

    jobs = []
    if JOBS_FILE.exists():
        try:
            jobs = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        except Exception:
            jobs = []

    target_job = find_matching_job(jobs, req)
    if target_job:
        remaining_jobs = [j for j in jobs if j != target_job]
        JOBS_FILE.write_text(json.dumps(remaining_jobs, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"status": "success", "dumped": True, "message": f"Dumped job: {req.company} - {req.role}"}

    return {"status": "warning", "dumped": False, "message": "Job not found in active feed"}


class NoCacheStaticFiles(StaticFiles):
    def is_not_modified(self, response_headers, request_headers) -> bool:
        return False

    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


DASHBOARD_DIR = ROOT_DIR / "dashboard"
if DASHBOARD_DIR.exists():
    app.mount("/dashboard", NoCacheStaticFiles(directory=str(DASHBOARD_DIR), html=True), name="dashboard")
    app.mount("/data", NoCacheStaticFiles(directory=str(DATA_DIR)), name="data")

@app.get("/")
def root_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)

