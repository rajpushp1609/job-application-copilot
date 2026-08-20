from __future__ import annotations

import asyncio
import logging
import re
from datetime import date, datetime
from typing import AsyncIterator, Dict, List, Optional
from urllib.parse import quote_plus, urlparse

from agents.config import BROWSER_STATE_DIR, ROOT, PolicyConfig, load_policy
from agents.models import JobListing

logger = logging.getLogger("discovery_agent")


ROLE_SEARCH_TERMS = [
    "Product Manager",
    "Associate Product Manager",
    "Product Analyst",
    "Senior Product Analyst",
    "Product Operations",
    "Growth Product Manager",
]


class DiscoveryAgent:
    """Discovers job listings via LinkedIn search and direct URL ingestion."""

    def __init__(self, policy: Optional[PolicyConfig] = None, headless: bool = False):
        self.policy = policy or load_policy()
        self.headless = headless
        self.state_path = BROWSER_STATE_DIR / "linkedin-state.json"

    async def discover(
        self,
        sources: Optional[List[str]] = None,
        max_results: int = 20,
        region: str = "India",
    ) -> List[JobListing]:
        sources = sources or ["linkedin"]
        jobs: List[JobListing] = []
        seen_urls = set()

        if "linkedin" in sources:
            linkedin_jobs = await self._discover_linkedin(max_results=max_results, region=region)
            for job in linkedin_jobs:
                if job.job_url not in seen_urls:
                    seen_urls.add(job.job_url)
                    jobs.append(job)

        if "urls" in sources:
            for url in sources:
                if url.startswith("http"):
                    job = await self._discover_from_url(url, region=region)
                    if job and job.job_url not in seen_urls:
                        seen_urls.add(job.job_url)
                        jobs.append(job)

        return jobs

    def discover_from_urls(self, urls: List[str], region: str = "India") -> List[JobListing]:
        jobs = []
        for url in urls:
            job = self._parse_job_from_url(url, region=region)
            if job:
                jobs.append(job)
        return jobs

    def _parse_job_from_url(self, url: str, region: str = "India") -> Optional[JobListing]:
        parsed = urlparse(url)
        host = parsed.netloc.lower()

        company = ""
        role_title = ""
        portal = "Other"

        if "linkedin.com" in host:
            portal = "LinkedIn"
            company = "Unknown"
            role_title = "Product Role"
        elif "naukri.com" in host:
            portal = "Naukri"
            company = "Unknown"
            role_title = "Product Role"
        else:
            portal = "Company careers page"
            company = parsed.netloc.replace("www.", "").split(".")[0].title()
            role_title = "Product Role"

        return JobListing(
            company=company,
            role_title=role_title,
            role_family="",
            job_url=url,
            portal=portal,
            region=region,
            discovered_at=datetime.utcnow().isoformat(),
        )

    async def _discover_linkedin(self, max_results: int = 20, region: str = "India") -> List[JobListing]:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is required. Run: pip install playwright && playwright install chromium") from exc

        jobs: List[JobListing] = []
        search_query = " OR ".join(f'"{term}"' for term in ROLE_SEARCH_TERMS[:4])

        if region.lower() in ("sea", "south east asia", "southeast asia"):
            location_param = "Singapore"
        else:
            location_param = "India"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context_kwargs = {}
            if self.state_path.exists():
                context_kwargs["storage_state"] = str(self.state_path)

            search_url = (
                "https://www.linkedin.com/jobs/search/"
                f"?keywords={quote_plus(search_query)}&location={quote_plus(location_param)}&f_TPR=r604800&f_AL=true"
            )

            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()

            try:
                await page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
            except Exception as goto_err:
                if "ERR_TOO_MANY_REDIRECTS" in str(goto_err) or "999" in str(goto_err):
                    logger.info("Retrying LinkedIn search navigation with home page warmup...")
                    try:
                        await context.clear_cookies()
                    except Exception:
                        pass
                    await page.goto("https://www.linkedin.com/jobs", wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(1000)
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                else:
                    raise goto_err

            if "login" in page.url or "authwall" in page.url:
                await self.login_linkedin()
                # Retry discovery after login
                await page.goto(search_url, wait_until="domcontentloaded", timeout=45000)

            await page.wait_for_timeout(3000)
            cards = await page.query_selector_all(".job-search-card, .base-card")
            for card in cards[:max_results]:
                try:
                    title_el = await card.query_selector(".base-search-card__title, h3")
                    company_el = await card.query_selector(".base-search-card__subtitle, h4")
                    location_el = await card.query_selector(".job-search-card__location")
                    link_el = await card.query_selector("a.base-card__full-link, a[href*='/jobs/view/']")
                    time_el = await card.query_selector("time")

                    title = (await title_el.inner_text()).strip() if title_el else "Product Role"
                    company = (await company_el.inner_text()).strip() if company_el else "Unknown"
                    location_text = (await location_el.inner_text()).strip() if location_el else ""
                    href = await link_el.get_attribute("href") if link_el else ""
                    if href and not href.startswith("http"):
                        href = f"https://www.linkedin.com{href}"

                    date_posted = None
                    if time_el:
                        datetime_attr = await time_el.get_attribute("datetime")
                        if datetime_attr:
                            date_posted = date.fromisoformat(datetime_attr[:10])

                    role_family = self._infer_role_family(title)
                    jobs.append(JobListing(
                        company=company,
                        role_title=title,
                        role_family=role_family,
                        job_url=href or search_url,
                        portal="LinkedIn",
                        location=location_text,
                        region=region,
                        date_posted=date_posted,
                        discovered_at=datetime.utcnow().isoformat(),
                    ))
                except Exception:
                    continue

            await context.storage_state(path=str(self.state_path))
            await browser.close()

        return jobs

    async def _discover_from_url(self, url: str) -> Optional[JobListing]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return self._parse_job_from_url(url)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            title = await page.title()
            text = await page.inner_text("body")

            company = self._extract_company_from_page(text, urlparse(url).netloc)
            role_title = self._extract_role_from_title(title)
            role_family = self._infer_role_family(role_title)

            job = JobListing(
                company=company,
                role_title=role_title,
                role_family=role_family,
                job_url=url,
                portal=self._portal_from_url(url),
                description=text[:4000],
                discovered_at=datetime.utcnow().isoformat(),
            )
            await browser.close()
            return job

    async def login_linkedin(self) -> None:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is required.") from exc

        import os
        env_file = ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()

        email = os.environ.get("LINKEDIN_EMAIL")
        password = os.environ.get("LINKEDIN_PASSWORD")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                locale="en-US",
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
            )
            await context.add_cookies([
                {"name": "lang", "value": "v=2&lang=en-us", "domain": ".linkedin.com", "path": "/"},
                {"name": "lang", "value": "v=2&lang=en-us", "domain": "www.linkedin.com", "path": "/"},
            ])
            page = await context.new_page()
            await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            if "feed" in page.url or "checkpoint" in page.url or "mynetwork" in page.url:
                print("Already logged in to LinkedIn!")
                await context.storage_state(path=str(self.state_path))
                storage_file = BROWSER_STATE_DIR / "storage_state.json"
                await context.storage_state(path=str(storage_file))
                await browser.close()
                print(f"Saved English session to {self.state_path} and {storage_file}")
                return

            try:
                if email and password:
                    print("Automating LinkedIn sign-in using .env credentials...")
                    user_input = await page.query_selector('#username, #session_key, input[name="session_key"], input[name="username"], input[type="email"]')
                    if user_input and await user_input.is_visible():
                        await user_input.fill(email)
                    pass_input = await page.query_selector('#password, #session_password, input[name="session_password"], input[name="password"], input[type="password"]')
                    if pass_input and await pass_input.is_visible():
                        await pass_input.fill(password)
                    submit_btn = await page.query_selector('button[type="submit"], button:has-text("Sign in")')
                    if submit_btn and await submit_btn.is_visible():
                        await submit_btn.click()
                        await page.wait_for_timeout(5000)
            except Exception as e:
                print(f"Automated sign-in note: {e}")

            print("Waiting for LinkedIn sign-in to complete...")
            for _ in range(45):
                try:
                    if "feed" in page.url or "mynetwork" in page.url or "jobs" in page.url:
                        break
                    await page.wait_for_timeout(1000)
                except Exception:
                    break

            try:
                await context.storage_state(path=str(self.state_path))
                storage_file = BROWSER_STATE_DIR / "storage_state.json"
                await context.storage_state(path=str(storage_file))
                print(f"Saved English session to {self.state_path} and {storage_file}")
            except Exception as e:
                print(f"State save note: {e}")

            try:
                await browser.close()
            except Exception:
                pass

    async def login_google(self) -> None:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is required. Run: pip install playwright && playwright install chromium") from exc

        google_state_path = BROWSER_STATE_DIR / "google-state.json"

        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(
                    channel="chrome",
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                )
            except Exception:
                browser = await p.chromium.launch(
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                )

            context = await browser.new_context(locale="en-US")
            page = await context.new_page()

            await page.goto("https://accounts.google.com/signin", wait_until="domcontentloaded")
            print("\nPlease sign in to your Google Account in the browser window.")
            print("Once signed in, press ENTER in this terminal to save session...")
            await asyncio.get_event_loop().run_in_executor(None, input)

            await context.storage_state(path=str(google_state_path))
            await browser.close()
            print(f"Successfully saved Google session state to {google_state_path}")

    def _infer_role_family(self, title: str) -> str:
        t = title.lower()
        mapping = [
            ("associate product manager", "Associate Product Manager / APM"),
            ("apm", "Associate Product Manager / APM"),
            ("senior product analyst", "Senior Product Analyst"),
            ("product analyst", "Product Analyst"),
            ("strategy analyst", "Strategy Analyst"),
            ("product owner", "Product Owner"),
            ("product operations", "Product Operations / Product Ops"),
            ("product ops", "Product Operations / Product Ops"),
            ("growth", "Growth Product / Growth Analyst"),
            ("product manager", "Product Manager"),
        ]
        for needle, family in mapping:
            if needle in t:
                return family
        return "Product Generalist"

    def _extract_company_from_page(self, text: str, host: str) -> str:
        for line in text.splitlines()[:30]:
            if "careers" in line.lower() or "hiring" in line.lower():
                continue
            if 2 < len(line.strip()) < 60:
                return line.strip()
        return host.replace("www.", "").split(".")[0].title()

    def _extract_role_from_title(self, title: str) -> str:
        cleaned = re.sub(r"\s*[|\-].*$", "", title).strip()
        return cleaned or "Product Role"

    def _portal_from_url(self, url: str) -> str:
        host = urlparse(url).netloc.lower()
        if "linkedin.com" in host:
            return "LinkedIn"
        if "naukri.com" in host:
            return "Naukri"
        if "indeed.com" in host:
            return "Indeed"
        return "Company careers page"
