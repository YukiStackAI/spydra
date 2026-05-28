# Spydra — GitHub Push & PyPI Publish Guide

Step-by-step instructions to push your project to GitHub and publish it on PyPI
so anyone can `pip install spydra`.

---

## STEP 1 — Create the GitHub repository

1. Go to https://github.com/new
2. Fill in:
   - **Repository name:** `spydra`
   - **Description:** `Undetectable AI-native web scraping. Distributed crawling, advanced anti-bot bypass, LLM-powered extraction.`
   - **Visibility:** Public (required for free PyPI publishing)
   - ❌ Do NOT tick "Add a README" — you already have one
3. Click **Create repository**
4. Copy the URL shown — it looks like `https://github.com/YOUR_USERNAME/spydra.git`

---

## STEP 2 — Set your author info in pyproject.toml

Open `pyproject.toml` and replace the placeholder values:

```toml
authors = [{name = "Your Real Name", email = "your@email.com"}]

[project.urls]
Homepage      = "https://github.com/YOUR_USERNAME/spydra"
Documentation = "https://github.com/YOUR_USERNAME/spydra#readme"
Repository    = "https://github.com/YOUR_USERNAME/spydra"
"Bug Tracker" = "https://github.com/YOUR_USERNAME/spydra/issues"
```

---

## STEP 3 — Set up Git and push

Open a terminal in the `spydra/` folder and run these commands one by one:

```bash
# 1. Initialise git (if not already done)
git init

# 2. Tell git who you are
git config user.name  "Your Real Name"
git config user.email "your@email.com"

# 3. Create a .gitignore so junk files don't get uploaded
cat > .gitignore << 'EOF'
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/
*.whl
.env
.venv
venv/
env/
*.log
.DS_Store
.idea/
.vscode/
*.sqlite
*.db
EOF

# 4. Add all files
git add .

# 5. First commit
git commit -m "feat: Spydra 2.0.0 — AI extraction, anti-bot bypass, distributed crawling"

# 6. Set the main branch name
git branch -M main

# 7. Connect to your GitHub repo (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/spydra.git

# 8. Push!
git push -u origin main
```

After this, visit `https://github.com/YOUR_USERNAME/spydra` — your project is live.

---

## STEP 4 — Publish to PyPI

Anyone will be able to `pip install spydra` once you do this.

### 4a — Create a PyPI account
Go to https://pypi.org/account/register/ and create an account.
Verify your email address.

### 4b — Create an API token
1. Go to https://pypi.org/manage/account/token/
2. Click **Add API token**
3. Name it `spydra-publish`
4. Scope: **Entire account** (first time) or the `spydra` project after first upload
5. Copy the token — it starts with `pypi-`

### 4c — Install publishing tools

```bash
pip install build twine
```

### 4d — Build the distribution

```bash
cd spydra/   # make sure you're in the project root
python -m build
```

This creates two files in `dist/`:
- `spydra-2.0.0-py3-none-any.whl`   ← wheel (fast install)
- `spydra-2.0.0.tar.gz`              ← source distribution

### 4e — Upload to PyPI

```bash
twine upload dist/*
```

When prompted:
- **Username:** `__token__`   (literally type `__token__`)
- **Password:** paste your `pypi-...` token

### 4f — Verify it works

```bash
pip install spydra
python -c "import spydra; print(spydra.__version__)"
# → 2.0.0
```

---

## STEP 5 — Create a GitHub Release (optional but professional)

1. Go to your repo → **Releases** → **Create a new release**
2. **Tag:** `v2.0.0`
3. **Title:** `Spydra v2.0.0 — AI-native scraping`
4. **Description:**

```
## What's new in 2.0.0

### 🤖 Feature 1 — AI-native extraction
- `LLMExtractor`: extract structured data with plain-English instructions
- `SchemaInferrer`: auto-generate Pydantic schemas from any URL
- `AISelector`: natural-language → CSS/XPath selectors
- Supports OpenAI, Anthropic Claude, and local Ollama models

### 🛡 Feature 2 — Advanced anti-bot bypass
- `FingerprintRotator`: dynamic JS fingerprint rotation (Canvas, WebGL, AudioContext, screen, platform)
- `BehaviorEmulator`: cubic Bezier mouse movement, eased scroll physics, WPM-matched typing
- `CaptchaSolver`: reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile, image CAPTCHAs via 2captcha/CapSolver

### ⚡ Feature 3 — Distributed crawling
- `DistSpider`: drop-in Spider replacement backed by Redis
- `WorkerPool`: multi-machine worker launcher with CLI
- `JsonSink`, `CsvSink`, `WebhookSink`: streaming real-time result outputs

### Core (unchanged)
- All existing Fetcher, StealthyFetcher, DynamicFetcher, Spider features intact
```

5. Attach `dist/spydra-2.0.0-py3-none-any.whl` as a release asset
6. Click **Publish release**

---

## STEP 6 — Future updates

When you add features or fix bugs:

```bash
# 1. Make your changes
# 2. Bump version in pyproject.toml: version = "2.1.0"
# 3. Commit and push
git add .
git commit -m "feat: add XYZ"
git push

# 4. Rebuild and re-publish
python -m build
twine upload dist/*
```

---

## Folder structure your repo will have

```
spydra/
├── spydra/                  ← Python package
│   ├── __init__.py          ← version, lazy imports
│   ├── parser.py            ← core HTML parser (Selector)
│   ├── cli.py               ← spydra CLI command
│   ├── fetchers/            ← Fetcher, StealthyFetcher, DynamicFetcher
│   ├── spiders/             ← Spider, Request, CrawlResult
│   ├── engines/             ← HTTP + browser engines
│   ├── core/                ← storage, shell, translator, AI (MCP)
│   ├── ai/                  ← NEW: LLMExtractor, SchemaInferrer, AISelector
│   ├── antibot/             ← NEW: FingerprintRotator, BehaviorEmulator, CaptchaSolver
│   └── distributed/         ← NEW: DistSpider, WorkerPool, JsonSink, CsvSink, WebhookSink
├── tests/                   ← test suite
├── docs/                    ← documentation
├── examples/                ← example spiders
├── pyproject.toml           ← package metadata + dependencies
├── README.md                ← this file
└── LICENSE                  ← BSD license
```

---

## Common issues

**`twine upload` says "File already exists"**
→ You already uploaded that version. Bump the version number in `pyproject.toml` and rebuild.

**`git push` asks for a password**
→ GitHub no longer accepts passwords. Use a Personal Access Token:
  1. https://github.com/settings/tokens → Generate new token (classic)
  2. Tick `repo` scope
  3. Use the token as your password when pushing

**`pip install spydra` installs old version**
→ PyPI caches for ~5 min. Wait and try `pip install spydra --no-cache-dir`
