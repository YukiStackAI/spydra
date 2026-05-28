"""Spydra Distributed — DistSpider: drop-in Spider replacement backed by Redis."""
from __future__ import annotations
import asyncio, json, logging, multiprocessing, os, time
from typing import Any, Optional

log = logging.getLogger("spydra.distributed.spider")

class DistSpider:
    """Distributed spider backed by a Redis URL queue.

    Drop-in replacement for Spydra's Spider — same parse(), on_start(),
    configure_sessions() API. Only the base class changes.

    Class attributes::

        redis_url     = "redis://localhost:6379/0"
        workers       = 4          # local worker processes
        queue_timeout = 30         # seconds idle before worker exits
        sink          = JsonSink("out.jsonl")   # optional streaming sink
        clear_on_start = True      # wipe queue on fresh run

    Example::

        class QuoteSpider(DistSpider):
            name = "quotes"
            start_urls = ["https://quotes.toscrape.com/"]
            redis_url  = "redis://localhost:6379/0"
            workers    = 4
            sink       = JsonSink("quotes.jsonl")

            async def parse(self, response):
                for q in response.css(".quote"):
                    yield {"text": q.css("span.text::text").get()}
                nxt = response.css("li.next a::attr(href)").get()
                if nxt:
                    from spydra.spiders.request import Request
                    yield Request(response.urljoin(nxt))

        QuoteSpider().start()
    """

    # ── class-level config (override in subclass) ─────────────────────
    name: str = "dist_spider"
    start_urls: list = []
    redis_url: str = os.getenv("SPYDRA_REDIS_URL", "redis://localhost:6379/0")
    workers: int = 1
    queue_key: str = ""
    seen_key: str = ""
    result_key: str = ""
    queue_timeout: int = 30
    sink: Any = None
    clear_on_start: bool = True

    # Inherit all Spider options
    follow_robots: bool = False
    max_retries: int = 3
    concurrency: int = 5

    def __init__(self):
        if not self.queue_key:  self.queue_key  = f"spydra:{self.name}:queue"
        if not self.seen_key:   self.seen_key   = f"spydra:{self.name}:seen"
        if not self.result_key: self.result_key = f"spydra:{self.name}:results"
        self._redis = None
        # Import and initialise the real Spider engine components
        try:
            from spydra.spiders.spider import Spider
            self._spider_cls = Spider
        except Exception:
            self._spider_cls = None

    # ── Redis helpers ─────────────────────────────────────────────────
    def _r(self):
        if self._redis: return self._redis
        try: import redis as _r
        except ImportError: raise ImportError("pip install redis")
        self._redis = _r.from_url(self.redis_url, decode_responses=True)
        return self._redis

    def _push_url(self, url, priority=0):
        r = self._r()
        if r.sadd(self.seen_key, url):
            r.zadd(self.queue_key, {url: -priority})

    def _pop_url(self):
        res = self._r().zpopmin(self.queue_key, 1)
        return res[0][0] if res else None

    def _push_result(self, item):
        self._r().rpush(self.result_key, json.dumps(item, default=str))

    def _qlen(self): return self._r().zcard(self.queue_key)

    # ── Public start ──────────────────────────────────────────────────
    def start(self):
        """Seed queue, spawn workers, return results."""
        import anyio
        r = self._r()
        if self.clear_on_start:
            r.delete(self.queue_key, self.seen_key, self.result_key)
        for url in self.start_urls:
            self._push_url(url)
        log.info("DistSpider %r: %d URLs → %d worker(s)", self.name, len(self.start_urls), self.workers)

        if self.workers > 1:
            return self._multiprocess()
        return anyio.run(self._crawl_loop, backend="asyncio")

    def _multiprocess(self):
        procs = []
        for i in range(self.workers):
            p = multiprocessing.Process(
                target=_worker_entry,
                args=(self.__class__, self.redis_url, self.queue_key,
                      self.seen_key, self.result_key, self.queue_timeout),
                name=f"spydra-worker-{i}", daemon=False)
            p.start(); procs.append(p)
            log.info("Spawned worker %d (pid=%d)", i, p.pid)
        for p in procs: p.join()
        return self._collect()

    # ── Core async crawl loop ─────────────────────────────────────────
    async def _crawl_loop(self):
        from spydra.spiders.request import Request
        items = []
        idle_since = None

        await self.on_start()

        while True:
            url = self._pop_url()
            if url is None:
                if idle_since is None: idle_since = time.time()
                elif time.time()-idle_since > self.queue_timeout:
                    log.info("Queue idle %ds — exiting", self.queue_timeout); break
                await asyncio.sleep(1); continue

            idle_since = None
            try:
                response = await self._fetch(url)
                async for out in self.parse(response):
                    if isinstance(out, Request):
                        self._push_url(out.url, getattr(out,"priority",0))
                    elif isinstance(out, dict) and out:
                        out = await self.on_scraped_item(out)
                        if out:
                            items.append(out)
                            self._push_result(out)
                            if self.sink:
                                await self.sink.write(out)
            except Exception as e:
                log.error("Error on %s: %s", url, e)

        await self.on_close()
        if self.sink:
            await self.sink.flush()
        return {"items": items, "count": len(items)}

    async def _fetch(self, url):
        """Fetch using Spydra's existing HTTP fetcher (async)."""
        from spydra.fetchers import AsyncFetcher
        return await AsyncFetcher.get(url)

    def _collect(self):
        r = self._r()
        raw = r.lrange(self.result_key, 0, -1)
        items = [json.loads(i) for i in raw]
        return {"items": items, "count": len(items)}

    # ── Hooks (override these in your spider) ─────────────────────────
    async def on_start(self): pass
    async def on_close(self): pass
    async def on_scraped_item(self, item): return item
    async def parse(self, response):
        raise NotImplementedError("Implement parse() in your DistSpider subclass")
        yield  # make it an async generator


def _worker_entry(spider_cls, redis_url, queue_key, seen_key, result_key, timeout):
    """Subprocess entry — must be top-level for pickle."""
    import anyio
    spider = spider_cls.__new__(spider_cls)
    spider.redis_url    = redis_url
    spider.queue_key    = queue_key
    spider.seen_key     = seen_key
    spider.result_key   = result_key
    spider.queue_timeout = timeout
    spider.workers      = 1
    spider.clear_on_start = False
    spider._redis       = None
    if spider.sink is None:
        pass  # no sink in subprocess, results go to Redis
    anyio.run(spider._crawl_loop, backend="asyncio")
