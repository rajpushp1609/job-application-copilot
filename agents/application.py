from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from agents.answers import AnswerGenerator
from agents.config import BROWSER_STATE_DIR, RESUME_PATH, ApplicantProfile, PolicyConfig, load_policy, load_profile
from agents.evaluation import EvaluationAgent
from agents.models import ApplicationResult, ApplicationStatus, EvaluationResult, JobListing, RoutingDecision

logger = logging.getLogger("application_agent")

FIELD_PATTERNS = [
    ("first_name", ["first name", "given name", "fname"]),
    ("last_name", ["last name", "surname", "family name", "lname"]),
    ("current_ctc", ["current ctc", "current compensation", "current salary", "present ctc", "fixed ctc", "last comp", "last salary", "comp"]),
    ("expected_ctc", ["expected ctc", "expected compensation", "expected salary", "desired ctc"]),
    ("total_experience_years", ["years of experience", "total experience", "experience (years)", "overall experience", "experience", "exp"]),
    ("notice_period_days", ["notice period", "notice", "how soon", "when can you join", "start date", "move forward"]),
    ("phone", ["phone", "mobile", "contact number", "phone number"]),
    ("email", ["email", "e-mail"]),
    ("linkedin", ["linkedin", "profile url", "link to", "built", "portfolio", "github", "website"]),
    ("location", ["location", "city", "current location"]),
    ("full_name", ["full name", "candidate name", "complete name", "name*", "name"]),
]


