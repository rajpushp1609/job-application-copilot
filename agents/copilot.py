from __future__ import annotations

import asyncio
import logging
import re
import urllib.request

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from agents.answers import AnswerGenerator
from agents.config import BROWSER_STATE_DIR, ApplicantProfile, PolicyConfig, load_policy, load_profile
from agents.evaluation import EvaluationAgent
from agents.models import ApplicationResult, ApplicationStatus, EvaluationResult, JobListing, RoutingDecision
from agents.application import ApplicationAgent, get_combined_storage_state

logger = logging.getLogger("copilot_agent")


class CopilotBatchResult:
    def __init__(self, job: JobListing, page_index: int, fields_filled: List[str], verified: bool = False, unfilled_fields: Optional[List[str]] = None, error: Optional[str] = None):
        self.job = job
        self.page_index = page_index
        self.fields_filled = fields_filled
        self.verified = verified
        self.unfilled_fields = unfilled_fields or []
        self.error = error


class CopilotAgent:
    """Interactive Co-Pilot Agent: Verifies job URLs, opens them in a single browser window, auto-fills forms, verifies pre-filled data, auto-closes broken tabs, and updates the Question Bank."""

    def __init__(
        self,
        policy: Optional[PolicyConfig] = None,
        profile: Optional[ApplicantProfile] = None,
    ):
        self.policy = policy or load_policy()
        self.profile = profile or load_profile()
        self.answers = AnswerGenerator(self.policy, self.profile)
        self.evaluator = EvaluationAgent(self.policy)

    async def _label_for(self, page, element) -> str:
        try:
            element_id = await element.get_attribute("id")
            if element_id:
                label_el = await page.query_selector(f'label[for="{element_id}"]')
                if label_el:
                    lbl_text = (await label_el.inner_text()).strip()
                    if lbl_text:
                        return lbl_text

            parent_label = await element.evaluate("""
                el => {
                    const container = el.closest('label, .form-group, .field, .form-field, .jobs-easy-apply-form-element, div[class*="field"], div[class*="form"], div[class*="input"], div[class*="container"]');
                    if (container) {
                        const lbl = container.querySelector('label, span, legend, p, h1, h2, h3, h4');
                        if (lbl && lbl !== el) return lbl.innerText;
                    }
                    return '';
                }
            """)
            if parent_label and len(parent_label.strip()) < 400:
                return parent_label.strip()
        except Exception:
            pass
        return ""

    async def verify_url_active(self, url: str) -> Tuple[bool, str]:
        """Pre-flight check to verify that a job posting URL is active and reachable."""
        if not url or not url.startswith("http"):
            return False, "Invalid URL format"
        
        if "linkedin.com" in url:
            return True, "Active LinkedIn Posting"

        def check_http():
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status in (200, 301, 302):
                        return True, "Active (200 OK)"
                    return False, f"HTTP Status {resp.status}"
            except Exception as exc:
                err_str = str(exc).lower()
                if "404" in err_str or "not found" in err_str or "410" in err_str:
                    return False, f"Job URL expired/404: {exc}"
                return True, f"Reachable (notice: {exc})"

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, check_http)

    async def verify_prefilled_info(self, page) -> Tuple[bool, List[str]]:
        """Inspects page elements to verify prefilled inputs and report any remaining unfilled fields."""
        unfilled = []
        try:
            inputs = await page.query_selector_all('input[type="text"], input[type="email"], input[type="tel"], textarea')
            for el in inputs:
                try:
                    if not await el.is_visible():
                        continue
                    val = (await el.input_value() or "").strip()
                    if not val:
                        label = await self._label_for(page, el)
                        unfilled.append(label[:40] if label else "Required Input")
                except Exception:
                    pass
        except Exception as exc:
            logger.warning(f"Verification pass warning: {exc}")
        
        is_verified = (len(unfilled) == 0)
        return is_verified, unfilled

    async def fill_single_tab(self, page, job: JobListing, ev: EvaluationResult, tab_num: int) -> CopilotBatchResult:
        """Navigates to job URL, follows external apply links to target ATS portal, fills form fields, and verifies prefilled state."""
        fields_filled: List[str] = []
        try:
            logger.info(f"Tab [{tab_num}]: Opening {job.company} - {job.role_title}")
            target_url = job.job_url
            if "linkedin.com/jobs/" in target_url:
                job_id_match = re.search(r'(\d{8,})', target_url)
                if job_id_match:
                    target_url = f"https://www.linkedin.com/jobs/view/{job_id_match.group(1)}/"

            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=35000)
            except Exception as goto_err:
                if "ERR_HTTP_RESPONSE_CODE_FAILURE" in str(goto_err) or "999" in str(goto_err):
                    logger.info(f"Tab [{tab_num}]: Retrying LinkedIn navigation...")
                    try:
                        await page.goto("https://www.linkedin.com/", wait_until="domcontentloaded", timeout=12000)
                        await page.wait_for_timeout(1000)
                        await page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
                    except Exception as retry_err:
                        logger.warning(f"Tab [{tab_num}] retry notice: {retry_err}")
                else:
                    await page.close()
                    return CopilotBatchResult(job=job, page_index=tab_num, fields_filled=[], verified=False, error=f"Navigation failed: {goto_err}")

            await page.wait_for_timeout(2000)

            # Strict Page Validity Inspection (Close tab immediately if page is broken / closed / 404)
            page_text = (await page.inner_text("body")).lower()
            page_title = (await page.title()).lower()
            combined_text = f"{page_title} {page_text}"

            broken_triggers = [
                "no longer accepting applications", "job closed", "this posting has expired",
                "job is inactive", "page not working", "page not found", "404", "something went wrong",
                "item not found", "this job is no longer available", "error 404"
            ]
            if any(trigger in combined_text for trigger in broken_triggers):
                logger.info(f"Tab [{tab_num}]: Page broken/closed ({job.company}). Closing tab.")
                try:
                    await page.close()
                except Exception:
                    pass
                return CopilotBatchResult(job=job, page_index=tab_num, fields_filled=[], verified=False, error="Job posting is closed/broken/404 on load")

            # Dismiss blocking sign-in popups or modal overlays
            try:
                dismiss_btns = await page.query_selector_all('button[aria-label="Dismiss"], button[aria-label="Close"], .modal__dismiss, button.contextual-sign-in-modal__modal-dismiss')
                for d_btn in dismiss_btns:
                    try:
                        await d_btn.click()
                    except Exception:
                        pass
            except Exception:
                pass

            # If page is on LinkedIn, click external apply button and navigate page directly to external ATS form!
            active_page = page
            if "linkedin.com" in page.url:
                ext_button = await page.query_selector('.jobs-apply-button, a.jobs-apply-button, button:has-text("Apply"), a:has-text("Apply")')
                if ext_button:
                    href = await ext_button.get_attribute("href")
                    if href and href.startswith("http") and "linkedin.com" not in href:
                        await page.goto(href, wait_until="domcontentloaded", timeout=30000)
                        active_page = page
                    else:
                        try:
                            context = page.context
                            async with context.expect_page(timeout=6000) as page_info:
                                await ext_button.click()
                            new_page = await page_info.value
                            await new_page.wait_for_load_state("domcontentloaded")
                            # Close the LinkedIn tab and switch active tab to target ATS page
                            await page.close()
                            active_page = new_page
                        except Exception:
                            await page.wait_for_timeout(2000)
                            active_page = page

            # Check if page is STILL on LinkedIn job page after attempting navigation
            if "linkedin.com/jobs/view/" in active_page.url:
                logger.info(f"Tab [{tab_num}]: Remaining on LinkedIn view without ATS form. Closing tab.")
                try:
                    if not active_page.is_closed():
                        await active_page.close()
                except Exception:
                    pass
                return CopilotBatchResult(job=job, page_index=tab_num, fields_filled=[], verified=False, error="Could not navigate to external ATS form")

            if not active_page.is_closed():
                await active_page.wait_for_timeout(2000)
                app_agent = ApplicationAgent(policy=self.policy, profile=self.profile, headless=False, dry_run=False)

                # Step 1: Autofill via resume parser if present
                await app_agent._autofill_via_resume(active_page)
                await active_page.wait_for_timeout(2000)

                # Step 2: Country code
                await app_agent._select_country_code(active_page)

                # Step 3: Standard & custom form fields
                filled_common = await app_agent._fill_common_fields(active_page, job)
                fields_filled.extend(filled_common)
                filled_radios = await app_agent._fill_radio_questions(active_page)
                fields_filled.extend(filled_radios)
                filled_selects = await app_agent._fill_select_questions(active_page)
                fields_filled.extend(filled_selects)
                filled_texts = await app_agent._fill_textareas(active_page, job, ev.recommended_project)
                fields_filled.extend(filled_texts)

                # Step 4: Resume upload
                uploaded = await app_agent._upload_resume(active_page)
                if uploaded:
                    fields_filled.append("resume_uploaded")

                # Step 5: Universal QC pass
                filled_qc = await app_agent._universal_qc_pass(active_page, job)
                fields_filled.extend(filled_qc)

            verified, unfilled = await self.verify_prefilled_info(active_page)
            return CopilotBatchResult(job=job, page_index=tab_num, fields_filled=fields_filled, verified=verified, unfilled_fields=unfilled)

        except Exception as exc:
            logger.warning(f"Tab [{tab_num}] prefill error: {exc}")
            try:
                if not page.is_closed():
                    await page.close()
            except Exception:
                pass
            return CopilotBatchResult(job=job, page_index=tab_num, fields_filled=fields_filled, verified=False, error=str(exc))
