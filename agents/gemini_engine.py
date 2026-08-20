from __future__ import annotations

import os
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("gemini_engine")


from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def _resolve_api_key(api_key: Optional[str] = None) -> str:
    if api_key:
        return api_key
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        return key
    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"\'')
    return ""


class GeminiEngine:
    """Wrapper for Gemini API with automatic DeepSeek API fallback and strict token safeguards."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-3.6-flash"):
        self.api_key = _resolve_api_key(api_key)
        self.model_name = model_name
        self.fallback_models = ["gemini-3.1-flash-lite", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
        self._client = None
        self._rate_limited = False
        
        # DeepSeek Fallback configuration
        self.deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not self.deepseek_key:
            env_path = ROOT_DIR / ".env"
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    if line.startswith("DEEPSEEK_API_KEY="):
                        self.deepseek_key = line.split("=", 1)[1].strip().strip('"\'')

        # Safeguards: Token limits & Daily budgets
        self.max_screening_tokens = 150  # Cap response length to ~100 words (saves cost)
        self.daily_call_limit = 100      # Safety cap on AI generations per day
        self._daily_call_count = 0

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as exc:
                logger.warning(f"Could not initialize google.genai client: {exc}")
                try:
                    import google.generativeai as legacy_genai
                    legacy_genai.configure(api_key=self.api_key)
                    self._legacy = legacy_genai
                except Exception as legacy_exc:
                    logger.warning(f"Could not initialize google.generativeai client: {legacy_exc}")

    @property
    def is_available(self) -> bool:
        has_gemini = bool(self.api_key and not self._rate_limited and (self._client is not None or getattr(self, "_legacy", None) is not None))
        has_deepseek = bool(self.deepseek_key)
        return (has_gemini or has_deepseek) and self._daily_call_count < self.daily_call_limit

    def _call_deepseek(self, prompt: str, system_instruction: str = "", max_tokens: int = 150) -> Optional[str]:
        """Direct REST call to DeepSeek API with strict token limits."""
        if not self.deepseek_key:
            return None
        
        try:
            import urllib.request
            import ssl
            ssl_ctx = ssl._create_unverified_context()
            
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            data = {
                "model": "deepseek-chat",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.3
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.deepseek_key}"
            }

            req = urllib.request.Request(
                "https://api.deepseek.com/chat/completions",
                data=json.dumps(data).encode("utf-8"),
                headers=headers,
                method="POST"
            )

            with urllib.request.urlopen(req, context=ssl_ctx, timeout=12) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                text = res.get("choices", [{}])[0].get("message", {}).get("content", "")
                if text:
                    logger.info("DeepSeek API Fallback: Successfully generated answer.")
                    return text.strip()
        except Exception as exc:
            logger.warning(f"DeepSeek API call failed: {exc}")
        return None

    def generate_text(self, prompt: str, system_instruction: str = "", max_tokens: int = 150) -> Optional[str]:
        if not self.is_available:
            logger.warning("No LLM provider available or daily budget exceeded.")
            return None

        self._daily_call_count += 1

        # Attempt 1: Try Gemini API
        if not self._rate_limited and self.api_key:
            models_to_try = [self.model_name] + [m for m in self.fallback_models if m != self.model_name]
            for model in models_to_try:
                try:
                    if self._client:
                        from google.genai import types
                        config = types.GenerateContentConfig(
                            system_instruction=system_instruction if system_instruction else None,
                            temperature=0.3,
                            max_output_tokens=max_tokens,
                        )
                        response = self._client.models.generate_content(
                            model=model,
                            contents=prompt,
                            config=config,
                        )
                        if response and response.text:
                            return response.text.strip()
                    elif hasattr(self, "_legacy"):
                        legacy_model = self._legacy.GenerativeModel(model)
                        full_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
                        response = legacy_model.generate_content(full_prompt)
                        if response and response.text:
                            return response.text.strip()
                except Exception as exc:
                    exc_str = str(exc)
                    if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
                        logger.warning("Gemini API key rate limited / quota exhausted. Failing over to DeepSeek API.")
                        self._rate_limited = True
                        break
                    logger.warning(f"Gemini generation with model {model} failed: {exc}")
                    continue

        # Attempt 2: Dual Fallback to DeepSeek API
        logger.info("Triggering DeepSeek API failover...")
        return self._call_deepseek(prompt=prompt, system_instruction=system_instruction, max_tokens=max_tokens)

    def generate_screening_answer(
        self,
        question: str,
        job_info: Dict[str, Any],
        profile_info: Dict[str, Any],
        policy_info: Dict[str, Any],
    ) -> Optional[str]:
        if not self.is_available:
            return None

        system_instruction = (
            "You are an executive career assistant representing Pushp Raj (3.5 years experience as a Product Manager / APM / Analyst). "
            "Your task is to generate concise, highly persuasive, authentic screening answers for job applications. "
            "STRICT RULES:\n"
            "1. Base all impact claims strictly on Pushp's real experience:\n"
            "   - Navi: Account Aggregator (50K+ daily users), pre-purchase conversion improved 20-25% via A/B tests.\n"
            "   - Wayground: Voyage Math 0-to-1 scaled to 5K teachers in 4 months; AI quiz publish rate 65% -> 75%.\n"
            "   - SquadStack: Acquisition & retention insights driving $3M revenue, TAT reduced by 32%.\n"
            "   - AI Tools: Daily user of Claude Code, ChatGPT, Cursor, and Gemini for 0-to-1 vibe-coding prototypes, PRDs, and AI workflows.\n"
            "2. Never hallucinate fake companies or metrics.\n"
            "3. Answer directly and concisely in 2-3 sentences (under 90 words)."
        )

        prompt = (
            f"Question: {question}\n\n"
            f"Job Context:\n"
            f"- Company: {job_info.get('company', '')}\n"
            f"- Role: {job_info.get('role_title', '')}\n"
            f"Write a crisp 2-3 sentence response."
        )

        return self.generate_text(prompt=prompt, system_instruction=system_instruction, max_tokens=self.max_screening_tokens)

    def evaluate_match_score(
        self,
        job_info: Dict[str, Any],
        policy_info: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not self.is_available:
            return None

        system_instruction = (
            "You are a job-match evaluation system. Analyze the job title and description against target product roles. "
            "Return output strictly in JSON format with fields:\n"
            '{"score": <float between 0.0 and 1.0>, "reason": "<short summary>", "is_match": <boolean>}'
        )

        prompt = (
            f"Target Role Families: {json.dumps(policy_info.get('role_families', []))}\n\n"
            f"Job to Evaluate:\n"
            f"- Company: {job_info.get('company')}\n"
            f"- Role: {job_info.get('role_title')}\n"
            f"- Description: {job_info.get('description', '')[:1000]}\n"
        )

        res = self.generate_text(prompt=prompt, system_instruction=system_instruction, max_tokens=100)
        if res:
            try:
                cleaned = res.replace("```json", "").replace("```", "").strip()
                return json.loads(cleaned)
            except Exception:
                pass
        return None

    def verify_submission(self, page_text: str) -> Optional[bool]:
        """Verifies if the post-submission text contains a genuine job application submission confirmation."""
        if not self.is_available or not page_text or len(page_text.strip()) < 10:
            return None

        system_instruction = (
            "Determine if web page text represents a successful job application submission confirmation. "
            "Respond strictly with JSON:\n"
            '{"is_submitted": true/false, "confidence": <float 0.0 to 1.0>, "reason": "<short explanation>"}'
        )

        prompt = f"Page Text:\n{page_text[:1500]}\n"

        res = self.generate_text(prompt=prompt, system_instruction=system_instruction, max_tokens=60)
        if res:
            try:
                cleaned = res.replace("```json", "").replace("```", "").strip()
                data = json.loads(cleaned)
                if isinstance(data, dict):
                    return bool(data.get("is_submitted", False) and data.get("confidence", 0.0) >= 0.6)
            except Exception as exc:
                logger.warning(f"Error parsing verify_submission AI JSON: {exc}")
        return None