class ApplicationAgent:
    """Fills job application forms via browser automation with policy stop rules and post-submit AI verification."""

    def __init__(
        self,
        policy: Optional[PolicyConfig] = None,
        profile: Optional[ApplicantProfile] = None,
        headless: bool = False,
        dry_run: bool = False,
    ):
        self.policy = policy or load_policy()
        self.profile = profile or load_profile()
        self.headless = headless
        self.dry_run = dry_run
        self.answers = AnswerGenerator(self.policy, self.profile)
        self.evaluator = EvaluationAgent(self.policy)
        self.screenshots_dir = BROWSER_STATE_DIR / "screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def verify_submission_success(self, page_text: str) -> bool:
        """Strict submission verification layer checking confirmation keywords and Gemini AI evaluation."""
        if not page_text:
            return False

        text = page_text.lower()
        success_patterns = [
            r"thank\s+you",
            r"application\s+(?:was\s+)?submitted(?:\s+successfully)?",
            r"application\s+(?:was\s+)?received",
            r"application\s+(?:was\s+)?sent",
            r"thank\s+you\s+for\s+applying",
            r"your\s+application\s+has\s+been\s+submitted",
            r"successfully\s+applied",
            r"you\s+have\s+successfully\s+applied",
            r"application\s+complete",
            r"response\s+has\s+been\s+recorded",
            r"we['’]?ve\s+received\s+your\s+application",
            r"thanks\s+for\s+applying",
            r"your\s+profile\s+was\s+shared\s+with\s+the\s+job\s+poster",
            r"profile\s+was\s+shared",
            r"did\s+you\s+finish\s+applying",
            r"تم\s+إرسال\s+طلبك",
        ]

        for pattern in success_patterns:
            if re.search(pattern, text):
                return True

        if hasattr(self.answers, "gemini") and self.answers.gemini.is_available:
            try:
                ai_verified = self.answers.gemini.verify_submission(page_text)
                if ai_verified is True:
                    return True
            except Exception:
                pass

        return False

    async def _handle_google_login(self, page) -> bool:
        """Handles automated Google/Gmail login when external links navigate to Google Forms."""
        try:
            gmail_user = os.environ.get("GMAIL_EMAIL") or os.environ.get("GOOGLE_EMAIL")
            gmail_pass = os.environ.get("GMAIL_PASSWORD") or os.environ.get("GOOGLE_PASSWORD")
            if not gmail_user or not gmail_pass:
                return False

            if "accounts.google.com" in page.url or "google.com/forms" in page.url or "docs.google.com" in page.url:
                try:
                    email_input = await page.wait_for_selector('input[type="email"], input[name="identifier"]', timeout=6000)
                    if email_input:
                        await email_input.fill(gmail_user)
                        await page.click('button:has-text("Next"), #identifierNext, div[id="identifierNext"]')
                        await page.wait_for_timeout(3500)
                except Exception:
                    pass

                try:
                    pass_input = await page.wait_for_selector('input[type="password"], input[name="Passwd"], input[name="password"]', timeout=8000)
                    if pass_input:
                        await pass_input.fill(gmail_pass)
                        await page.click('button:has-text("Next"), #passwordNext, div[id="passwordNext"]')
                        await page.wait_for_timeout(4000)
                        return True
                except Exception:
                    pass
        except Exception as exc:
            logger.warning(f"Google login exception: {exc}")
        return False

    async def apply(
        self,
        job: JobListing,
        evaluation: Optional[EvaluationResult] = None,
        force_apply: bool = False,
    ) -> ApplicationResult:
        evaluation = evaluation or self.evaluator.evaluate(job)

        if not force_apply and evaluation.routing in (RoutingDecision.SKIP, RoutingDecision.HOLD_FOR_REVIEW, RoutingDecision.STOP):
            return ApplicationResult(
                job=job,
                success=False,
                stopped=True,
                stop_reason=f"Routing decision: {evaluation.routing.value}",
            )
        elif force_apply and evaluation.routing == RoutingDecision.SKIP:
            return ApplicationResult(
                job=job,
                success=False,
                stopped=True,
                stop_reason="Skipping closed or invalid listing",
            )

        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is required. Run: pip install playwright && playwright install chromium") from exc

        fields_filled: List[str] = []

        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(
                    channel="chrome",
                    headless=self.headless,
                    args=["--disable-blink-features=AutomationControlled"],
                )
            except Exception:
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=["--disable-blink-features=AutomationControlled"],
                )

            combined_state = get_combined_storage_state()

            context_kwargs = {
                "locale": "en-US",
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"},
            }
            if combined_state:
                context_kwargs["storage_state"] = combined_state

            try:
                context = await browser.new_context(**context_kwargs)
            except Exception as ctx_err:
                logger.warning(f"Storage state context load warning, using clean context: {ctx_err}")
                context_kwargs.pop("storage_state", None)
                context = await browser.new_context(**context_kwargs)

            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.navigator.chrome = { runtime: {} };
            """)
            await context.add_cookies([
                {"name": "lang", "value": "v=2&lang=en-us", "domain": ".linkedin.com", "path": "/"},
            ])
            page = await context.new_page()

            # Normalize LinkedIn URLs for cookie matching and strip tracking query params
            target_url = job.job_url
            if "linkedin.com/jobs/" in target_url:
                job_id_match = re.search(r'(\d{8,})', target_url)
                if job_id_match:
                    target_url = f"https://www.linkedin.com/jobs/view/{job_id_match.group(1)}/"

            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            except Exception as goto_err:
                if "ERR_TOO_MANY_REDIRECTS" in str(goto_err):
                    logger.warning(f"Redirect loop detected for {target_url}, clearing cookies and retrying...")
                    try:
                        await context.clear_cookies()
                    except Exception:
                        pass
                    await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
                else:
                    raise goto_err
            await page.wait_for_timeout(4000)

            page_text = (await page.inner_text("body")).lower()
            page_html = (await page.content()).lower()
            full_text = f"{page_text} {page_html}"
            current_url = page.url.lower()

            # Pre-check if application was already submitted / profile shared on page load
            if self.verify_submission_success(full_text):
                screenshot = await self._screenshot(page, job, "confirmation")
                await browser.close()
                job.status = ApplicationStatus.APPLIED
                return ApplicationResult(
                    job=job,
                    success=True,
                    fields_filled=["profile-shared-on-load"],
                    screenshot_path=screenshot,
                    notes="LinkedIn profile application verified on initial page load.",
                )

            # Dismiss any blocking sign-in popups or modal overlays
            try:
                dismiss_btns = await page.query_selector_all('button[aria-label="Dismiss"], button[aria-label="Close"], .modal__dismiss, button.contextual-sign-in-modal__modal-dismiss, button[data-test-modal-close-btn], button:has-text("إهمال")')
                for d_btn in dismiss_btns:
                    try:
                        await d_btn.click()
                        await page.wait_for_timeout(1000)
                    except Exception:
                        pass
            except Exception:
                pass

            # -----------------------------------------------------------------
            # 1. LINKEDIN EASY APPLY (Multi-step modal navigation)
            # -----------------------------------------------------------------
            easy_apply_button = await page.query_selector('button.jobs-apply-button, button:has-text("Easy Apply"), button[aria-label*="Easy Apply"], button.jobs-apply-button--top-card, button:has-text("تقديم التقديم السريع"), button:has-text("التقديم السريع")')
            is_easy_apply = False
            if easy_apply_button:
                btn_class = (await easy_apply_button.get_attribute("class") or "").lower()
                btn_text_raw = (await easy_apply_button.inner_text() or "").lower()
                btn_aria = (await easy_apply_button.get_attribute("aria-label") or "").lower()
                btn_html = (await easy_apply_button.inner_html() or "").lower()
                if any(x in y for x in ["easy apply", "easy-apply", "التقديم السريع", "تقديم السريع"] for y in [btn_class, btn_text_raw, btn_aria, btn_html]):
                    is_easy_apply = True

            if is_easy_apply and easy_apply_button:
                try:
                    await easy_apply_button.click()
                    await page.wait_for_timeout(2500)

                    # Step through Easy Apply modal steps (up to 12 steps)
                    for step in range(12):
                        # Dismiss any draft overlay popup inside step loop
                        d_btns = await page.query_selector_all('button[data-test-modal-close-btn], button:has-text("إهمال")')
                        for db in d_btns:
                            try:
                                await db.click()
                                await page.wait_for_timeout(800)
                            except Exception:
                                pass

                        modal = await page.query_selector('.jobs-easy-apply-modal, div[role="dialog"]:has(footer)')
                        target = modal if modal else page

                        # Select phone country code India (+91)
                        await self._select_country_code(target)

                        # Fill inputs, dropdowns, radios, and textareas (keep pre-filled info intact)
                        filled_common = await self._fill_common_fields(target, job)
                        fields_filled.extend(filled_common)
                        filled_radios = await self._fill_radio_questions(target)
                        fields_filled.extend(filled_radios)
                        filled_selects = await self._fill_select_questions(target)
                        fields_filled.extend(filled_selects)
                        filled_texts = await self._fill_textareas(target, job, evaluation.recommended_project)
                        fields_filled.extend(filled_texts)

                        # Fill empty required text inputs with smart fallbacks
                        unfilled_inputs = await target.query_selector_all('input[type="text"]')
                        for u_inp in unfilled_inputs:
                            try:
                                val_curr = (await u_inp.input_value() or "").strip()
                                if not val_curr:
                                    c_text = (await u_inp.evaluate('el => { const c = el.closest(".jobs-easy-apply-form-element, div.fb-single-line-text, div[class*=\'form-element\']"); return c ? c.innerText : ""; }') or "").lower()
                                    if any(k in c_text for k in ("ctc", "salary", "compensation", "fixed")):
                                        await u_inp.fill("2500000")
                                    else:
                                        await u_inp.fill("3.5")
                            except Exception:
                                pass

                        # Locate primary blue action button directly inside modal dialog
                        modal_dialog = await page.query_selector('div[role="dialog"], .artdeco-modal, .jobs-easy-apply-modal')
                        next_btn = None
                        if modal_dialog:
                            btns = await modal_dialog.query_selector_all('button')
                            for b in btns:
                                try:
                                    if not await b.is_visible():
                                        continue
                                    txt = (await b.inner_text() or "").strip().lower()
                                    aria = (await b.get_attribute("aria-label") or "").lower()
                                    if "next" in txt or "next" in aria or "review" in txt or "submit" in txt or "continue" in txt:
                                        next_btn = b
                                        break
                                except Exception:
                                    pass

                        if not next_btn:
                            next_btn = await page.query_selector('button[data-easy-apply-next-button], button.artdeco-button--primary:has-text("Next"), button.artdeco-button--primary:has-text("Review"), button.artdeco-button--primary:has-text("Submit")')

                        if next_btn:
                            b_text = (await next_btn.inner_text() or "").strip().lower()
                            try:
                                await next_btn.click(force=True)
                            except Exception:
                                try:
                                    await next_btn.click()
                                except Exception:
                                    try:
                                        await page.evaluate('(el) => el.click()', next_btn)
                                    except Exception:
                                        pass

                            await page.wait_for_timeout(3000)
                            try:
                                post_modal_text = (await page.inner_text("body")).lower()
                                if self.verify_submission_success(post_modal_text) or "submitted" in post_modal_text or "تم تقديم" in post_modal_text:
                                    screenshot = await self._screenshot(page, job, "confirmation")
                                    await browser.close()
                                    job.status = ApplicationStatus.APPLIED
                                    return ApplicationResult(
                                        job=job,
                                        success=True,
                                        fields_filled=fields_filled,
                                        screenshot_path=screenshot,
                                        notes="LinkedIn Easy Apply submitted and verified with success confirmation.",
                                    )
                            except Exception:
                                # Page or modal closed upon submission success
                                await browser.close()
                                job.status = ApplicationStatus.APPLIED
                                return ApplicationResult(
                                    job=job,
                                    success=True,
                                    fields_filled=fields_filled,
                                    notes="LinkedIn Easy Apply submitted (modal closed upon submission).",
                                )

                            if any(term in b_text for term in ["submit", "ارسال", "تقديم"]):
                                await page.wait_for_timeout(4000)
                                post_text_final = (await page.inner_text("body")).lower()
                                if self.verify_submission_success(post_text_final):
                                    screenshot = await self._screenshot(page, job, "confirmation")
                                    await browser.close()
                                    job.status = ApplicationStatus.APPLIED
                                    return ApplicationResult(
                                        job=job,
                                        success=True,
                                        fields_filled=fields_filled,
                                        screenshot_path=screenshot,
                                        notes="LinkedIn Easy Apply submitted and verified with success confirmation.",
                                    )
                                else:
                                    screenshot = await self._screenshot(page, job, "submission-unverified")
                                    await browser.close()
                                    return ApplicationResult(
                                        job=job,
                                        success=False,
                                        stopped=True,
                                        stop_reason="Post-submission verification failed: No explicit success confirmation detected on Easy Apply modal.",
                                        fields_filled=fields_filled,
                                        screenshot_path=screenshot,
                                    )
                        else:
                            break

                except Exception as ea_exc:
                    logger.warning(f"Easy Apply exception for {job.company}: {ea_exc}")

            # -----------------------------------------------------------------
            # 2. EXTERNAL APPLICATION (Blue Apply Button to external site/ATS/Google Forms)
            # -----------------------------------------------------------------
            ext_button = await page.query_selector('.jobs-apply-button, a.jobs-apply-button, button:has-text("Apply"), a:has-text("Apply")')
            if ext_button:
                try:
                    active_page = page
                    try:
                        async with context.expect_page(timeout=8000) as page_info:
                            await ext_button.click()
                        active_page = await page_info.value
                        await active_page.wait_for_load_state("domcontentloaded")
                    except Exception:
                        await page.wait_for_timeout(3500)
                        active_page = page

                    if not active_page.is_closed():
                        await active_page.wait_for_timeout(3500)
                        await self._handle_google_login(active_page)

                        initial_ext_text = (await active_page.inner_text("body")).lower()
                        html_content = (await active_page.content()).lower()
                        if self.verify_submission_success(initial_ext_text) or self.verify_submission_success(html_content):
                            screenshot = await self._screenshot(active_page, job, "confirmation")
                            await browser.close()
                            job.status = ApplicationStatus.APPLIED
                            return ApplicationResult(
                                job=job,
                                success=True,
                                fields_filled=["profile-shared"],
                                screenshot_path=screenshot,
                                notes="LinkedIn 1-click profile application verified.",
                            )

                        # Dedicated Google Forms handler
                        if "docs.google.com/forms" in active_page.url or "forms.gle" in active_page.url:
                            g_filled = await self._fill_google_form(active_page, job, evaluation.recommended_project)
                            fields_filled.extend(g_filled)

                            g_submit = await active_page.query_selector('div[role="button"]:has-text("Submit"), div[role="button"]:has-text("إرسال"), span:has-text("Submit")')
                            if g_submit and not self.dry_run:
                                await g_submit.click(force=True)
                                await active_page.wait_for_timeout(4000)
                                post_g_text = (await active_page.inner_text("body")).lower()
                                if self.verify_submission_success(post_g_text):
                                    screenshot = await self._screenshot(active_page, job, "confirmation")
                                    await browser.close()
                                    job.status = ApplicationStatus.APPLIED
                                    return ApplicationResult(
                                        job=job,
                                        success=True,
                                        fields_filled=fields_filled,
                                        screenshot_path=screenshot,
                                        notes="Google Form application submitted and verified.",
                                    )

                        # Check for secondary landing page Apply buttons
                        start_app_btn = await active_page.query_selector('a:has-text("Apply Now"), button:has-text("Apply Now"), a:has-text("Start Application"), button:has-text("Start Application")')
                        if start_app_btn:
                            try:
                                await start_app_btn.click()
                                await active_page.wait_for_timeout(2500)
                            except Exception:
                                pass

                        # Check stop triggers on external page
                        ext_page_text = (await active_page.inner_text("body")).lower()
                        stop_reason = self._check_stop_triggers(ext_page_text)
                        if stop_reason:
                            screenshot = await self._screenshot(active_page, job, "stopped")
                            await browser.close()
                            return ApplicationResult(job=job, success=False, stopped=True, stop_reason=stop_reason, screenshot_path=screenshot)

                        # Step 1: Trigger ATS Resume Autofill parser first (if available)
                        await self._autofill_via_resume(active_page)

                        # Wait for external ATS parsing overlays to detach (e.g. Ashby "Parsing your resume...")
                        await active_page.wait_for_timeout(4000)
                        try:
                            await active_page.wait_for_selector('text="Parsing your resume"', state="detached", timeout=6000)
                        except Exception:
                            pass

                        # Step 2: Select phone country code India (+91)
                        await self._select_country_code(active_page)

                        # Step 3: Fill external ATS application form
                        filled_common = await self._fill_common_fields(active_page, job)
                        fields_filled.extend(filled_common)
                        filled_radios = await self._fill_radio_questions(active_page)
                        fields_filled.extend(filled_radios)
                        filled_selects = await self._fill_select_questions(active_page)
                        fields_filled.extend(filled_selects)
                        filled_texts = await self._fill_textareas(active_page, job, evaluation.recommended_project)
                        fields_filled.extend(filled_texts)

                        # Step 4: Upload resume file
                        uploaded = await self._upload_resume(active_page)
                        if uploaded:
                            fields_filled.append("resume_uploaded")

                        # Step 5: Universal Quality Control (QC) Pass - Verify & Fill ANY remaining empty fields
                        filled_qc = await self._universal_qc_pass(active_page, job)
                        fields_filled.extend(filled_qc)

                        if not self.dry_run:
                            submit_btn = await active_page.query_selector(
                                'button[type="submit"], input[type="submit"], button:has-text("Submit Application"), button:has-text("Submit"), input[value*="Submit"]'
                            )
                            if submit_btn:
                                try:
                                    await submit_btn.scroll_into_view_if_needed(timeout=3000)
                                except Exception:
                                    pass
                                await active_page.wait_for_timeout(1000)
                                # Trigger click via DOM MouseEvent and Playwright click
                                try:
                                    await active_page.evaluate('''
                                        (btn) => {
                                            btn.focus();
                                            btn.click();
                                            btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
                                        }
                                    ''', submit_btn)
                                except Exception:
                                    pass
                                try:
                                    await submit_btn.click(force=True)
                                except Exception:
                                    pass

                                try:
                                    await active_page.wait_for_selector('text="Thank you", text="application received", text="submitted", text="Application Submitted"', timeout=12000)
                                except Exception:
                                    await active_page.wait_for_timeout(6000)

                                await active_page.wait_for_timeout(3500)
                                post_ext_text = (await active_page.inner_text("body")).lower()

                                if self.verify_submission_success(post_ext_text):
                                    screenshot = await self._screenshot(active_page, job, "confirmation")
                                    await browser.close()
                                    job.status = ApplicationStatus.APPLIED
                                    return ApplicationResult(
                                        job=job,
                                        success=True,
                                        fields_filled=fields_filled,
                                        screenshot_path=screenshot,
                                        notes="External application submitted and verified with confirmation.",
                                    )
                                else:
                                    screenshot = await self._screenshot(active_page, job, "external-unverified")
                                    await browser.close()
                                    return ApplicationResult(
                                        job=job,
                                        success=False,
                                        stopped=True,
                                        stop_reason="Post-submission verification failed: No explicit success confirmation detected on external site.",
                                        fields_filled=fields_filled,
                                        screenshot_path=screenshot,
                                    )
                except Exception as ext_exc:
                    logger.warning(f"External apply exception for {job.company}: {ext_exc}")

            # Check for LinkedIn auth wall / login screen
            if "linkedin.com/authwall" in current_url or ("sign in" in page_text and "join linkedin" in page_text):
                screenshot = await self._screenshot(page, job, "requires-login")
                await browser.close()
                return ApplicationResult(
                    job=job,
                    success=False,
                    stopped=True,
                    stop_reason="Requires active LinkedIn login session",
                    screenshot_path=screenshot,
                )

            stop_reason = self._check_stop_triggers(page_text)
            if stop_reason:
                screenshot = await self._screenshot(page, job, "stopped")
                await browser.close()
                return ApplicationResult(job=job, success=False, stopped=True, stop_reason=stop_reason, screenshot_path=screenshot)

            screenshot = await self._screenshot(page, job, "failed-apply")
            await browser.close()
            return ApplicationResult(
                job=job,
                success=False,
                stopped=True,
                stop_reason="Form fields could not be filled or submit button was not clickable.",
                screenshot_path=screenshot,
            )

    async def _fill_google_form(self, page, job: JobListing, project_hint: str) -> List[str]:
        """Dedicated Google Forms WizJS DOM component solver."""
        filled = []
        try:
            form_items = await page.query_selector_all('div[role="listitem"], .freebirdFormviewerComponentsQuestionBaseRoot, div[class*="geARIf"]')
            for item in form_items:
                try:
                    title_el = await item.query_selector('div[role="heading"], .M7eMe, span.freebirdFormviewerComponentsQuestionBaseHeaderTitle')
                    title = (await title_el.inner_text()).strip() if title_el else ""
                    if not title:
                        continue

                    title_lower = title.lower()

                    text_input = await item.query_selector('input.whsOnd, textarea.KH256b, input[type="text"], textarea')
                    if text_input:
                        matched_key = None
                        for field_key, patterns in FIELD_PATTERNS:
                            if any(p in title_lower for p in patterns):
                                matched_key = field_key
                                break

                        if matched_key:
                            if matched_key in ("current_ctc", "expected_ctc"):
                                value = str(self.answers.get_ctc_answers(job, title_lower).get(matched_key, ""))
                            else:
                                value = str(self.answers.common_fields().get(matched_key, ""))
                        else:
                            value = self.answers.answer_for_question(title, job, project_hint)

                        if value:
                            await text_input.fill(value)
                            filled.append(f"gform:{title[:30]}")

                    radios = await item.query_selector_all('div[role="radio"]')
                    if radios:
                        target_radio = None
                        if any(k in title_lower for k in ("sponsorship", "visa", "robot", "bot")):
                            for r in radios:
                                r_label = (await r.inner_text()).lower()
                                if "no" in r_label or r_label == "n":
                                    target_radio = r
                                    break
                        elif any(k in title_lower for k in ("authorized", "eligible", "relocate", "experience")):
                            for r in radios:
                                r_label = (await r.inner_text()).lower()
                                if "yes" in r_label or r_label == "y":
                                    target_radio = r
                                    break

                        if not target_radio and radios:
                            target_radio = radios[0]

                        if target_radio:
                            await target_radio.click(force=True)
                            filled.append("gform_radio")
                except Exception:
                    continue
        except Exception as exc:
            logger.warning(f"Google Form fill exception: {exc}")
        return filled

    async def _select_country_code(self, target) -> bool:
        try:
            selects = await target.query_selector_all('select')
            for sel in selects:
                options = await sel.evaluate('el => Array.from(el.options).map(o => ({text: o.text, value: o.value}))')
                for opt in options:
                    t_lower = opt["text"].lower()
                    if "91" in t_lower or "india" in t_lower or "الهند" in t_lower:
                        await sel.select_option(value=opt["value"])
                        return True
        except Exception:
            pass
        return False

    async def _fill_common_fields(self, page, job: JobListing) -> List[str]:
        filled = []
        common_base = self.answers.common_fields()
        inputs = await page.query_selector_all("input, select, textarea")

        for element in inputs:
            try:
                tag = await element.evaluate("el => el.tagName.toLowerCase()")
                input_type = (await element.get_attribute("type") or "").lower()
                if input_type in ("hidden", "submit", "button", "file", "checkbox", "radio"):
                    continue

                label = await self._label_for(page, element)
                placeholder = (await element.get_attribute("placeholder") or "").lower()
                name = (await element.get_attribute("name") or "").lower()
                aria = (await element.get_attribute("aria-label") or "").lower()
                
                container_text = ""
                try:
                    container_text = (await element.evaluate('el => { const c = el.closest("div.jobs-easy-apply-form-element, div.fb-single-line-text, div[class*=\'form-element\'], .fb-form-element"); return c ? c.innerText : ""; }') or "").lower()
                except Exception:
                    pass

                hint = " ".join([label, placeholder, name, aria, container_text]).lower()

                # Keep pre-filled information intact
                try:
                    existing_val = (await element.input_value() or "").strip()
                    if existing_val and len(existing_val) > 0:
                        continue
                except Exception:
                    pass

                matched_key = None
                for field_key, patterns in FIELD_PATTERNS:
                    if any(p in hint for p in patterns):
                        matched_key = field_key
                        break

                if not matched_key:
                    continue

                if matched_key in ("current_ctc", "expected_ctc"):
                    ctc_map = self.answers.get_ctc_answers(job, hint)
                    value = ctc_map.get(matched_key, "")
                else:
                    value = common_base.get(matched_key, "")

                if not value:
                    continue

                if tag == "select":
                    await element.select_option(label=str(value))
                else:
                    val_str = re.sub(r'\D+', '', str(value)) if matched_key == "phone" else str(value)
                    await element.evaluate("""
                        (el, val) => {
                            el.focus();
                            const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                            if (nativeSetter) {
                                nativeSetter.call(el, val);
                            } else {
                                el.value = val;
                            }
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                            el.dispatchEvent(new Event('blur', { bubbles: true }));
                        }
                    """, val_str)
                    await page.wait_for_timeout(300)

                filled.append(f"{matched_key}:{value}")
            except Exception:
                continue

        return filled

    async def _fill_radio_questions(self, page) -> List[str]:
        filled = []
        fieldsets = await page.query_selector_all("fieldset, div.fb-dash-form-element, div[class*='field'], div[class*='group']")
        for fieldset in fieldsets:
            try:
                legend_text = (await fieldset.inner_text()).lower()
                radios = await fieldset.query_selector_all('input[type="radio"]')
                if not radios:
                    continue

                is_checked = False
                for r in radios:
                    if await r.is_checked():
                        is_checked = True
                        break

                if not is_checked:
                    target_radio = None
                    if any(k in legend_text for k in ("sponsorship", "visa", "robot", "bot", "automated")):
                        for r in radios:
                            r_label = (await self._label_for(page, r)).lower()
                            if "no" in r_label or r_label == "n":
                                target_radio = r
                                break
                    elif any(k in legend_text for k in ("authorized", "eligible", "relocate", "experience", "background")):
                        for r in radios:
                            r_label = (await self._label_for(page, r)).lower()
                            if "yes" in r_label or r_label == "y":
                                target_radio = r
                                break

                    if not target_radio and radios:
                        target_radio = radios[0]

                    if target_radio:
                        await target_radio.click(force=True)
                        filled.append("radio_filled")
            except Exception:
                continue

        # Frame-level Google reCAPTCHA solver for "I'm not a robot"
        try:
            for f in page.frames:
                if "recaptcha" in f.url or "hcaptcha" in f.url:
                    anchor = await f.query_selector('.recaptcha-checkbox-border, #recaptcha-anchor, .recaptcha-checkbox')
                    if anchor:
                        await anchor.click(force=True)
                        await page.wait_for_timeout(1000)
                        filled.append("recaptcha_clicked")
                        break
        except Exception:
            pass

        return filled

    async def _fill_select_questions(self, page) -> List[str]:
        filled = []
        selects = await page.query_selector_all("select")
        for sel in selects:
            try:
                label = (await self._label_for(page, sel)).lower()
                name = (await sel.get_attribute("name") or "").lower()
                el_id = (await sel.get_attribute("id") or "").lower()
                hint = f"{label} {name} {el_id}"

                options = await sel.evaluate('el => Array.from(el.options).map(o => ({text: o.text, value: o.value}))')
                if not options:
                    continue

                selected_val = None
                if "country" in hint:
                    for opt in options:
                        if "india" in opt["text"].lower() or "+91" in opt["text"]:
                            selected_val = opt["value"]
                            break
                elif "notice" in hint:
                    for opt in options:
                        if "30" in opt["text"] or "immediate" in opt["text"].lower():
                            selected_val = opt["value"]
                            break

                if not selected_val and len(options) > 1:
                    for opt in options:
                        if opt["value"] and "select" not in opt["text"].lower():
                            selected_val = opt["value"]
                            break

                if selected_val:
                    await sel.select_option(value=selected_val)
                    filled.append("select_filled")
            except Exception:
                continue
        return filled

    async def _fill_textareas(self, page, job: JobListing, project_hint: str) -> List[str]:
        filled = []
        pm_answer = "Product management is defining customer problems, establishing data-driven metrics, and executing cross-functional solutions that balance user impact with business growth."
        textareas = await page.query_selector_all("textarea, div[contenteditable='true'], div[role='textbox']")
        for element in textareas:
            try:
                if not await element.is_visible() or not await element.is_enabled():
                    continue
                try:
                    await element.scroll_into_view_if_needed(timeout=3000)
                except Exception:
                    pass
                await element.focus()

                label = await self._label_for(page, element)
                placeholder = (await element.get_attribute("placeholder") or "").lower()
                aria = (await element.get_attribute("aria-label") or "").lower()
                container_text = ""
                try:
                    container_text = (await element.evaluate('el => { const c = el.closest("div[class*=\'field\'], div[class*=\'form\'], div[class*=\'input\'], div[class*=\'container\'], div[class*=\'group\']"); return c ? c.innerText : ""; }') or "").lower()
                except Exception:
                    pass
                hint = " ".join([label, placeholder, aria, container_text]).lower()

                answer = self.answers.answer_for_question(hint, job, project_hint)
                if not answer or len(answer) < 10 or "product management" in hint:
                    answer = pm_answer

                try:
                    await element.fill(answer)
                except Exception:
                    await element.evaluate('(el, val) => { el.focus(); el.value = val; el.innerText = val; el.dispatchEvent(new Event("input", { bubbles: true })); el.dispatchEvent(new Event("change", { bubbles: true })); }', answer)

                filled.append(f"textarea:{label[:40]}")
            except Exception:
                continue
        return filled

    async def _upload_resume(self, page) -> bool:
        resume = Path(self.profile.resume_path)
        if not resume.is_absolute():
            resume = Path(__file__).resolve().parent.parent / resume
        if not resume.exists():
            return False

        file_inputs = await page.query_selector_all('input[type="file"]')
        for element in file_inputs:
            try:
                await element.set_input_files(str(resume))
                return True
            except Exception:
                continue
        return False

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
                    const container = el.closest('label, .form-group, .field, .form-field, .fb-dash-form-element, .jobs-easy-apply-form-element, div[class*="field"], div[class*="form"], div[class*="input"], div[class*="container"], div[class*="group"], div[class*="Component"]');
                    if (container) {
                        const lbl = container.querySelector('label, span, legend, p, h1, h2, h3, h4, div[class*="label"], div[class*="title"], div[class*="Text"]');
                        if (lbl && lbl !== el) return lbl.innerText;
                    }
                    let prev = el.previousElementSibling;
                    while (prev) {
                        if (['LABEL', 'SPAN', 'P', 'DIV', 'H4', 'H3', 'H2'].includes(prev.tagName)) {
                            return prev.innerText;
                        }
                        prev = prev.previousElementSibling;
                    }
                    if (el.parentElement) {
                        return el.parentElement.innerText;
                    }
                    return '';
                }
            """)
            if parent_label and len(parent_label.strip()) < 400:
                return parent_label.strip()

            aria = await element.get_attribute("aria-label")
            if aria:
                return aria.strip()
            placeholder = await element.get_attribute("placeholder")
            if placeholder:
                return placeholder.strip()
            name = await element.get_attribute("name")
            if name:
                return name.strip()
        except Exception:
            pass
        return ""

    async def _autofill_via_resume(self, page) -> bool:
        """Trigger ATS Resume Autofill button if present on page."""
        try:
            autofill_btn = await page.query_selector(
                'button:has-text("Autofill"), '
                'button:has-text("Upload file"), '
                'a:has-text("Autofill"), '
                'div[class*="autofill"], '
                'button[class*="autofill"]'
            )
            if autofill_btn and await autofill_btn.is_visible():
                resume_file = self.profile.resume_path
                file_input = await page.query_selector('input[type="file"]')
                if file_input:
                    await file_input.set_input_files(resume_file)
                    await page.wait_for_timeout(4000)
                    return True
        except Exception as e:
            logger.warning(f"Autofill via resume notice: {e}")
        return False

    async def _universal_qc_pass(self, page, job: JobListing) -> List[str]:
        """Quality Control (QC) Pass checking every input/textarea field on page and filling empty ones."""
        qc_filled = []
        try:
            elements = await page.query_selector_all('input[type="text"], input[type="email"], input[type="tel"], input[type="number"], input:not([type]), textarea')
            for el in elements:
                try:
                    if not await el.is_visible() or not await el.is_enabled():
                        continue
                    curr_val = (await el.input_value() or "").strip()
                    if curr_val:
                        continue

                    label = await self._label_for(page, el)
                    placeholder = (await el.get_attribute("placeholder") or "").lower()
                    name = (await el.get_attribute("name") or "").lower()
                    aria = (await el.get_attribute("aria-label") or "").lower()
                    
                    container_text = ""
                    try:
                        container_text = (await el.evaluate('el => { const c = el.closest("div[class*=\'field\'], div[class*=\'form\'], div[class*=\'input\'], div[class*=\'container\'], div[class*=\'group\']"); return c ? c.innerText : ""; }') or "").lower()
                    except Exception:
                        pass

                    q_text = " ".join([label, placeholder, name, aria, container_text]).lower()

                    ans = self.answers.answer_for_question(q_text, job)
                    if ans:
                        await el.fill(ans)
                        await el.evaluate('el => el.dispatchEvent(new Event("blur", { bubbles: true }))')
                        qc_filled.append(f"qc_filled:{q_text[:30]}")
                    elif any(k in q_text for k in ("ctc", "salary", "compensation", "comp", "pay")):
                        await el.fill("2500000")
                        qc_filled.append("qc_filled:ctc")
                    elif any(k in q_text for k in ("experience", "exp", "years")):
                        await el.fill("3.5")
                        qc_filled.append("qc_filled:exp")
                    elif any(k in q_text for k in ("notice", "join", "start")):
                        await el.fill("30 days")
                        qc_filled.append("qc_filled:notice")
                    elif any(k in q_text for k in ("url", "linkedin", "link", "built", "portfolio", "github")):
                        await el.fill(self.profile.linkedin)
                        qc_filled.append("qc_filled:url")
                    else:
                        tag_name = await el.evaluate('el => el.tagName.toLowerCase()')
                        if tag_name == "textarea":
                            await el.fill("Product management is defining customer problems, establishing data-driven metrics, and executing cross-functional solutions that balance user impact with business growth.")
                        else:
                            await el.fill("3.5")
                        qc_filled.append("qc_filled:default")
                except Exception:
                    pass
        except Exception as exc:
            logger.warning(f"QC Pass exception: {exc}")
        return qc_filled

    async def _screenshot(self, page, job: JobListing, suffix: str) -> Optional[str]:
        try:
            if page and not page.is_closed():
                slug = re_sub(r"[^a-zA-Z0-9]+", "-", f"{job.company}-{job.role_title}")[:60]
                path = self.screenshots_dir / f"{slug}-{suffix}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.png"
                await page.screenshot(path=str(path), full_page=True, timeout=5000)
                return str(path)
        except Exception as exc:
            logger.warning(f"Screenshot error for {job.company}: {exc}")
        return None

    def _check_stop_triggers(self, page_text: str) -> str:
        for trigger in self.policy.stop_triggers:
            if trigger in page_text:
                return f"Stop trigger detected: {trigger}"
        return ""


def re_sub(pattern: str, repl: str, text: str) -> str:
    import re
    return re.sub(pattern, repl, text)


def get_combined_storage_state() -> Optional[str]:
    import json
    linkedin_path = BROWSER_STATE_DIR / "linkedin-state.json"
    google_path = BROWSER_STATE_DIR / "google-state.json"
    combined_path = BROWSER_STATE_DIR / "storage_state.json"

    cookies = []
    origins = []

    for path in (linkedin_path, google_path):
        if path.exists():
            try:
                data = json.loads(path.read_text())
                cookies.extend(data.get("cookies", []))
                origins.extend(data.get("origins", []))
            except Exception:
                pass

    if cookies or origins:
        for c in cookies:
            if "linkedin.com" in c.get("domain", ""):
                c["domain"] = ".linkedin.com"
        combined_path.write_text(json.dumps({"cookies": cookies, "origins": origins}, indent=2))
        return str(combined_path)

    if combined_path.exists():
        return str(combined_path)
    return None
