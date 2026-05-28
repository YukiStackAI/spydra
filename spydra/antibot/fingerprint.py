"""Spydra AntiBot — FingerprintRotator: JS-level browser fingerprint rotation."""
from __future__ import annotations
import hashlib, json, logging, random, time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("spydra.antibot.fingerprint")

_SCREENS: List[Tuple[int,int]] = [(1920,1080),(1366,768),(1440,900),(1536,864),
    (1280,800),(1600,900),(2560,1440),(1280,1024),(1024,768),(1920,1200)]
_HW: List[int] = [2,4,6,8,12,16]
_PLATFORMS: List[str] = ["Win32","Win32","Win32","MacIntel","Linux x86_64"]
_TIMEZONES: List[str] = ["America/New_York","America/Chicago","America/Los_Angeles",
    "Europe/London","Europe/Berlin","Asia/Tokyo","Asia/Kolkata","America/Sao_Paulo"]
_CHROME: List[str] = ["124.0.0.0","125.0.0.0","126.0.0.0","127.0.0.0","128.0.0.0","129.0.0.0","130.0.0.0"]
_WEBGL: List[Tuple[str,str]] = [
    ("Google Inc. (NVIDIA)","ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (Intel)","ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (AMD)","ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)","ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Apple","Apple M1"),("Google Inc. (Intel)","ANGLE (Intel, Intel Iris Pro OpenGL Engine, OpenGL 4.1)"),
]
_UA_PLAT = {"Win32":"Windows NT 10.0; Win64; x64","MacIntel":"Macintosh; Intel Mac OS X 10_15_7","Linux x86_64":"X11; Linux x86_64"}
_UA = "Mozilla/5.0 ({platform}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome} Safari/537.36"

@dataclass
class FingerprintProfile:
    """A single consistent browser fingerprint profile."""
    user_agent: str
    platform: str
    screen_width: int
    screen_height: int
    hardware_concurrency: int
    timezone_id: str
    canvas_noise_seed: int
    webgl_vendor: str
    webgl_renderer: str
    do_not_track: Optional[str]
    chrome_version: str
    extra_headers: Dict[str,str] = field(default_factory=dict)

    @property
    def viewport(self): return {"width":self.screen_width,"height":self.screen_height-90}

    def fingerprint_hash(self):
        key = f"{self.user_agent}|{self.platform}|{self.screen_width}x{self.screen_height}"
        return hashlib.sha1(key.encode(),usedforsecurity=False).hexdigest()[:12]

    def to_playwright_init_script(self) -> str:
        """Returns a JS snippet — inject via page.add_init_script() before page.goto()."""
        s = self.canvas_noise_seed
        return f"""
(function(){{
  Object.defineProperty(navigator,'platform',{{get:()=>'{self.platform}'}});
  Object.defineProperty(navigator,'hardwareConcurrency',{{get:()=>{self.hardware_concurrency}}});
  Object.defineProperty(navigator,'doNotTrack',{{get:()=>{json.dumps(self.do_not_track)}}});
  Object.defineProperty(screen,'width',{{get:()=>{self.screen_width}}});
  Object.defineProperty(screen,'height',{{get:()=>{self.screen_height}}});
  Object.defineProperty(screen,'availWidth',{{get:()=>{self.screen_width}}});
  Object.defineProperty(screen,'availHeight',{{get:()=>{self.screen_height-48}}});
  const _gid=CanvasRenderingContext2D.prototype.getImageData;
  CanvasRenderingContext2D.prototype.getImageData=function(x,y,w,h){{
    const d=_gid.call(this,x,y,w,h);let r={s};
    for(let i=0;i<d.data.length;i+=97){{r=(r*1664525+1013904223)&0xffffffff;d.data[i]=(d.data[i]+(r&3))&255;}}
    return d;
  }};
  const _gp=WebGLRenderingContext.prototype.getParameter;
  WebGLRenderingContext.prototype.getParameter=function(p){{
    if(p===37445)return'{self.webgl_vendor}';
    if(p===37446)return'{self.webgl_renderer}';
    return _gp.call(this,p);
  }};
}})();""".strip()

class FingerprintRotator:
    """Generate and rotate browser fingerprint profiles.

    Example::

        rotator = FingerprintRotator(strategy="random")
        profile  = rotator.generate()
        page = StealthyFetcher.fetch(url, extra_headers=profile.extra_headers)
        # For Playwright: rotator.patch_playwright_page(pw_page, profile)
    """
    def __init__(self, strategy="random", ttl=3600, seed=None):
        self.strategy = strategy
        self.ttl = ttl
        self._rng = random.Random(seed)
        self._current: Optional[FingerprintProfile] = None
        self._ts = 0.0

    def generate(self) -> FingerprintProfile:
        if self.strategy == "consistent" and self._current and (time.time()-self._ts) < self.ttl:
            return self._current
        p = self._build()
        self._current, self._ts = p, time.time()
        log.debug("Fingerprint generated: %s", p.fingerprint_hash())
        return p

    def _build(self) -> FingerprintProfile:
        r = self._rng
        w, h = r.choice(_SCREENS)
        cv = r.choice(_CHROME)
        pl = r.choice(_PLATFORMS)
        ua = _UA.format(platform=_UA_PLAT.get(pl,"Windows NT 10.0; Win64; x64"), chrome=cv)
        wv, wr = r.choice(_WEBGL)
        return FingerprintProfile(
            user_agent=ua, platform=pl, screen_width=w, screen_height=h,
            hardware_concurrency=r.choice(_HW), timezone_id=r.choice(_TIMEZONES),
            canvas_noise_seed=r.randint(0,0xFFFFFFFF), webgl_vendor=wv, webgl_renderer=wr,
            do_not_track=r.choice([None,None,None,"1"]), chrome_version=cv,
            extra_headers={"User-Agent":ua,"Accept-Language":r.choice(["en-US,en;q=0.9","en-GB,en;q=0.9"])},
        )

    def patch_playwright_page(self, page: Any, profile: Optional[FingerprintProfile]=None) -> FingerprintProfile:
        """Inject fingerprint into an active Playwright page before navigation."""
        if profile is None: profile = self.generate()
        try:
            page.add_init_script(script=profile.to_playwright_init_script())
            page.set_extra_http_headers(profile.extra_headers)
            page.set_viewport_size(profile.viewport)
        except Exception as e:
            log.warning("Fingerprint inject failed: %s", e)
        return profile
