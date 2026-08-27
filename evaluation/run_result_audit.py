"""Second evidence pass: audits the /m3 page *after* an explanation renders.

The first pass only sees the empty state, so it cannot check the explanation
card itself. This one triggers a real explanation and then measures:

  - heading hierarchy of the rendered result (skipped levels)
  - whether the injected result is announced to assistive tech (live regions)
  - where keyboard focus goes after submitting
  - WCAG 2.1 contrast ratios of every distinct text colour/size combination
    actually rendered on the page, computed from getComputedStyle
  - what happens when the backend is unreachable (error-state copy)
  - stale-result behaviour while a new request is in flight

Usage:  venv\\Scripts\\python.exe evaluation\\run_result_audit.py
"""

import json
import os
import time

from playwright.sync_api import sync_playwright

BASE = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
THEME = os.environ.get("EVAL_THEME", "dark")
HERE = os.path.dirname(os.path.abspath(__file__))
# See run_inspection.py: generated evidence lives beside these scripts, in
# evaluation/Milestone4_Evaluation/, and the directories are created on demand.
OUTPUT = os.environ.get(
    "EVAL_OUTPUT_DIR",
    os.path.join(HERE, "Milestone4_Evaluation"),
)
SHOTS = os.path.join(OUTPUT, "screenshots")
LOGS = os.path.join(OUTPUT, "logs")
os.makedirs(SHOTS, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)

# Walks every text node, resolves the effective background, and returns one row
# per distinct (colour, background, size, weight) combination with its ratio.
CONTRAST_JS = """
() => {
  // Tailwind v4 emits oklch(), which getComputedStyle returns verbatim, so a
  // plain rgb() regex silently drops most of the page. Normalising through a
  // canvas makes the browser itself do the colour-space conversion.
  // Reading the string back from fillStyle still yields oklab for wide-gamut
  // notations, so the colour is rasterised into a 1x1 canvas and the sRGB
  // bytes are read straight out of the pixel buffer. Drawing twice -- once
  // over black, once over white -- recovers the alpha the notation carries.
  const _cv = document.createElement('canvas');
  _cv.width = _cv.height = 1;
  const _ctx = _cv.getContext('2d', { willReadFrequently: true });
  const _sampleOver = (c, base) => {
    _ctx.clearRect(0, 0, 1, 1);
    _ctx.fillStyle = base;
    _ctx.fillRect(0, 0, 1, 1);
    _ctx.fillStyle = c;
    _ctx.fillRect(0, 0, 1, 1);
    const d = _ctx.getImageData(0, 0, 1, 1).data;
    return { r: d[0], g: d[1], b: d[2] };
  };
  const _cache = new Map();
  const parse = (c) => {
    if (!c) return null;
    if (c === 'transparent' || c === 'rgba(0, 0, 0, 0)') {
      return { r: 0, g: 0, b: 0, a: 0 };
    }
    if (_cache.has(c)) return _cache.get(c);
    const onBlack = _sampleOver(c, '#000');
    const onWhite = _sampleOver(c, '#fff');
    // composite over white = a*C + (1-a)*255, over black = a*C
    // so alpha falls out of the difference on any channel.
    const alpha = 1 - (onWhite.r - onBlack.r) / 255;
    let out;
    if (alpha <= 0.004) {
      out = { r: 0, g: 0, b: 0, a: 0 };
    } else {
      out = {
        r: onBlack.r / alpha,
        g: onBlack.g / alpha,
        b: onBlack.b / alpha,
        a: Math.min(1, Math.max(0, alpha)),
      };
    }
    _cache.set(c, out);
    return out;
  };
  const lum = (c) => {
    const f = (v) => {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  const over = (fg, bg) => ({
    r: fg.r * fg.a + bg.r * (1 - fg.a),
    g: fg.g * fg.a + bg.g * (1 - fg.a),
    b: fg.b * fg.a + bg.b * (1 - fg.a),
    a: 1,
  });
  const bgOf = (el) => {
    let node = el;
    let stack = [];
    while (node && node !== document.documentElement) {
      const c = parse(getComputedStyle(node).backgroundColor);
      if (c && c.a > 0) {
        stack.push(c);
        if (c.a === 1) break;
      }
      node = node.parentElement;
    }
    let base = { r: 255, g: 255, b: 255, a: 1 };
    for (let i = stack.length - 1; i >= 0; i--) base = over(stack[i], base);
    return base;
  };

  const rows = new Map();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())) {
    const text = n.textContent.trim();
    if (!text) continue;
    const el = n.parentElement;
    if (!el || !el.offsetParent) continue;
    const cs = getComputedStyle(el);
    const fgRaw = parse(cs.color);
    if (!fgRaw) continue;
    const bg = bgOf(el);
    const fg = over(fgRaw, bg);
    const l1 = lum(fg), l2 = lum(bg);
    const ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
    const px = parseFloat(cs.fontSize);
    const weight = parseInt(cs.fontWeight, 10) || 400;
    const large = px >= 24 || (px >= 18.66 && weight >= 700);
    const required = large ? 3.0 : 4.5;
    const key = [cs.color, Math.round(bg.r) + ',' + Math.round(bg.g) + ',' + Math.round(bg.b), px, weight].join('|');
    if (!rows.has(key)) {
      rows.set(key, {
        color: cs.color,
        background: 'rgb(' + Math.round(bg.r) + ', ' + Math.round(bg.g) + ', ' + Math.round(bg.b) + ')',
        font_px: px,
        weight: weight,
        ratio: Math.round(ratio * 100) / 100,
        required_AA: required,
        passes_AA: ratio >= required,
        sample: text.slice(0, 70),
        count: 1,
      });
    } else {
      rows.get(key).count += 1;
    }
  }
  return [...rows.values()].sort((a, b) => a.ratio - b.ratio);
}
"""

