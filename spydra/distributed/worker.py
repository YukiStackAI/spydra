"""Spydra Distributed — WorkerPool: programmatic + CLI worker launcher."""
from __future__ import annotations
import importlib, logging, multiprocessing, os, sys
from typing import Any, Optional

log = logging.getLogger("spydra.distributed.worker")

class WorkerPool:
    """Launch and manage DistSpider worker processes.

    Example::

        from spydra.distributed import WorkerPool
        from myspider import QuoteSpider

        pool = WorkerPool(QuoteSpider, workers=4, redis_url="redis://localhost:6379")
        result = pool.run()
        print(f"Scraped {result['count']} items")
    """
    def __init__(self, spider_class, workers=4, redis_url="redis://localhost:6379/0", timeout=30):
        self.spider_class = spider_class
        self.workers      = workers
        self.redis_url    = redis_url
        self.timeout      = timeout
        self._procs       = []

    def run(self):
        """Seed queue + run all workers. Blocks until complete."""
        spider = self.spider_class()
        spider.workers      = self.workers
        spider.redis_url    = self.redis_url
        spider.queue_timeout = self.timeout
        return spider.start()

    def start_background(self):
        """Start workers as daemon processes (non-blocking)."""
        from spydra.distributed.spider import _worker_entry
        for i in range(self.workers):
            p = multiprocessing.Process(
                target=_worker_entry,
                args=(self.spider_class, self.redis_url, "", "", "", self.timeout),
                name=f"spydra-worker-{i}", daemon=True)
            p.start(); self._procs.append(p)
            log.info("Worker %d started (pid=%d)", i, p.pid)

    def stop(self):
        for p in self._procs:
            if p.is_alive(): p.terminate()
        for p in self._procs: p.join(timeout=5)
        self._procs.clear()

    def status(self):
        return {p.name: {"pid":p.pid,"alive":p.is_alive(),"exitcode":p.exitcode} for p in self._procs}

    def __enter__(self):  self.start_background(); return self
    def __exit__(self, *_): self.stop()


def _load_spider(spec: str):
    """Load spider class from 'module:ClassName' string."""
    if ":" not in spec: raise ValueError(f"Use 'module:ClassName', got {spec!r}")
    mod_path, cls_name = spec.rsplit(":", 1)
    mod = importlib.import_module(mod_path)
    return getattr(mod, cls_name)


def main():
    """CLI: python -m spydra.distributed.worker myspider:QuoteSpider --workers 4"""
    import argparse
    parser = argparse.ArgumentParser(description="Spydra distributed worker launcher")
    parser.add_argument("spider",   help="module:ClassName  e.g. myspider:QuoteSpider")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--redis",  default="redis://localhost:6379/0")
    parser.add_argument("--timeout",type=int, default=30)
    args = parser.parse_args()

    sys.path.insert(0, os.getcwd())
    spider_cls = _load_spider(args.spider)
    pool = WorkerPool(spider_cls, workers=args.workers, redis_url=args.redis, timeout=args.timeout)
    result = pool.run()
    print(f"\n✓ Done — {result['count']} items scraped")


if __name__ == "__main__":
    main()
