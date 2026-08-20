from __future__ import annotations

import asyncio
from datetime import date
from typing import List, Optional, Dict, Any

from agents.application import ApplicationAgent, get_combined_storage_state
from agents.discovery import DiscoveryAgent
from agents.evaluation import EvaluationAgent
from agents.gemini_engine import GeminiEngine
from agents.models import ApplicationResult, ApplicationStatus, EvaluationResult, JobListing, RoutingDecision
from agents.subagent_runner import RegionalSubAgent
from agents.tracker import TrackerSync


class JobApplicationOrchestrator:
    """Main Orchestrator Agent: Runs parallel regional sub-agents and manages central state/tracking."""

    def __init__(
        self,
        headless: bool = False,
        dry_run: bool = False,
        gemini_key: Optional[str] = None,
    ):
        self.headless = headless
        self.dry_run = dry_run
        self.gemini = GeminiEngine(api_key=gemini_key)
        self.discovery = DiscoveryAgent(headless=headless)
        self.evaluator = EvaluationAgent()
        self.application = ApplicationAgent(headless=headless, dry_run=dry_run)
        self.tracker = TrackerSync()

    async def run_parallel_regions(
        self,
        regions: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        urls: Optional[List[str]] = None,
        max_discover: int = 10,
        apply_limit: int = 3,
    ) -> Dict[str, Any]:
        regions = regions or ["India", "SEA"]
        print(f"\n🚀 [Main Orchestrator] Launching {len(regions)} parallel regional sub-agents: {regions}")

        subagents = [
            RegionalSubAgent(
                region=r,
                headless=self.headless,
                dry_run=self.dry_run,
                gemini=self.gemini,
            )
            for r in regions
        ]

        # Execute sub-agents concurrently in parallel
        tasks = [
            sub.run_pipeline(
                sources=sources,
                urls=urls,
                max_discover=max_discover,
                apply_limit=apply_limit,
            )
            for sub in subagents
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs: List[JobListing] = []
        regional_reports = {}

        for res in results:
            if isinstance(res, Exception):
                print(f"❌ Sub-agent failed with error: {res}")
                continue
            region_name = res["region"]
            jobs = res["jobs"]
            all_jobs.extend(jobs)
            regional_reports[region_name] = {
                "discovered": len(jobs),
                "applied": len(res["applications"]),
            }

        # Central deduplication and tracker update
        merged_jobs = self.tracker.upsert(all_jobs)
        self.run_evaluate(merged_jobs)
        csv_path = self.tracker.export_csv()

        print(f"\n✅ [Main Orchestrator] Completed parallel execution across regions.")
        print(f"Central tracker updated: {csv_path}")

        return {
            "parallel_regions": regional_reports,
            "total_jobs_tracked": len(merged_jobs),
            "summary": self.tracker.summary(),
            "csv_export": str(csv_path),
        }

    async def run_discover(
        self,
        sources: Optional[List[str]] = None,
        urls: Optional[List[str]] = None,
        max_results: int = 20,
        region: str = "India",
    ) -> List[JobListing]:
        jobs: List[JobListing] = []

        if urls:
            jobs.extend(self.discovery.discover_from_urls(urls, region=region))

        if sources:
            discovered = await self.discovery.discover(sources=sources, max_results=max_results, region=region)
            jobs.extend(discovered)

        merged = self.tracker.upsert(jobs)
        return merged

    def run_evaluate(self, jobs: Optional[List[JobListing]] = None) -> List[EvaluationResult]:
        jobs = jobs or self.tracker.load()
        results = self.evaluator.evaluate_batch(jobs)
        self.tracker.apply_evaluations(results)
        return results

    async def run_apply(
        self,
        routing_filter: Optional[RoutingDecision] = RoutingDecision.AUTO_APPLY,
        limit: int = 25,
        force_apply: bool = False,
        company_filter: Optional[List[str]] = None,
    ) -> List[ApplicationResult]:
        jobs = self.tracker.load()
        evaluations = self.evaluator.evaluate_batch(jobs)
        self.tracker.apply_evaluations(evaluations)

        targets = []
        for job, ev in zip(jobs, evaluations):
            if company_filter:
                if not any(c.lower() in job.company.lower() for c in company_filter):
                    continue
            if job.attempt_count >= 3 or job.status in (ApplicationStatus.APPLIED, ApplicationStatus.CLOSED):
                continue
            if not force_apply and routing_filter and ev.routing != routing_filter:
                continue
            if ev.routing == RoutingDecision.SKIP:
                continue
            # User Directive: Easy Apply jobs are exported to Google Sheet for manual application.
            # Automated apply runs ONLY on non-Easy Apply ATS roles (Lever, Greenhouse, Ashby, External ATS).
            is_easy_apply_job = "linkedin.com" in job.job_url.lower() and ("f_al=true" in job.job_url.lower() or "easy" in (job.portal or "").lower())
            if is_easy_apply_job and not force_apply and not company_filter:
                continue
            targets.append((job, ev))
            if len(targets) >= limit:
                break

        results = []
        for job, ev in targets:
            job.attempt_count += 1
            try:
                result = await self.application.apply(job, ev, force_apply=force_apply)
            except Exception as exc:
                result = ApplicationResult(
                    job=job,
                    success=False,
                    stopped=True,
                    stop_reason=f"Application error: {exc}",
                )
            results.append(result)
            if result.success:
                job.status = ApplicationStatus.APPLIED
            elif job.attempt_count >= 3:
                job.status = ApplicationStatus.NEEDS_FIX
                job.notes = f"Max attempts (3) reached: {result.stop_reason}"
            self.tracker.upsert([job])
            await asyncio.sleep(2)
        return results

    async def run_copilot(
        self,
        batch_size: int = 10,
        limit: int = 40,
        force_apply: bool = False,
        company_filter: Optional[List[str]] = None,
    ) -> None:
        """Runs interactive Co-Pilot mode: Accumulates EXACTLY batch_size (default 10) valid, open, pre-filled forms in Chrome before user handoff."""
        from playwright.async_api import async_playwright
        from agents.copilot import CopilotAgent
        from agents.config import BROWSER_STATE_DIR

        jobs = self.tracker.load()
        evaluations = self.evaluator.evaluate_batch(jobs)
        self.tracker.apply_evaluations(evaluations)

        targets = []
        for job, ev in zip(jobs, evaluations):
            if company_filter:
                if not any(c.lower() in job.company.lower() for c in company_filter):
                    continue
            # Unconditionally skip already applied jobs and closed jobs
            if job.status in (ApplicationStatus.APPLIED, ApplicationStatus.CLOSED):
                continue
            # Filter out LinkedIn Easy Apply jobs (Easy Apply is tracked in Google Sheet / manual)
            is_easy_apply_job = "linkedin.com" in job.job_url.lower() and ("f_al=true" in job.job_url.lower() or "easy" in (job.portal or "").lower())
            if is_easy_apply_job:
                continue
            if job.attempt_count >= 5:
                continue
            if not force_apply and ev.routing in (RoutingDecision.SKIP, RoutingDecision.STOP):
                continue
            targets.append((job, ev))
            if len(targets) >= limit:
                break

        if not targets:
            print("✨ No jobs currently in queue matching criteria for Co-Pilot apply.")
            return

        print(f"\n🚀 [CO-PILOT MODE] Starting interactive assist session.")
        print(f"Goal: Accumulate EXACTLY {batch_size} active, fully pre-filled job forms open in 1 Chrome window.\n")

        copilot = CopilotAgent(policy=self.policy if hasattr(self, 'policy') else None)
        combined_state = get_combined_storage_state()

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )

            context_kwargs = {
                "locale": "en-US",
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"},
            }
            if combined_state:
                context_kwargs["storage_state"] = combined_state

            context = await browser.new_context(**context_kwargs)
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.navigator.chrome = { runtime: {} };
            """)

            candidate_idx = 0
            total_candidates = len(targets)

            while candidate_idx < total_candidates:
                active_batch_items = []

                print(f"\n================================================================================")
                print(f"🔍 [ACCUMULATING BATCH] Finding & pre-filling {batch_size} active job forms...")
                print(f"================================================================================")

                while candidate_idx < total_candidates and len(active_batch_items) < batch_size:
                    job, ev = targets[candidate_idx]
                    candidate_idx += 1
                    tab_num = len(active_batch_items) + 1

                    # 1. Pre-flight URL check
                    is_active, status_msg = await copilot.verify_url_active(job.job_url)
                    if not is_active:
                        print(f"  [DISCARDED] {job.company} — {job.role_title} ({status_msg}) -> Marking Closed")
                        job.status = ApplicationStatus.CLOSED
                        job.notes = f"URL check: {status_msg}"
                        self.tracker.upsert([job])
                        continue

                    # 2. Open tab in Chrome window & pre-fill
                    # Reuse initial blank tab if present
                    if len(active_batch_items) == 0 and len(context.pages) > 0 and context.pages[0].url in ("about:blank", "chrome://newtab/"):
                        p_tab = context.pages[0]
                    else:
                        p_tab = await context.new_page()

                    res = await copilot.fill_single_tab(p_tab, job, ev, tab_num)

                    if res.error:
                        print(f"  [DISCARDED] {job.company} — {job.role_title} (Broken/Closed: {res.error}) -> Closed Tab")
                        try:
                            if not p_tab.is_closed():
                                await p_tab.close()
                        except Exception:
                            pass
                        job.status = ApplicationStatus.CLOSED
                        job.notes = f"Broken tab: {res.error}"
                        self.tracker.upsert([job])
                        continue

                    # Valid open & pre-filled form!
                    active_batch_items.append((p_tab, job, res))
                    fill_count = len(res.fields_filled)
                    ver_status = "100% Pre-filled" if res.verified else f"{fill_count} fields filled"
                    print(f"  [FORM {len(active_batch_items)}/{batch_size} READY] ✅ {job.company} — {job.role_title} ({ver_status})")
                    await asyncio.sleep(0.5)

                if not active_batch_items:
                    print("⚠️ No remaining active job listings found in queue.")
                    break

                print("\n================================================================================")
                print(f"📋 [CO-PILOT READY] Exactly {len(active_batch_items)} active pre-filled job forms open in Chrome:")
                print("================================================================================")

                batch_map = {}
                for idx, (p_tab, job, res) in enumerate(active_batch_items, start=1):
                    batch_map[idx] = (p_tab, job)
                    fill_count = len(res.fields_filled)
                    ver_status = "✅ Fully Verified (100% pre-filled)" if res.verified else f"⚠️ Needs Attention ({len(res.unfilled_fields)} unfilled)"
                    print(f"  [{idx:2d}] {job.company} — {job.role_title}")
                    print(f"       Status: {ver_status} | {fill_count} fields populated")
                    if res.unfilled_fields:
                        print(f"       Remaining: {', '.join(res.unfilled_fields[:3])}")

                print("================================================================================")
                print(f" 💡 Question Bank Status: New screening answers saved to data/question_bank.json")
                print(f" 🔔 USER ACTION REQUIRED: Please inspect all {len(active_batch_items)} open tabs in Chrome and click 'Submit'!")
                print(" 📥 Enter submitted tab numbers (e.g. 'all', '1,2,5', '1-10') or 'skip':")

                user_input = await asyncio.get_event_loop().run_in_executor(None, input, "Submitted tabs > ")
                user_input = user_input.strip().lower()

                submitted_indices = []
                if user_input in ("all", "a", "*"):
                    submitted_indices = list(batch_map.keys())
                elif user_input and user_input not in ("skip", "none", "n", "s"):
                    # Parse ranges like 1,2,3 or 1-5
                    parts = user_input.split(",")
                    for part in parts:
                        part = part.strip()
                        if "-" in part:
                            try:
                                s, e = map(int, part.split("-"))
                                submitted_indices.extend(range(s, e + 1))
                            except Exception:
                                pass
                        else:
                            try:
                                submitted_indices.append(int(part))
                            except Exception:
                                pass

                # Update tracker for submitted jobs
                applied_jobs = []
                for idx in submitted_indices:
                    if idx in batch_map:
                        _, j = batch_map[idx]
                        j.status = ApplicationStatus.APPLIED
                        applied_jobs.append(j)

                if applied_jobs:
                    self.tracker.upsert(applied_jobs)
                    csv_path = self.tracker.export_csv()
                    print(f"✅ Logged {len(applied_jobs)} jobs as APPLIED! Tracker updated: {csv_path}")
                else:
                    print("ℹ️ No jobs logged as applied in this batch.")

                # Close current batch pages
                for p_tab, job in batch_map.values():
                    try:
                        if not p_tab.is_closed():
                            await p_tab.close()
                    except Exception:
                        pass

                if candidate_idx < total_candidates:
                    cont = await asyncio.get_event_loop().run_in_executor(None, input, "\nPress Enter to start next batch of 10 (or 'q' to quit) > ")
                    if cont.strip().lower() in ("q", "quit", "exit"):
                        break

            await browser.close()
        print("\n🎉 [CO-PILOT MODE] Session completed successfully!")


    async def run_full_pipeline(
        self,
        sources: Optional[List[str]] = None,
        urls: Optional[List[str]] = None,
        max_discover: int = 20,
        apply_limit: int = 3,
        dry_run_apply: bool = True,
        parallel: bool = True,
        regions: Optional[List[str]] = None,
    ) -> dict:
        self.application.dry_run = dry_run_apply
        if parallel:
            return await self.run_parallel_regions(
                regions=regions or ["India", "SEA"],
                sources=sources,
                urls=urls,
                max_discover=max_discover,
                apply_limit=apply_limit,
            )

        discovered = await self.run_discover(sources=sources, urls=urls, max_results=max_discover)
        evaluations = self.run_evaluate(discovered)
        apply_results = await self.run_apply(limit=apply_limit)
        csv_path = self.tracker.export_csv()
        return {
            "discovered": len(discovered),
            "evaluations": [
                {
                    "company": e.job.company,
                    "role": e.job.role_title,
                    "routing": e.routing.value,
                    "match_score": e.match_score,
                    "reasons": e.reasons,
                }
                for e in evaluations
            ],
            "applications": [
                {
                    "company": r.job.company,
                    "success": r.success,
                    "stopped": r.stopped,
                    "stop_reason": r.stop_reason,
                }
                for r in apply_results
            ],
            "summary": self.tracker.summary(),
            "csv_export": str(csv_path),
        }

    def print_review_queue(self) -> None:
        jobs = self.tracker.load()
        evaluations = self.evaluator.evaluate_batch(jobs)
        held = [(j, e) for j, e in zip(jobs, evaluations) if e.routing == RoutingDecision.HOLD_FOR_REVIEW]
        print(f"\n=== Review Queue ({len(held)} jobs) ===")
        for job, ev in held:
            print(f"- {job.company} | {job.role_title}")
            print(f"  URL: {job.job_url}")
            print(f"  Match: {ev.match_score:.0%} | Priority: {'Yes' if ev.is_priority_company else 'No'}")
            for reason in ev.reasons:
                print(f"  • {reason}")
            print()