HEADINGS_JS = """
() => [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')]
        .map(h => ({ level: +h.tagName[1], text: (h.textContent || '').trim().slice(0, 70) }))
"""

LIVE_JS = """
() => ({
  liveRegions: [...document.querySelectorAll('[aria-live],[role=status],[role=alert]')]
    .map(el => el.tagName + '/' + (el.getAttribute('aria-live') || el.getAttribute('role'))),
  focused: document.activeElement ? document.activeElement.tagName + ' :: ' +
    (document.activeElement.textContent || '').trim().slice(0, 50) : null,
  busyAttrs: [...document.querySelectorAll('[aria-busy]')].length,
  helpIconsKeyboardReachable: [...document.querySelectorAll('[title]')]
    .filter(el => el.tabIndex >= 0).length,
  helpIconsTotal: document.querySelectorAll('[title]').length,
})
"""

result = {"base_url": BASE, "theme": THEME, "collected_at": time.strftime("%Y-%m-%d %H:%M:%S")}

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                              device_scale_factor=2, color_scheme=THEME)
    page = ctx.new_page()
    page.goto(BASE + "/m3", wait_until="networkidle", timeout=60000)

    # --- state A: empty ---------------------------------------------------
    result["empty_state"] = {
        "headings": page.evaluate(HEADINGS_JS),
        "aria": page.evaluate(LIVE_JS),
    }

    # --- state B: explanation rendered ------------------------------------
    page.get_by_role("button", name="Mid-career manager").click()
    page.wait_for_selector("text=What moved the answer", timeout=30000)
    page.wait_for_timeout(1500)

    result["result_state"] = {
        "headings": page.evaluate(HEADINGS_JS),
        "aria": page.evaluate(LIVE_JS),
        "contrast": page.evaluate(CONTRAST_JS),
    }

    # Which factors are shown vs. which fields the form asked for. The served
    # model drops three inputs; this records whether the interface says so.
    result["form_vs_factors"] = page.evaluate("""
    () => {
      const formLabels = [...document.querySelectorAll('form label > span:first-child')]
        .map(s => s.textContent.replace(/[?]/g, '').trim());
      const factorLabels = [...document.querySelectorAll('li')]
        .map(li => (li.textContent || '').split(':')[0].trim())
        .filter(t => t.length && t.length < 30);
      return { formLabels, factorSample: [...new Set(factorLabels)].slice(0, 25) };
    }
    """)

    # --- state C: keyboard reachability of the "?" help affordance --------
    result["help_affordance"] = page.evaluate("""
    () => {
      const icons = [...document.querySelectorAll('span[title]')];
      return icons.slice(0, 3).map(el => ({
        tag: el.tagName,
        tabIndex: el.tabIndex,
        role: el.getAttribute('role'),
        hasAriaDescribedby: !!el.getAttribute('aria-describedby'),
        onlyTitle: !el.getAttribute('aria-describedby'),
        text: el.getAttribute('title').slice(0, 60),
      }));
    }
    """)

    # --- state D: backend unreachable -------------------------------------
    page.route("**/explain", lambda route: route.abort())
    page.get_by_role("button", name="Part-time clerk").click()
    page.wait_for_timeout(2500)
    err = page.locator("p.text-red-600")
    result["backend_down"] = {
        "error_shown": err.count() > 0,
        "error_text": err.first.inner_text() if err.count() else None,
        "previous_result_still_visible": page.locator(
            "text=What moved the answer").count() > 0,
    }
    page.screenshot(path=os.path.join(SHOTS, "flow-09-backend-unreachable.png"),
                    full_page=True)

    ctx.close()

    # --- state E: the same contrast measurement in the other theme --------
    # The interface has no in-page theme toggle, so which palette a user gets is
    # decided by their OS. Both are therefore shipped surfaces and both have to
    # pass; measuring only one would understate the problem.
    by_theme = {}
    for theme in ("dark", "light"):
        tctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                   device_scale_factor=2, color_scheme=theme)
        tpage = tctx.new_page()
        tpage.goto(BASE + "/m3", wait_until="networkidle", timeout=60000)
        tpage.get_by_role("button", name="Mid-career manager").click()
        tpage.wait_for_selector("text=What moved the answer", timeout=30000)
        tpage.wait_for_timeout(1500)
        rows = tpage.evaluate(CONTRAST_JS)
        failing = [r for r in rows if not r["passes_AA"]]
        by_theme[theme] = {
            "measured": len(rows),
            "failing_AA": len(failing),
            "worst_ratio": rows[0]["ratio"] if rows else None,
            "failing_text_instances": sum(r["count"] for r in failing),
            "rows": rows,
        }
        tctx.close()
    result["contrast_by_theme"] = by_theme

    browser.close()

out = os.path.join(LOGS, "result_audit.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)
print("Wrote " + out)

for theme, data in result["contrast_by_theme"].items():
    print("\n[%s theme] %d combinations measured, %d fail WCAG AA "
          "(%d text instances), worst %.2f:1"
          % (theme, data["measured"], data["failing_AA"],
             data["failing_text_instances"], data["worst_ratio"]))
    for r in [x for x in data["rows"] if not x["passes_AA"]][:12]:
        print("   %.2f:1 (need %.1f) %spx w%d n=%-3d %r"
              % (r["ratio"], r["required_AA"], r["font_px"], r["weight"],
                 r["count"], r["sample"][:50]))
