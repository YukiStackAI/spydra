"""Spydra AntiBot — CaptchaSolver: multi-provider CAPTCHA solving."""
from __future__ import annotations
import logging, re, time
from typing import Any, Callable, Dict, Optional

log = logging.getLogger("spydra.antibot.captcha")
_POLL, _TIMEOUT = 5, 120

class CaptchaSolverError(Exception): pass

class CaptchaSolver:
    """Solve reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile, and image CAPTCHAs.

    Providers: "2captcha" | "capsolver" | "custom"

    Example::

        solver = CaptchaSolver(provider="2captcha", api_key="YOUR_KEY")
        token  = solver.solve_recaptcha_v2(site_key="6Le-...", page_url="https://example.com")

        # Auto-detect + solve on any Playwright page:
        solver.auto_solve(playwright_page)
    """
    def __init__(self, provider="2captcha", api_key=None, custom_solver=None,
                 timeout=_TIMEOUT, poll_interval=_POLL, soft_fail=False):
        self.provider = provider.lower()
        self.api_key = api_key
        self.custom_solver = custom_solver
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.soft_fail = soft_fail
        if self.provider == "custom" and custom_solver is None:
            raise ValueError("custom_solver callable required when provider='custom'")

    def solve_recaptcha_v2(self, site_key, page_url, invisible=False):
        return self._dispatch("recaptcha_v2", {"sitekey":site_key,"url":page_url,"invisible":invisible})

    def solve_recaptcha_v3(self, site_key, page_url, action="verify", min_score=0.5):
        return self._dispatch("recaptcha_v3", {"sitekey":site_key,"url":page_url,"action":action,"min_score":min_score})

    def solve_hcaptcha(self, site_key, page_url):
        return self._dispatch("hcaptcha", {"sitekey":site_key,"url":page_url})

    def solve_image(self, image_b64, case_sensitive=False):
        return self._dispatch("image", {"image":image_b64,"case_sensitive":case_sensitive})

    def solve_turnstile(self, site_key, page_url):
        return self._dispatch("turnstile", {"sitekey":site_key,"url":page_url})

    def auto_solve(self, page: Any) -> Optional[str]:
        """Auto-detect and solve any CAPTCHA on a Playwright page."""
        html = page.content()
        url  = page.url
        sitekey = self._extract_sitekey(html)
        if sitekey and "recaptcha" in html.lower():
            log.info("Detected reCAPTCHA v2 on %s", url)
            token = self.solve_recaptcha_v2(sitekey, url)
            if token: self._inject_recaptcha(page, token)
            return token
        if "hcaptcha.com" in html and sitekey:
            log.info("Detected hCaptcha on %s", url)
            token = self.solve_hcaptcha(sitekey, url)
            if token: page.evaluate(f"document.querySelector('[name=\"h-captcha-response\"]').value='{token}'")
            return token
        if "turnstile" in html.lower() and sitekey:
            log.info("Detected Cloudflare Turnstile on %s", url)
            token = self.solve_turnstile(sitekey, url)
            if token: page.evaluate(f"document.querySelector('[name=\"cf-turnstile-response\"]').value='{token}'")
            return token
        log.debug("No CAPTCHA detected on %s", url)
        return None

    # ── dispatch ──────────────────────────────────────────────────────
    def _dispatch(self, kind, params):
        try:
            if self.provider == "2captcha":   return self._2captcha(kind, params)
            if self.provider == "capsolver":  return self._capsolver(kind, params)
            if self.provider == "custom":     return self.custom_solver(kind, params)
            raise CaptchaSolverError(f"Unknown provider: {self.provider!r}")
        except CaptchaSolverError:
            if self.soft_fail: log.warning("CAPTCHA failed (soft_fail=True)"); return None
            raise

    # ── 2captcha ──────────────────────────────────────────────────────
    def _2captcha(self, kind, params):
        try: import requests
        except ImportError: raise ImportError("pip install requests")
        base = "https://2captcha.com"
        d: Dict = {"key":self.api_key,"json":1}
        if kind=="image":        d.update({"method":"base64","body":params["image"]})
        elif kind=="recaptcha_v2": d.update({"method":"userrecaptcha","googlekey":params["sitekey"],"pageurl":params["url"],"invisible":1 if params.get("invisible") else 0})
        elif kind=="recaptcha_v3": d.update({"method":"userrecaptcha","version":"v3","googlekey":params["sitekey"],"pageurl":params["url"],"action":params.get("action","verify"),"min_score":params.get("min_score",0.5)})
        elif kind=="hcaptcha":   d.update({"method":"hcaptcha","sitekey":params["sitekey"],"pageurl":params["url"]})
        elif kind=="turnstile":  d.update({"method":"turnstile","sitekey":params["sitekey"],"pageurl":params["url"]})
        else: raise CaptchaSolverError(f"2captcha: unsupported {kind!r}")
        r = requests.post(f"{base}/in.php", data=d, timeout=30).json()
        if r.get("status")!=1: raise CaptchaSolverError(f"2captcha submit: {r}")
        task_id = r["request"]
        deadline = time.time()+self.timeout
        while time.time()<deadline:
            time.sleep(self.poll_interval)
            res = requests.get(f"{base}/res.php", params={"key":self.api_key,"action":"get","id":task_id,"json":1},timeout=30).json()
            if res.get("status")==1: return res["request"]
            if res.get("request")!="CAPCHA_NOT_READY": raise CaptchaSolverError(f"2captcha: {res}")
        raise CaptchaSolverError(f"2captcha timeout after {self.timeout}s")

    # ── CapSolver ─────────────────────────────────────────────────────
    def _capsolver(self, kind, params):
        try: import requests
        except ImportError: raise ImportError("pip install requests")
        base = "https://api.capsolver.com"
        task: Dict = {}
        if kind=="image":        task={"type":"ImageToTextTask","body":params["image"]}
        elif kind=="recaptcha_v2": task={"type":"ReCaptchaV2Task","websiteURL":params["url"],"websiteKey":params["sitekey"]}
        elif kind=="recaptcha_v3": task={"type":"ReCaptchaV3Task","websiteURL":params["url"],"websiteKey":params["sitekey"],"pageAction":params.get("action","verify")}
        elif kind=="hcaptcha":   task={"type":"HCaptchaTask","websiteURL":params["url"],"websiteKey":params["sitekey"]}
        elif kind=="turnstile":  task={"type":"AntiTurnstileTask","websiteURL":params["url"],"websiteKey":params["sitekey"]}
        else: raise CaptchaSolverError(f"CapSolver: unsupported {kind!r}")
        cr = requests.post(f"{base}/createTask",json={"clientKey":self.api_key,"task":task},timeout=30).json()
        if cr.get("errorId")!=0: raise CaptchaSolverError(f"CapSolver create: {cr}")
        task_id = cr["taskId"]
        deadline = time.time()+self.timeout
        while time.time()<deadline:
            time.sleep(self.poll_interval)
            res = requests.post(f"{base}/getTaskResult",json={"clientKey":self.api_key,"taskId":task_id},timeout=30).json()
            if res.get("status")=="ready":
                sol = res.get("solution",{})
                return sol.get("gRecaptchaResponse") or sol.get("text") or sol.get("token") or ""
            if res.get("errorId")!=0: raise CaptchaSolverError(f"CapSolver: {res}")
        raise CaptchaSolverError(f"CapSolver timeout after {self.timeout}s")

    # ── helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _extract_sitekey(html):
        m = re.search(r'data-sitekey=["\']([^"\']+)["\']', html)
        return m.group(1) if m else None

    @staticmethod
    def _inject_recaptcha(page, token):
        page.evaluate(f"""
            var el=document.getElementById('g-recaptcha-response');
            if(el) el.value='{token}';
        """)
