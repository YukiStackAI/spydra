"""Spydra AI — LLMExtractor: natural-language data extraction on top of Spydra's parser."""
from __future__ import annotations
import json, logging, textwrap
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

log = logging.getLogger("spydra.ai.extractor")

@dataclass
class ExtractionResult:
    items: List[Dict[str, Any]] = field(default_factory=list)
    schema_used: Optional[Dict] = None
    raw_llm_response: str = ""
    url: str = ""

    def to_json(self, path: str, indent: bool = True) -> None:
        import orjson
        from pathlib import Path
        opts = orjson.OPT_SERIALIZE_NUMPY | (orjson.OPT_INDENT_2 if indent else 0)
        Path(path).write_bytes(orjson.dumps(self.items, option=opts))

    def __len__(self): return len(self.items)
    def __repr__(self): return f"<ExtractionResult items={len(self.items)} url={self.url!r}>"

class LLMExtractor:
    """Extract structured data from any page using plain-English instructions.

    Works with all Spydra fetchers — Fetcher, StealthyFetcher, DynamicFetcher —
    and plugs directly into spider parse() methods without re-fetching.

    Providers: "openai" | "anthropic" | "ollama"

    Example::

        from spydra.ai import LLMExtractor
        extractor = LLMExtractor(provider="anthropic", model="claude-haiku-4-5-20251001")
        result = extractor.extract("https://quotes.toscrape.com/",
                                   "Get all quotes with author and tags")
        for item in result.items:
            print(item)
    """
    SYSTEM = textwrap.dedent("""\
        You are a precise data extraction assistant.
        Return ONLY a valid JSON array of objects — no preamble, no markdown fences.
        If nothing matches, return [].
    """)

    def __init__(self, provider="openai", model=None, api_key=None,
                 base_url=None, max_tokens=4096, temperature=0.0, fetcher="http"):
        self.provider = provider.lower()
        self.model = model or {"openai":"gpt-4o-mini","anthropic":"claude-haiku-4-5-20251001","ollama":"llama3"}.get(self.provider,"gpt-4o-mini")
        self.api_key, self.base_url = api_key, base_url
        self.max_tokens, self.temperature = max_tokens, temperature
        self.fetcher = fetcher

    def extract(self, url, instruction, output_schema=None, css_selector=None, **kw):
        page = self._fetch(url, **kw)
        return self.extract_from_page(page, instruction, output_schema=output_schema, css_selector=css_selector)

    def extract_from_page(self, page, instruction, output_schema=None, css_selector=None):
        content = self._get_content(page, css_selector)
        url = getattr(page, "url", "")
        raw, items = self._run(content, instruction, output_schema)
        return ExtractionResult(items=items, schema_used=output_schema, raw_llm_response=raw, url=url)

    async def extract_async(self, url, instruction, output_schema=None, css_selector=None, **kw):
        page = await self._fetch_async(url, **kw)
        return self.extract_from_page(page, instruction, output_schema=output_schema, css_selector=css_selector)

    def _get_content(self, page, css_selector):
        try:
            from spydra.core.shell import Convertor
            if css_selector:
                els = page.css(css_selector)
                if els: return "\n".join(e.get_text(separator="\n", strip=True) for e in els)
            chunks = list(Convertor._extract_content(page, extraction_type="markdown", main_content_only=True))
            return "\n".join(chunks) if chunks else page.get_text(separator="\n", strip=True)
        except Exception:
            return page.get_text(separator="\n", strip=True) if hasattr(page,"get_text") else str(page)

    def _build_prompt(self, content, instruction, schema):
        parts = [f"INSTRUCTION: {instruction}"]
        if schema: parts.append(f"OUTPUT SCHEMA:\n{json.dumps(schema,indent=2)}")
        parts.append(f"PAGE CONTENT:\n{content[:12000]}")
        return "\n\n".join(parts)

    def _run(self, content, instruction, schema):
        prompt = self._build_prompt(content, instruction, schema)
        if self.provider == "anthropic": raw = self._call_anthropic(prompt)
        elif self.provider == "ollama":  raw = self._call_openai_compat(prompt, base_url=self.base_url or "http://localhost:11434/v1", api_key="ollama")
        else:                            raw = self._call_openai_compat(prompt)
        return raw, self._parse(raw)

    def _call_openai_compat(self, prompt, base_url=None, api_key=None):
        try: from openai import OpenAI
        except ImportError: raise ImportError("pip install openai")
        c = OpenAI(api_key=api_key or self.api_key, base_url=base_url or self.base_url)
        r = c.chat.completions.create(model=self.model,
            messages=[{"role":"system","content":self.SYSTEM},{"role":"user","content":prompt}],
            max_tokens=self.max_tokens, temperature=self.temperature)
        return r.choices[0].message.content or ""

    def _call_anthropic(self, prompt):
        try: import anthropic
        except ImportError: raise ImportError("pip install anthropic")
        c = anthropic.Anthropic(api_key=self.api_key)
        m = c.messages.create(model=self.model, max_tokens=self.max_tokens,
            system=self.SYSTEM, messages=[{"role":"user","content":prompt}])
        return m.content[0].text if m.content else ""

    def _parse(self, raw):
        text = raw.strip()
        if text.startswith("```"): text = "\n".join(text.split("\n")[1:]).rstrip("`").strip()
        try:
            r = json.loads(text)
            if isinstance(r, list): return r
            for v in (r.values() if isinstance(r,dict) else []): 
                if isinstance(v,list): return v
            return [r]
        except json.JSONDecodeError:
            log.warning("LLM returned invalid JSON: %s", raw[:200])
            return []

    def _fetch(self, url, **kw):
        if self.fetcher == "stealthy":
            from spydra.fetchers import StealthyFetcher; return StealthyFetcher.fetch(url,**kw)
        elif self.fetcher == "dynamic":
            from spydra.fetchers import DynamicFetcher; return DynamicFetcher.fetch(url,**kw)
        else:
            from spydra.fetchers import Fetcher; return Fetcher.get(url,**kw)

    async def _fetch_async(self, url, **kw):
        from spydra.fetchers import AsyncFetcher; return await AsyncFetcher.get(url,**kw)
