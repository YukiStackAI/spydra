"""Spydra Distributed — Sinks: streaming result outputs (JSON, CSV, Webhook)."""
from __future__ import annotations
import asyncio, csv, json, logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("spydra.distributed.sinks")


class ResultSink(ABC):
    @abstractmethod
    async def write(self, item: Dict[str, Any]) -> None: ...
    async def flush(self) -> None: pass


class JsonSink(ResultSink):
    """Stream results to JSON Lines or a JSON array file.

    Example::

        sink = JsonSink("results.jsonl")          # streaming — one JSON per line
        sink = JsonSink("results.json", format="json", indent=True)  # pretty array
    """
    def __init__(self, path, format="jsonl", indent=False):
        self.path = Path(path)
        self.format = format.lower()
        self.indent = indent
        self._items: List[Dict] = []
        self._lock = asyncio.Lock()
        self._fh = None
        if self.format == "jsonl":
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(self.path, "a", encoding="utf-8")

    async def write(self, item):
        async with self._lock:
            if self.format == "jsonl":
                self._fh.write(json.dumps(item, default=str, ensure_ascii=False) + "\n")
                self._fh.flush()
            else:
                self._items.append(item)

    async def flush(self):
        async with self._lock:
            if self.format == "json":
                self.path.parent.mkdir(parents=True, exist_ok=True)
                opts = {"indent":2} if self.indent else {}
                self.path.write_text(json.dumps(self._items, default=str, ensure_ascii=False, **opts), encoding="utf-8")
                log.info("JsonSink: %d items → %s", len(self._items), self.path)
            elif self._fh and not self._fh.closed:
                self._fh.close()
                log.info("JsonSink: closed %s", self.path)

    def __del__(self):
        if self._fh and not self._fh.closed: self._fh.close()


class CsvSink(ResultSink):
    """Stream results to a CSV file. Headers inferred from first item.

    Example::

        sink = CsvSink("results.csv")
        sink = CsvSink("results.csv", fieldnames=["title","price","url"])
    """
    def __init__(self, path, fieldnames=None, delimiter=",", encoding="utf-8-sig"):
        self.path = Path(path)
        self.fieldnames = fieldnames
        self.delimiter = delimiter
        self.encoding = encoding
        self._lock = asyncio.Lock()
        self._writer = None
        self._fh = None
        self._count = 0

    def _init_writer(self, item):
        if self._writer: return
        if not self.fieldnames: self.fieldnames = list(item.keys())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "w", newline="", encoding=self.encoding)
        self._writer = csv.DictWriter(self._fh, fieldnames=self.fieldnames,
                                      delimiter=self.delimiter, extrasaction="ignore")
        self._writer.writeheader()

    async def write(self, item):
        async with self._lock:
            self._init_writer(item)
            flat = {k: json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in item.items()}
            self._writer.writerow(flat)
            self._fh.flush()
            self._count += 1

    async def flush(self):
        async with self._lock:
            if self._fh and not self._fh.closed:
                self._fh.close()
                log.info("CsvSink: %d rows → %s", self._count, self.path)

    def __del__(self):
        if self._fh and not self._fh.closed: self._fh.close()


class WebhookSink(ResultSink):
    """POST results in batches to an HTTP endpoint.

    Example::

        sink = WebhookSink("https://api.example.com/ingest",
                           batch_size=50,
                           headers={"Authorization": "Bearer TOKEN"},
                           retry_on_fail=3)
    """
    def __init__(self, url, batch_size=100, headers=None, timeout=30, retry_on_fail=3):
        self.url = url
        self.batch_size = batch_size
        self.headers = {"Content-Type":"application/json", **(headers or {})}
        self.timeout = timeout
        self.retry = retry_on_fail
        self._buf: List[Dict] = []
        self._lock = asyncio.Lock()
        self._sent = self._failed = 0

    async def write(self, item):
        async with self._lock:
            self._buf.append(item)
            if len(self._buf) >= self.batch_size:
                batch, self._buf = self._buf[:], []
                await self._post(batch)

    async def flush(self):
        async with self._lock:
            if self._buf:
                await self._post(self._buf[:])
                self._buf.clear()
        log.info("WebhookSink: sent=%d failed=%d → %s", self._sent, self._failed, self.url)

    async def _post(self, batch):
        payload = json.dumps(batch, default=str)
        for attempt in range(self.retry+1):
            try:
                try: import httpx
                except ImportError:
                    import aiohttp  # type: ignore
                    async with aiohttp.ClientSession(headers=self.headers) as s:
                        async with s.post(self.url, data=payload,
                                          timeout=aiohttp.ClientTimeout(total=self.timeout)) as r:
                            r.raise_for_status(); self._sent+=len(batch); return

                async with httpx.AsyncClient() as c:
                    r = await c.post(self.url, content=payload, headers=self.headers, timeout=self.timeout)
                    r.raise_for_status(); self._sent+=len(batch); return
            except Exception as e:
                if attempt < self.retry:
                    await asyncio.sleep(2**attempt)
                else:
                    self._failed+=len(batch)
                    log.error("WebhookSink: gave up on %d items: %s", len(batch), e)
