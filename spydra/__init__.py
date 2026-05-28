__author__ = "Your Name (you@example.com)"
__version__ = "2.0.0"
__copyright__ = "Copyright (c) 2025 Your Name"

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from spydra.parser import Selector, Selectors
    from spydra.core.custom_types import AttributesHandler, TextHandler
    from spydra.fetchers import Fetcher, AsyncFetcher, StealthyFetcher, DynamicFetcher


# Lazy import mapping
_LAZY_IMPORTS = {
    "Fetcher": ("spydra.fetchers", "Fetcher"),
    "Selector": ("spydra.parser", "Selector"),
    "Selectors": ("spydra.parser", "Selectors"),
    "AttributesHandler": ("spydra.core.custom_types", "AttributesHandler"),
    "TextHandler": ("spydra.core.custom_types", "TextHandler"),
    "AsyncFetcher": ("spydra.fetchers", "AsyncFetcher"),
    "StealthyFetcher": ("spydra.fetchers", "StealthyFetcher"),
    "DynamicFetcher": ("spydra.fetchers", "DynamicFetcher"),
}
__all__ = ["Selector", "Fetcher", "AsyncFetcher", "StealthyFetcher", "DynamicFetcher"]


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        module_path, class_name = _LAZY_IMPORTS[name]
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Support for dir() and autocomplete."""
    return sorted(__all__ + ["fetchers", "parser", "cli", "core", "__author__", "__version__", "__copyright__"])

# ── Spydra 2.0 — lazy imports for 3 new features ─────────────────────────────
_LAZY_2 = {
    # Feature 1: AI-native extraction
    "LLMExtractor":    ("spydra.ai.extractor", "LLMExtractor"),
    "ExtractionResult":("spydra.ai.extractor", "ExtractionResult"),
    "SchemaInferrer":  ("spydra.ai.schema",    "SchemaInferrer"),
    "AISelector":      ("spydra.ai.selector",  "AISelector"),
    # Feature 2: Anti-bot bypass
    "FingerprintRotator": ("spydra.antibot.fingerprint","FingerprintRotator"),
    "FingerprintProfile": ("spydra.antibot.fingerprint","FingerprintProfile"),
    "BehaviorProfile":    ("spydra.antibot.behavior",  "BehaviorProfile"),
    "BehaviorEmulator":   ("spydra.antibot.behavior",  "BehaviorEmulator"),
    "CaptchaSolver":      ("spydra.antibot.captcha",   "CaptchaSolver"),
    # Feature 3: Distributed crawling
    "DistSpider":  ("spydra.distributed.spider","DistSpider"),
    "WorkerPool":  ("spydra.distributed.worker","WorkerPool"),
    "JsonSink":    ("spydra.distributed.sinks", "JsonSink"),
    "CsvSink":     ("spydra.distributed.sinks", "CsvSink"),
    "WebhookSink": ("spydra.distributed.sinks", "WebhookSink"),
}

def __getattr__(name):
    # Check existing lazy imports first
    if name in _LAZY_IMPORTS:
        module_path, class_name = _LAZY_IMPORTS[name]
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    # Then check 2.0 features
    if name in _LAZY_2:
        module_path, class_name = _LAZY_2[name]
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    raise AttributeError(f"module 'spydra' has no attribute {name!r}")
