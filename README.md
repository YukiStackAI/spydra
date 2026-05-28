<div align="center">

<img src="docs/assets/logo.png" width="180" alt="Spydra Logo"/>

# 🕷 Spydra

**Undetectable AI-native web scraping framework**

*Distributed crawling · Advanced anti-bot bypass · LLM-powered extraction*

[![License: BSD](https://img.shields.io/badge/license-BSD-blue.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/YukiStackAI/spydra?style=social)](https://github.com/YukiStackAI/spydra)

---

</div>

## 🚀 What is Spydra?

Spydra is a high-performance Python web scraping framework that brings three new superpowers on top of a battle-tested core:

| | Feature | What it does |
|---|---|---|
| 🤖 | **AI-native extraction** | Describe data in English — Spydra extracts it using an LLM. |
| 🛡 | **Advanced anti-bot bypass** | Dynamic JS fingerprints, human behavior emulation, and automated CAPTCHA solving. |
| ⚡ | **Distributed crawling** | Redis-backed worker pools to stream results directly to JSON, CSV, or Webhooks. |

---

## 📦 Installation

Since Spydra `2.0.0` is officially on PyPI, you can now install it cleanly via pip:

```bash
pip install spydra
```

### Advanced Installation Options

Tailor Spydra to your exact needs by installing only the features you require:

| Command | Features Included |
|---------|-------------------|
| `pip install "spydra[fetchers]"` | Core + Browser engines (Playwright) + Spider framework |
| `pip install "spydra[ai-extract]"` | Core + LLM extraction support |
| `pip install "spydra[antibot]"` | Core + Fingerprint generation + CAPTCHA solvers |
| `pip install "spydra[distributed]"` | Core + Redis workers + Data Sinks |
| `pip install "spydra[all]"` | **Everything included** |

*(For development, you can clone the repository and run `pip install -e ".[all]"`, or use `git+https://github.com/YukiStackAI/spydra.git`)*

---

## 📖 Quick Start & Core Features

### Fast HTTP Scraping

```python
from spydra import Fetcher

page = Fetcher.get("https://quotes.toscrape.com/")
for quote in page.css(".quote"):
    print(quote.css("span.text::text").get())
    print(quote.css("small.author::text").get())
```

### Defeat Cloudflare & Bot Protection

```python
from spydra import StealthyFetcher

page = StealthyFetcher.fetch("https://protected-site.com")
print(page.status)  # 200 OK
```

### Render JavaScript (SPA)

```python
from spydra import DynamicFetcher

page = DynamicFetcher.fetch("https://spa-site.com", wait_selector=".results")
data = page.css(".product-title::text").getall()
```

### Build Scalable Spiders

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

## 🤖 Feature Deep Dive

### 1. AI-native extraction
Extract strictly typed, structured data from any website just by describing it. 

```python
from spydra.ai import LLMExtractor

# Supports OpenAI, Anthropic, or local Ollama
extractor = LLMExtractor(provider="openai", model="gpt-4o-mini")

result = extractor.extract(
    url="https://quotes.toscrape.com/",
    instruction="Get all quotes with author name and tags",
)

result.to_json("quotes.json")
```

**Generate Pydantic schemas automatically:**
```python
from spydra.ai import SchemaInferrer

schema = SchemaInferrer(provider="openai").infer("https://books.toscrape.com/")
BookModel = schema.to_pydantic() # → live Pydantic v2 model
```

### 2. Advanced anti-bot bypass
Seamlessly bypass sophisticated bot-protection systems without getting blocked.

```python
from spydra.antibot import FingerprintRotator, BehaviorEmulator, BehaviorProfile, CaptchaSolver

# 1. Rotate JS fingerprints (Canvas, WebGL, AudioContext, screen, platform)
rotator = FingerprintRotator(strategy="random")
profile = rotator.generate()
page = StealthyFetcher.fetch(url, extra_headers=profile.extra_headers)

# 2. Emulate human behavior 
emulator = BehaviorEmulator(BehaviorProfile(scroll=True, mouse_jitter=True, typing_wpm=52))
emulator.goto(playwright_page, "https://example.com/login")
emulator.type_text(playwright_page, "input#email", "user@example.com")
emulator.click(playwright_page, "button[type=submit]")

# 3. Solve CAPTCHAs automatically
solver = CaptchaSolver(provider="2captcha", api_key="YOUR_KEY")
solver.auto_solve(playwright_page)
```

### 3. Distributed crawling
Scale up your scraping across multiple machines with a Redis-backed queue system.

```python
from spydra.distributed import DistSpider, JsonSink
from spydra.spiders.request import Request

class QuoteSpider(DistSpider):
    name       = "quotes"
    start_urls = ["https://quotes.toscrape.com/"]
    redis_url  = "redis://localhost:6379/0"
    workers    = 4                          # Number of parallel workers
    sink       = JsonSink("quotes.jsonl")   # Real-time streaming output

    async def parse(self, response):
        # Your scraping logic here
        pass

QuoteSpider().start()
```

Launch multiple workers across different machines to consume the same queue:
```bash
python -m spydra.distributed.worker myspider:QuoteSpider --workers 2 --redis redis://HOST:6379
```

---

## 📋 Requirements

- **Python:** 3.10+
- **Redis:** *(Optional, required only for distributed crawling)*

## ⚖️ License

Spydra is licensed under the **BSD License**. See [LICENSE](LICENSE) for more details.
