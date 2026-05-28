"""Spydra AntiBot — BehaviorEmulator: human-like mouse, scroll, and typing on Playwright pages."""
from __future__ import annotations
import asyncio, logging, math, random, time
from dataclasses import dataclass
from typing import Any, Optional, Tuple

log = logging.getLogger("spydra.antibot.behavior")

@dataclass
class BehaviorProfile:
    scroll: bool = True
    mouse_jitter: bool = True
    typing_wpm: int = 60
    min_action_delay: float = 0.3
    max_action_delay: float = 1.8
    scroll_distance_range: Tuple[int,int] = (200,600)
    scroll_steps: int = 8
    random_seed: Optional[int] = None

class BehaviorEmulator:
    """Emulate human behavior on Playwright pages to defeat behavioral bot-detection.

    Example::

        emulator = BehaviorEmulator(BehaviorProfile(scroll=True, mouse_jitter=True, typing_wpm=52))
        emulator.goto(page, "https://example.com/login")
        emulator.type_text(page, "input#email", "user@example.com")
        emulator.click(page, "button[type=submit]")
    """
    def __init__(self, profile: Optional[BehaviorProfile]=None):
        self.p = profile or BehaviorProfile()
        self._rng = random.Random(self.p.random_seed)

    # ── Sync API ──────────────────────────────────────────────────────
    def goto(self, page, url, wait_until="domcontentloaded"):
        page.goto(url, wait_until=wait_until)
        self._post_load(page)

    def click(self, page, selector, move_first=True):
        el = page.query_selector(selector)
        if el is None: raise ValueError(f"Not found: {selector!r}")
        box = el.bounding_box()
        if box and move_first:
            self._mouse_move(page, box["x"]+box["width"]/2, box["y"]+box["height"]/2)
        self._delay(); el.click(); self._delay(0.1,0.5)

    def type_text(self, page, selector, text):
        self.click(page, selector)
        if self.p.typing_wpm <= 0: page.fill(selector, text); return
        d = (self.p.typing_wpm*5/60.0)**-1
        for ch in text:
            page.keyboard.type(ch)
            time.sleep(max(0.02, d + self._rng.uniform(-d*0.3, d*0.5)))

    def scroll_page(self, page, direction="down", times=3):
        for _ in range(times):
            px = self._rng.randint(*self.p.scroll_distance_range) * (-1 if direction=="up" else 1)
            self._scroll(page, px); self._delay(0.4,1.2)

    def hover(self, page, selector):
        el = page.query_selector(selector)
        if el:
            box = el.bounding_box()
            if box: self._mouse_move(page, box["x"]+box["width"]/2, box["y"]+box["height"]/2)

    # ── Async API ─────────────────────────────────────────────────────
    async def a_goto(self, page, url, wait_until="domcontentloaded"):
        await page.goto(url, wait_until=wait_until); await self._a_post_load(page)

    async def a_click(self, page, selector):
        el = await page.query_selector(selector)
        if el is None: raise ValueError(f"Not found: {selector!r}")
        box = await el.bounding_box()
        if box: await self._a_mouse_move(page, box["x"]+box["width"]/2, box["y"]+box["height"]/2)
        await self._a_delay(); await el.click()

    async def a_type_text(self, page, selector, text):
        await self.a_click(page, selector)
        d = (self.p.typing_wpm*5/60.0)**-1
        for ch in text:
            await page.keyboard.type(ch)
            await asyncio.sleep(max(0.02, d+self._rng.uniform(-d*0.3, d*0.5)))

    async def a_scroll_page(self, page, direction="down", times=3):
        for _ in range(times):
            px = self._rng.randint(*self.p.scroll_distance_range) * (-1 if direction=="up" else 1)
            await self._a_scroll(page, px); await self._a_delay(0.4,1.2)

    # ── Internals ─────────────────────────────────────────────────────
    def _delay(self, lo=None, hi=None):
        time.sleep(self._rng.uniform(lo or self.p.min_action_delay, hi or self.p.max_action_delay))

    async def _a_delay(self, lo=None, hi=None):
        await asyncio.sleep(self._rng.uniform(lo or self.p.min_action_delay, hi or self.p.max_action_delay))

    def _bezier(self, t, p0, p1, p2, p3):
        u=1-t
        return (u**3*p0[0]+3*u**2*t*p1[0]+3*u*t**2*p2[0]+t**3*p3[0],
                u**3*p0[1]+3*u**2*t*p1[1]+3*u*t**2*p2[1]+t**3*p3[1])

    def _mouse_move(self, page, tx, ty, steps=25):
        try:
            cx,cy = self._rng.uniform(100,800), self._rng.uniform(100,600)
            cp1 = (cx+self._rng.uniform(-150,150), cy+self._rng.uniform(-100,100))
            cp2 = (tx+self._rng.uniform(-150,150), ty+self._rng.uniform(-100,100))
            for i in range(steps+1):
                t = i/steps; te=t*t*(3-2*t)
                mx,my = self._bezier(te,(cx,cy),cp1,cp2,(tx,ty))
                if self.p.mouse_jitter and 0<i<steps:
                    mx+=self._rng.uniform(-1.5,1.5); my+=self._rng.uniform(-1.5,1.5)
                page.mouse.move(mx,my); time.sleep(self._rng.uniform(0.005,0.018))
        except Exception as e: log.debug("Mouse move (non-fatal): %s",e)

    async def _a_mouse_move(self, page, tx, ty, steps=25):
        try:
            cx,cy = self._rng.uniform(100,800), self._rng.uniform(100,600)
            cp1 = (cx+self._rng.uniform(-150,150), cy+self._rng.uniform(-100,100))
            cp2 = (tx+self._rng.uniform(-150,150), ty+self._rng.uniform(-100,100))
            for i in range(steps+1):
                t=i/steps; te=t*t*(3-2*t)
                mx,my=self._bezier(te,(cx,cy),cp1,cp2,(tx,ty))
                if self.p.mouse_jitter and 0<i<steps:
                    mx+=self._rng.uniform(-1.5,1.5); my+=self._rng.uniform(-1.5,1.5)
                await page.mouse.move(mx,my); await asyncio.sleep(self._rng.uniform(0.005,0.018))
        except Exception as e: log.debug("Async mouse move (non-fatal): %s",e)

    def _scroll(self, page, total_px):
        step = total_px/self.p.scroll_steps
        for i in range(self.p.scroll_steps):
            p=(i+1)/self.p.scroll_steps; e=p*p*(3-2*p)
            page.mouse.wheel(0, step*(1+math.sin(math.pi*e)*0.3))
            time.sleep(self._rng.uniform(0.03,0.08))

    async def _a_scroll(self, page, total_px):
        step = total_px/self.p.scroll_steps
        for i in range(self.p.scroll_steps):
            p=(i+1)/self.p.scroll_steps; e=p*p*(3-2*p)
            await page.mouse.wheel(0, step*(1+math.sin(math.pi*e)*0.3))
            await asyncio.sleep(self._rng.uniform(0.03,0.08))

    def _post_load(self, page):
        self._delay(0.5,1.5)
        if self.p.scroll: self.scroll_page(page, times=self._rng.randint(1,3))
        self._delay(0.3,0.8)

    async def _a_post_load(self, page):
        await self._a_delay(0.5,1.5)
        if self.p.scroll: await self.a_scroll_page(page, times=self._rng.randint(1,3))
        await self._a_delay(0.3,0.8)
