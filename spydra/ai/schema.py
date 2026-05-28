"""Spydra AI — SchemaInferrer: point at a URL, get a Pydantic schema back."""
from __future__ import annotations
import json, logging, textwrap
from typing import Any, Dict, Optional

log = logging.getLogger("spydra.ai.schema")

class InferredSchema:
    def __init__(self, schema: Dict, url: str = ""):
        self._schema, self.url = schema, url

    def json_schema(self): return self._schema

    def to_pydantic(self):
        try: from pydantic import create_model
        except ImportError: raise ImportError("pip install pydantic>=2")
        _map = {"string":str,"integer":int,"number":float,"boolean":bool,"array":list,"object":dict}
        req = set(self._schema.get("required",[]))
        fields = {}
        for name, prop in self._schema.get("properties",{}).items():
            t = _map.get(prop.get("type","string"), str)
            fields[name] = (t, ...) if name in req else (Optional[t], None)
        return create_model("InferredModel", **fields)

    def __repr__(self):
        return f"<InferredSchema fields={list(self._schema.get('properties',{}).keys())} url={self.url!r}>"

class SchemaInferrer:
    """Auto-generate a JSON schema / Pydantic model from any URL.

    Example::

        schema = SchemaInferrer(provider="openai").infer("https://books.toscrape.com/")
        print(schema.json_schema())
        BookModel = schema.to_pydantic()
    """
    SYSTEM = textwrap.dedent("""\
        Analyse web page content and return a JSON Schema (draft-07) describing
        the repeating structured data. Output ONLY valid JSON, no markdown.
        Schema is for a single ITEM. Use simple types. Add "description" per property.
        Mark always-present fields as "required".
    """)

    def __init__(self, provider="openai", model=None, api_key=None, fetcher="http"):
        self.provider = provider.lower()
        self.model = model or {"openai":"gpt-4o-mini","anthropic":"claude-haiku-4-5-20251001","ollama":"llama3"}.get(self.provider,"gpt-4o-mini")
        self.api_key, self.fetcher = api_key, fetcher

    def infer(self, url, hint=None, **kw):
        page = self._fetch(url, **kw)
        return self.infer_from_page(page, hint=hint)

    def infer_from_page(self, page, hint=None):
        content = self._get_content(page)
        url = getattr(page, "url", "")
        prompt = "Return the JSON Schema for the main data items on this page.\n"
        if hint: prompt += f"Focus on: {hint}\n"
        prompt += f"\nPAGE CONTENT:\n{content[:10000]}"
        raw = self._call_llm(prompt)
        text = raw.strip()
        if text.startswith("```"): text = "\n".join(text.split("\n")[1:]).rstrip("`").strip()
        try: schema = json.loads(text)
        except: schema = {"type":"object","properties":{}}
        return InferredSchema(schema=schema, url=url)

    def _get_content(self, page):
        try:
            from spydra.core.shell import Convertor
            chunks = list(Convertor._extract_content(page, extraction_type="markdown", main_content_only=True))
            return "\n".join(chunks) if chunks else page.get_text(separator="\n", strip=True)
        except: return page.get_text(separator="\n", strip=True) if hasattr(page,"get_text") else str(page)

    def _call_llm(self, prompt):
        if self.provider == "anthropic":
            try: import anthropic
            except ImportError: raise ImportError("pip install anthropic")
            c = anthropic.Anthropic(api_key=self.api_key)
            m = c.messages.create(model=self.model, max_tokens=1024, system=self.SYSTEM,
                                  messages=[{"role":"user","content":prompt}])
            return m.content[0].text if m.content else ""
        else:
            try: from openai import OpenAI
            except ImportError: raise ImportError("pip install openai")
            c = OpenAI(api_key=self.api_key)
            r = c.chat.completions.create(model=self.model,
                messages=[{"role":"system","content":self.SYSTEM},{"role":"user","content":prompt}],
                max_tokens=1024, temperature=0.0)
            return r.choices[0].message.content or ""

    def _fetch(self, url, **kw):
        if self.fetcher == "stealthy":
            from spydra.fetchers import StealthyFetcher; return StealthyFetcher.fetch(url,**kw)
        elif self.fetcher == "dynamic":
            from spydra.fetchers import DynamicFetcher; return DynamicFetcher.fetch(url,**kw)
        else:
            from spydra.fetchers import Fetcher; return Fetcher.get(url,**kw)
