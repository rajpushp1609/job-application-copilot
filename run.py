#!/usr/bin/env python3
"""CLI for job application agents."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from agents.config import ensure_data_dirs
from agents.discovery import DiscoveryAgent
from agents.evaluation import EvaluationAgent
from agents.models import RoutingDecision, load_jobs
from agents.orchestrator import JobApplicationOrchestrator
from agents.tracker import TrackerSync


SAMPLE_JOBS = [
    {
        "company": "Razorpay",
        "role_title": "Product Manager - Payments",
        "role_family": "Product Manager",
        "job_url": "https://example.com/razorpay-pm",
        "portal": "Company careers page",
        "location": "Bengaluru, India",
        "work_arrangement": "Hybrid",
        "date_posted": "2026-07-01",
        "description": "Payments product manager role focused on UPI, lending, and experimentation.",
    },
    {
        "company": "EarlyStage Startup",
        "role_title": "Associate Product Manager",
        "role_family": "Associate Product Manager / APM",
        "job_url": "https://example.com/startup-apm",
        "portal": "LinkedIn",
        "location": "Remote",
        "work_arrangement": "Remote",
        "date_posted": "2026-07-15",
        "description": "0-to-1 APM role in fintech startup.",
    },
    {
        "company": "Generic Corp",
        "role_title": "Product Analyst",
        "role_family": "Product Analyst",
        "job_url": "https://example.com/generic-analyst",
        "portal": "Naukri",
        "location": "Mumbai, India",
        "work_arrangement": "On-site",
        "date_posted": "2026-06-01",
        "description": "Analytics and experimentation for consumer product.",
    },
]


def cmd_seed(args: argparse.Namespace) -> None:
    from agents.models import JobListing
    from datetime import date

    tracker = TrackerSync()
    jobs = []
    for item in SAMPLE_JOBS:
        jobs.append(JobListing.from_dict({
            **item,
            "discovered_at": "2026-07-18T00:00:00",
        }))
    tracker.upsert(jobs)
    print(f"Seeded {len(jobs)} sample jobs into {tracker.jobs_path}")


def cmd_evaluate(args: argparse.Namespace) -> None:
    orchestrator = JobApplicationOrchestrator()
    results = orchestrator.run_evaluate()
    print(f"\nEvaluated {len(results)} jobs:\n")
    for ev in results:
        print(f"[{ev.routing.value}] {ev.job.company} — {ev.job.role_title} ({ev.match_score:.0%})")
        for reason in ev.reasons:
            print(f"  • {reason}")
    csv_path = orchestrator.tracker.export_csv()
    print(f"\nExported tracker CSV: {csv_path}")
    print(f"Summary: {json.dumps(orchestrator.tracker.summary(), indent=2)}")


def cmd_review(args: argparse.Namespace) -> None:
    orchestrator = JobApplicationOrchestrator()
    orchestrator.print_review_queue()


async def cmd_discover(args: argparse.Namespace) -> None:
    orchestrator = JobApplicationOrchestrator(headless=args.headless)
    urls = args.url or []
    sources = ["linkedin"] if args.linkedin else []
    if not sources and not urls:
        print("Provide --linkedin or --url. Use 'seed' command to test without browser.")
        return
    jobs = await orchestrator.run_discover(sources=sources, urls=urls, max_results=args.max)
    print(f"Discovered/upserted {len(jobs)} jobs")
    orchestrator.run_evaluate(jobs)
    orchestrator.print_review_queue()


async def cmd_apply(args: argparse.Namespace) -> None:
    orchestrator = JobApplicationOrchestrator(headless=args.headless, dry_run=not args.live)
    routing = RoutingDecision(args.routing) if args.routing else RoutingDecision.AUTO_APPLY
    results = await orchestrator.run_apply(routing_filter=routing, limit=args.limit, force_apply=args.force, company_filter=args.company)
    print(f"\nProcessed {len(results)} applications:")
    for r in results:
        status = "SUCCESS" if r.success else ("STOPPED" if r.stopped else "FAILED")
        print(f"  [{status}] {r.job.company} — {r.job.role_title}")
        if r.stop_reason:
            print(f"    Stop: {r.stop_reason}")
        if r.screenshot_path:
            print(f"    Screenshot: {r.screenshot_path}")


async def cmd_pipeline(args: argparse.Namespace) -> None:
    orchestrator = JobApplicationOrchestrator(
        headless=args.headless,
        dry_run=not args.live,
        gemini_key=args.gemini_key,
    )
    regions = [r.strip() for r in args.regions.split(",") if r.strip()] if args.regions else ["India", "SEA"]
    result = await orchestrator.run_full_pipeline(
        sources=["linkedin"] if args.linkedin else None,
        urls=args.url,
        max_discover=args.max,
        apply_limit=args.limit,
        dry_run_apply=not args.live,
        parallel=args.parallel,
        regions=regions,
    )
    print(json.dumps(result, indent=2))


async def cmd_copilot(args: argparse.Namespace) -> None:
    orchestrator = JobApplicationOrchestrator(headless=False, dry_run=False, gemini_key=args.gemini_key)
    await orchestrator.run_copilot(
        batch_size=args.batch_size,
        limit=args.limit,
        force_apply=args.force,
        company_filter=args.company,
    )


async def cmd_login(args: argparse.Namespace) -> None:
    discovery = DiscoveryAgent(headless=False)
    portal = (getattr(args, "portal", None) or "google").lower()
    if portal == "linkedin":
        await discovery.login_linkedin()
    elif portal in ("google", "gmail"):
        await discovery.login_google()
    else:
        print(f"Unsupported portal: {portal}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parallel Job Application Agent System for Pushp Raj")
    parser.add_argument("--gemini-key", type=str, help="Gemini API Key for AI answer generation and evaluation")
    sub = parser.add_subparsers(dest="command", required=True)

    copilot = sub.add_parser("copilot", help="Interactive Co-Pilot mode: Batch open parallel tabs, auto-fill forms, review and submit")
    copilot.add_argument("--batch-size", type=int, default=15, help="Number of parallel browser tabs per window (default: 15)")
    copilot.add_argument("--limit", type=int, default=45, help="Total number of jobs to queue for copilot session")
    copilot.add_argument("--company", nargs="+", help="Filter applications to specific company names")
    copilot.add_argument("--force", action="store_true", help="Force copilot filling for all queued active roles")
    copilot.set_defaults(func=cmd_copilot)

    seed = sub.add_parser("seed", help="Load sample jobs for testing evaluation/routing")
    seed.set_defaults(func=cmd_seed)

    evaluate = sub.add_parser("evaluate", help="Evaluate all jobs in tracker and export CSV")
    evaluate.set_defaults(func=cmd_evaluate)

    review = sub.add_parser("review", help="Show jobs held for review")
    review.set_defaults(func=cmd_review)

    discover = sub.add_parser("discover", help="Discover jobs from LinkedIn or URLs")
    discover.add_argument("--linkedin", action="store_true", help="Search LinkedIn (requires login)")
    discover.add_argument("--url", action="append", help="Direct job URL to ingest")
    discover.add_argument("--region", default="India", help="Target region (e.g. India or SEA)")
    discover.add_argument("--max", type=int, default=20)
    discover.add_argument("--headless", action="store_true")
    discover.set_defaults(func=cmd_discover)

    apply_cmd = sub.add_parser("apply", help="Apply to jobs with given routing")
    apply_cmd.add_argument("--routing", default="Auto-apply", choices=[r.value for r in RoutingDecision])
    apply_cmd.add_argument("--company", nargs="+", help="Filter application to specific company names")
    apply_cmd.add_argument("--limit", type=int, default=25)
    apply_cmd.add_argument("--force", action="store_true", help="Force apply to all active roles including held roles")
    apply_cmd.add_argument("--live", action="store_true", help="Actually submit applications (default is dry-run)")
    apply_cmd.add_argument("--headless", action="store_true")
    apply_cmd.set_defaults(func=cmd_apply)

    pipeline = sub.add_parser("pipeline", help="Run discover → evaluate → apply across parallel regional sub-agents")
    pipeline.add_argument("--linkedin", action="store_true")
    pipeline.add_argument("--url", action="append")
    pipeline.add_argument("--max", type=int, default=10)
    pipeline.add_argument("--limit", type=int, default=3)
    pipeline.add_argument("--parallel", action="store_true", default=True, help="Run regional sub-agents in parallel (default: True)")
    pipeline.add_argument("--regions", default="India,SEA", help="Comma separated regions to target (e.g. India,SEA)")
    pipeline.add_argument("--live", action="store_true", help="Submit applications (default is dry-run)")
    pipeline.add_argument("--headless", action="store_true")
    pipeline.set_defaults(func=cmd_pipeline)

    login = sub.add_parser("login", help="Save browser login session")
    login.add_argument("portal", nargs="?", default="google", help="Portal to sign into (linkedin or google)")
    login.set_defaults(func=cmd_login)

    return parser


def main() -> None:
    ensure_data_dirs()
    parser = build_parser()
    args = parser.parse_args()
    func = args.func
    if asyncio.iscoroutinefunction(func):
        asyncio.run(func(args))
    else:
        func(args)


if __name__ == "__main__":
    main()
