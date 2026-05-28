"""Spydra AI — AISelector: natural language → CSS/XPath selector."""
from __future__ import annotations
import logging, textwrap
from typing import Any, List, Optional

log = logging.getLogger("spydra.ai.selector")

class AISelector:
    """Generate CSS/XPath selectors from plain English and apply them instantly.

    Example::

        from spydra.fetchers import Fetcher
        from spydra.ai import AISelector

        page = Fetcher.get("https://quotes.toscrape.com/")
        elements = AISelector(provider="openai").select(page, "all quote text blocks")
        for el in elements:
            print(el.get_text())
    """
    SYSTEM = textwrap.dedent("""\
        You are an expert at writing CSS and XPath selectors.
        Given a description and HTML snippet, return ONLY the selector string.
        No explanation, no markdown, no quotes. Just the selector.
        Prefer stable attributes (id, data-*, aria-label) over positional selectors.
    """)

    def __init__(self, provider="openai", model=None, api_key=None,
                 selector_type="css", max_retries=2):
        self.provider = provider.lower()
        self.model = model or {"openai":"gpt-4o-mini","anthropic":"claude-haiku-4-5-20251001","ollama":"llama3"}.get(self.provider,"gpt-4o-mini")
        self.api_key = api_key
        self.selector_type = selector_type.lower()
        self.max_retries = max_retries

    def find_selector(self, page: Any, description: str) -> str:
        """Return a CSS/XPath selector string for the described elements."""
        html = (page.html if hasattr(page,"html") else str(page))[:6000]
        prompt = f"Selector type: {self.selector_type.upper()}\nDescription: {description}\n\nHTML:\n{html}"
        raw = self._call_llm(prompt)
        return raw.strip().strip("\"'`")

    def select(self, page: Any, description: str) -> List[Any]:
        """Generate a selector and immediately apply it to the page."""
        selector = self.find_selector(page, description)
        log.debug("AISelector → %r", selector)
        try:
            if self.selector_type == "xpath":
                return list(page.xpath(selector))
            return list(page.css(selector)) if page.css(selector) is not None else []
        except Exception as e:
            log.warning("Selector %r failed: %s", selector, e)
            return []

    def _call_llm(self, prompt):
        if self.provider == "anthropic":
            try: import anthropic
            except ImportError: raise ImportError("pip install anthropic")
            c = anthropic.Anthropic(api_key=self.api_key)
            m = c.messages.create(model=self.model, max_tokens=256, system=self.SYSTEM,
                                  messages=[{"role":"user","content":prompt}])
            return m.content[0].text if m.content else ""
        else:
            try: from openai import OpenAI
            except ImportError: raise ImportError("pip install openai")
            c = OpenAI(api_key=self.api_key)
            r = c.chat.completions.create(model=self.model,
                messages=[{"role":"system","content":self.SYSTEM},{"role":"user","content":prompt}],
                max_tokens=256, temperature=0.0)
            return r.choices[0].message.content or ""
