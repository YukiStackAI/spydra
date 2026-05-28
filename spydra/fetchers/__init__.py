from typing import TYPE_CHECKING, Any
from spydra.engines.toolbelt import ProxyRotator

if TYPE_CHECKING:
    from spydra.fetchers.requests import Fetcher, AsyncFetcher, FetcherSession
    from spydra.fetchers.chrome import DynamicFetcher, DynamicSession, AsyncDynamicSession
    from spydra.fetchers.stealth_chrome import StealthyFetcher, StealthySession, AsyncStealthySession


# Lazy import mapping
_LAZY_IMPORTS = {
    "Fetcher": ("spydra.fetchers.requests", "Fetcher"),
    "AsyncFetcher": ("spydra.fetchers.requests", "AsyncFetcher"),
    "FetcherSession": ("spydra.fetchers.requests", "FetcherSession"),
    "DynamicFetcher": ("spydra.fetchers.chrome", "DynamicFetcher"),
    "DynamicSession": ("spydra.fetchers.chrome", "DynamicSession"),
    "AsyncDynamicSession": ("spydra.fetchers.chrome", "AsyncDynamicSession"),
    "StealthyFetcher": ("spydra.fetchers.stealth_chrome", "StealthyFetcher"),
    "StealthySession": ("spydra.fetchers.stealth_chrome", "StealthySession"),
    "AsyncStealthySession": ("spydra.fetchers.stealth_chrome", "AsyncStealthySession"),
}

__all__ = [
    "Fetcher",
    "AsyncFetcher",
    "ProxyRotator",
    "FetcherSession",
    "DynamicFetcher",
    "DynamicSession",
    "AsyncDynamicSession",
    "StealthyFetcher",
    "StealthySession",
    "AsyncStealthySession",
]


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        module_path, class_name = _LAZY_IMPORTS[name]
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Support for dir() and autocomplete."""
    return sorted(list(_LAZY_IMPORTS.keys()))
