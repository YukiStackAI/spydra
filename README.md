<div align="center">

<img src="docs/assets/logo.png" width="180" alt="Spydra Logo"/>

# 🕷 Spydra

**Undetectable AI-native web scraping framework**

*Distributed crawling · Advanced anti-bot bypass · LLM-powered extraction*

[![PyPI](https://img.shields.io/pypi/v/spydra.svg?color=brightgreen&label=pypi)](https://pypi.org/project/spydra/)
[![Python](https://img.shields.io/pypi/pyversions/spydra)](https://pypi.org/project/spydra/)
[![License: BSD](https://img.shields.io/badge/license-BSD-blue.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/YukiStackAI/spydra?style=social)](https://github.com/YukiStackAI/spydra)

</div>

---

## Install from GitHub

```bash
# Latest stable
pip install git+https://github.com/YukiStackAI/spydra.git

# With browser engines (recommended)
pip install "git+https://github.com/YukiStackAI/spydra.git#egg=spydra[fetchers]"

# AI-native extraction
pip install "git+https://github.com/YukiStackAI/spydra.git#egg=spydra[ai-extract]"

# Anti-bot bypass
pip install "git+https://github.com/YukiStackAI/spydra.git#egg=spydra[antibot]"

# Distributed crawling
pip install "git+https://github.com/YukiStackAI/spydra.git#egg=spydra[distributed]"

# Everything
pip install "git+https://github.com/YukiStackAI/spydra.git#egg=spydra[all]"
```

Or clone and install locally:
```bash
git clone https://github.com/YukiStackAI/spydra.git
cd spydra
pip install -e ".[all]"
```

---

## What is Spydra?

Spydra is a Python web scraping framework with three new superpowers on top of a battle-tested core:

| | Feature | What it does |
|---|---|---|
| 🤖 | **AI-native extraction** | Describe data in English — Spydra extracts it using an LLM |
| 🛡 | **Advanced anti-bot bypass** | Dynamic JS fingerprints, human behavior emulation, CAPTCHA solving |
| ⚡ | **Distributed crawling** | Redis-backed worker pools, stream results to JSON / CSV / webhooks |

---

## Core features (original)

### Fast HTTP scraping

```python
from spydra import Fetcher

page = Fetcher.get("https://quotes.toscrape.com/")
for quote in page.css(".quote"):
    print(quote.css("span.text::text").get())
    print(quote.css("small.author::text").get())
```

### Cloudflare / bot-protected sites

```python
from spydra import StealthyFetcher

page = StealthyFetcher.fetch("https://protected-site.com")
print(page.status)  # 200
```

### JavaScript-rendered pages

```python
from spydra import DynamicFetcher

page = DynamicFetcher.fetch("https://spa-site.com", wait_selector=".results")
data = page.css(".product-title::text").getall()
```

### Full spider with auto-pagination

```python
from spydra.spiders.spider import Spider
from spydra.spiders.request import Request

class QuoteSpider(Spider):
    name = "quotes"
    start_urls = ["https://quotes.toscrape.com/"]

    async def parse(self, response):
        for quote in response.css(".quote"):
            yield {
                "text":   quote.css("span.text::text").get(),
                "author": quote.css("small.author::text").get(),
                "tags":   quote.css("a.tag::text").getall(),
            }
        next_page = response.css("li.next a::attr(href)").get()
        if next_page:
            yield Request(response.urljoin(next_page))

result = QuoteSpider().start()
print(f"Scraped {len(result.items)} quotes")
```

---

## 🤖 Feature 1 — AI-native extraction

```python
from spydra.ai import LLMExtractor

# Works with OpenAI, Anthropic, or local Ollama
extractor = LLMExtractor(provider="openai", model="gpt-4o-mini")

result = extractor.extract(
    url="https://quotes.toscrape.com/",
    instruction="Get all quotes with author name and tags",
)
for item in result.items:
    print(item)
# → [{"quote": "...", "author": "Einstein", "tags": [...]}, ...]

result.to_json("quotes.json")
```

**Auto-generate a Pydantic schema from any URL:**

```python
from spydra.ai import SchemaInferrer

schema = SchemaInferrer(provider="openai").infer("https://books.toscrape.com/")
print(schema.json_schema())      # → {"type": "object", "properties": {...}}
BookModel = schema.to_pydantic() # → live Pydantic v2 model
```

**Natural-language CSS selectors:**

```python
from spydra.ai import AISelector
from spydra import Fetcher

page     = Fetcher.get("https://quotes.toscrape.com/")
elements = AISelector(provider="openai").select(page, "all author names")
```

Supported providers: `openai` · `anthropic` · `ollama`

---

## 🛡 Feature 2 — Advanced anti-bot bypass

```python
from spydra.antibot import FingerprintRotator, BehaviorEmulator, BehaviorProfile, CaptchaSolver

# 1. Rotate JS fingerprint (Canvas, WebGL, AudioContext, screen, platform)
rotator = FingerprintRotator(strategy="random")
profile  = rotator.generate()
page = StealthyFetcher.fetch(url, extra_headers=profile.extra_headers)

# Inject into Playwright page
rotator.patch_playwright_page(playwright_page, profile)

# 2. Human behavioral emulation
emulator = BehaviorEmulator(BehaviorProfile(scroll=True, mouse_jitter=True, typing_wpm=52))
emulator.goto(playwright_page, "https://example.com/login")
emulator.type_text(playwright_page, "input#email", "user@example.com")
emulator.click(playwright_page, "button[type=submit]")

# 3. CAPTCHA solving
solver = CaptchaSolver(provider="2captcha", api_key="YOUR_KEY")
solver.auto_solve(playwright_page)             # auto-detect any CAPTCHA
solver.solve_recaptcha_v2("6Le-...", page_url) # explicit
solver.solve_hcaptcha("sitekey", page_url)
solver.solve_turnstile("sitekey", page_url)
```

---

## ⚡ Feature 3 — Distributed crawling

```python
from spydra.distributed import DistSpider, JsonSink
from spydra.spiders.request import Request

class QuoteSpider(DistSpider):
    name       = "quotes"
    start_urls = ["https://quotes.toscrape.com/"]
    redis_url  = "redis://localhost:6379/0"
    workers    = 4                          # parallel worker processes
    sink       = JsonSink("quotes.jsonl")   # real-time streaming output

    async def parse(self, response):
        for quote in response.css(".quote"):
            yield {
                "text":   quote.css("span.text::text").get(),
                "author": quote.css("small.author::text").get(),
            }
        nxt = response.css("li.next a::attr(href)").get()
        if nxt:
            yield Request(response.urljoin(nxt))

QuoteSpider().start()
```

**Multi-machine crawl:**

```bash
# Start Redis first
docker run -d -p 6379:6379 redis

# Machine A — seeds queue + 2 workers
python -m spydra.distributed.worker myspider:QuoteSpider --workers 2 --redis redis://HOST:6379

# Machine B — joins same queue
python -m spydra.distributed.worker myspider:QuoteSpider --workers 2 --redis redis://HOST:6379
```

**Available sinks:**

```python
from spydra.distributed import JsonSink, CsvSink, WebhookSink

JsonSink("out.jsonl")                              # streaming JSON Lines
JsonSink("out.json", format="json", indent=True)  # pretty JSON array
CsvSink("out.csv")                                 # CSV (headers auto-detected)
WebhookSink("https://api.example.com/ingest",
            batch_size=50,
            headers={"Authorization": "Bearer TOKEN"})
```

---

## Install options

| Command | What you get |
|---|---|
| `pip install "git+https://github.com/YukiStackAI/spydra.git"` | Core only |
| `pip install "git+...#egg=spydra[fetchers]"` | + all fetchers + Spider |
| `pip install "git+...#egg=spydra[ai-extract]"` | + LLM extraction |
| `pip install "git+...#egg=spydra[antibot]"` | + fingerprint + CAPTCHA |
| `pip install "git+...#egg=spydra[distributed]"` | + Redis workers + sinks |
| `pip install "git+...#egg=spydra[all]"` | Everything |

---

## Requirements

- Python 3.10+
- Redis *(distributed feature only)* — `docker run -d -p 6379:6379 redis`

## License

BSD License — see [LICENSE](LICENSE)
