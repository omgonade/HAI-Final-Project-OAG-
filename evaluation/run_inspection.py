"""Automated evidence-collection pass for the Milestone 4 evaluation.

Drives the running prototype with Playwright and records, per page:
  - full-page screenshots at desktop (1440x900) and mobile (390x844)
  - console errors / page errors / network failures
  - a keyboard tab-order trace (first 40 stops)
  - accessibility probes: images without alt, buttons/links with no accessible
    name, form controls with no associated label, <details> state, heading
    order, title-attribute tooltips, ARIA live regions
  - horizontal-overflow check per viewport

Everything written under logs/ is raw observation, not interpretation; the
severity ratings live in the evaluation workbook, not here.

Usage:  venv\\Scripts\\python.exe evaluation\\run_inspection.py
"""

import json
import os
import time

from playwright.sync_api import sync_playwright

BASE = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
# The interface is theme-aware via prefers-color-scheme and has no in-page
# toggle, so the theme is a property of the viewer, not the app. Chromium
# defaults to light, which is NOT what most users see -- capture dark.
THEME = os.environ.get("EVAL_THEME", "dark")
HERE = os.path.dirname(os.path.abspath(__file__))
# Generated evidence is written next to the script that produces it, so a
# fresh clone gets the whole evaluation -- code and evidence -- in one folder.
# The directories below are created on demand, so nothing has to exist first.
OUTPUT = os.environ.get(
    "EVAL_OUTPUT_DIR",
    os.path.join(HERE, "Milestone4_Evaluation"),
)
SHOTS = os.path.join(OUTPUT, "screenshots")
LOGS = os.path.join(OUTPUT, "logs")
os.makedirs(SHOTS, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)

DESKTOP = {"width": 1440, "height": 900}
MOBILE = {"width": 390, "height": 844}

PAGES = [
    ("landing", "/"),
    ("m3-explain", "/m3"),
    ("m3-how-it-works", "/m3/how-it-works"),
    ("m3-fairness", "/m3/fairness"),
    ("m3-about", "/m3/about"),
    ("m2-predict", "/m2"),
]

AUDIT_JS = """
() => {
  const name = (el) => (
    el.getAttribute('aria-label') ||
    el.getAttribute('title') ||
    (el.textContent || '').trim()
  );
  const imgs = [...document.querySelectorAll('img')]
    .filter(i => !i.hasAttribute('alt'))
    .map(i => i.getAttribute('src'));
  const unnamed = [...document.querySelectorAll('button, a')]
    .filter(el => !name(el))
    .map(el => el.tagName + ':' + el.outerHTML.slice(0, 90));
  const unlabelled = [...document.querySelectorAll('input, select, textarea')]
    .filter(el => {
      if (el.getAttribute('aria-label')) return false;
      if (el.id && document.querySelector('label[for="' + el.id + '"]')) return false;
      return !el.closest('label');
    })
    .map(el => el.tagName + '[' + (el.getAttribute('type') || '') + ']:' + el.outerHTML.slice(0, 90));
  const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')]
    .map(h => ({ level: +h.tagName[1], text: (h.textContent || '').trim().slice(0, 80) }));
  const details = [...document.querySelectorAll('details')].map(d => ({
    open: d.open,
    summary: (d.querySelector('summary')?.textContent || '').trim().slice(0, 90),
  }));
  const titleTooltips = [...document.querySelectorAll('[title]')]
    .map(el => ({ tag: el.tagName, title: el.getAttribute('title').slice(0, 120) }));
  const liveRegions = [...document.querySelectorAll('[aria-live],[role=status],[role=alert]')]
    .map(el => el.tagName + '/' + (el.getAttribute('aria-live') || el.getAttribute('role')));
  return {
    imgsWithoutAlt: imgs,
    controlsWithoutName: unnamed,
    inputsWithoutLabel: unlabelled,
    headings,
    details,
    titleTooltips,
    liveRegions,
    horizontalOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  };
}
"""

TAB_TRACE_JS = """
() => {
  const el = document.activeElement;
  if (!el || el === document.body) return 'BODY';
  const label = (el.getAttribute('aria-label') || (el.textContent || '').trim() ||
                 el.getAttribute('placeholder') || '').slice(0, 55);
  return el.tagName + (el.type ? '[' + el.type + ']' : '') + ' :: ' +
         label.replace(/\\s+/g, ' ');
}
"""

report = {
    "base_url": BASE,
    "theme": THEME,
    "collected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "pages": {},
}


def attach_listeners(page, sink):
    def on_console(m):
        if m.type in ("error", "warning"):
            sink["console"].append(m.type + ": " + m.text[:200])

    page.on("console", on_console)
    page.on("pageerror", lambda e: sink["pageerrors"].append(str(e)[:200]))
    page.on(
        "requestfailed",
        lambda r: sink["requestfailed"].append(
            r.method + " " + r.url[:120] + " :: " + str(r.failure)
        ),
    )


def tab_trace(page, stops=40):
    page.keyboard.press("Tab")
    trace, seen_body = [], 0
    for _ in range(stops):
        trace.append(page.evaluate(TAB_TRACE_JS))
        if trace[-1] == "BODY":
            seen_body += 1
            if seen_body > 1:
                break
        page.keyboard.press("Tab")
    return trace


def text_or_none(page, pattern):
    loc = page.locator(pattern)
    return loc.first.inner_text() if loc.count() else None


with sync_playwright() as p:
    browser = p.chromium.launch()

    # ---- pass 1: every page, desktop + mobile ---------------------------
    for slug, path in PAGES:
        entry = {"path": path}
        for label, viewport in (("desktop", DESKTOP), ("mobile", MOBILE)):
            ctx = browser.new_context(viewport=viewport, device_scale_factor=2,
                                      color_scheme=THEME)
            page = ctx.new_page()
            sink = {"console": [], "pageerrors": [], "requestfailed": []}
            attach_listeners(page, sink)
            t0 = time.time()
            page.goto(BASE + path, wait_until="networkidle", timeout=60000)
            entry[label + "_load_ms"] = round((time.time() - t0) * 1000)
            page.wait_for_timeout(800)
            page.screenshot(
                path=os.path.join(SHOTS, slug + "--" + label + ".png"), full_page=True
            )
            entry[label + "_audit"] = page.evaluate(AUDIT_JS)
            entry[label + "_events"] = sink
            if label == "desktop":
                entry["tab_order"] = tab_trace(page)
            ctx.close()
        report["pages"][slug] = entry
        print("[captured] " + slug)

    # ---- pass 2: the explanation flow, the heart of Milestone 3 ---------
    ctx = browser.new_context(viewport=DESKTOP, device_scale_factor=2,
                              color_scheme=THEME)
    page = ctx.new_page()
    sink = {"console": [], "pageerrors": [], "requestfailed": []}
    attach_listeners(page, sink)

    explain_calls = []
    page.on(
        "response",
        lambda r: explain_calls.append(r.url) if "/explain" in r.url else None,
    )

    page.goto(BASE + "/m3", wait_until="networkidle", timeout=60000)
    flow = {}

    page.screenshot(path=os.path.join(SHOTS, "flow-01-empty-state.png"), full_page=True)

    # preset: predicted above 50K
    t0 = time.time()
    page.get_by_role("button", name="Mid-career manager").click()
    page.wait_for_selector("text=The model", timeout=30000)
    flow["preset_high_latency_ms"] = round((time.time() - t0) * 1000)
    page.wait_for_timeout(1200)
    page.screenshot(
        path=os.path.join(SHOTS, "flow-02-result-above50k.png"), full_page=True
    )

    # preset: predicted at or below 50K -> recourse should be forward-looking
    t0 = time.time()
    page.get_by_role("button", name="Part-time clerk").click()
    page.wait_for_timeout(1500)
    flow["preset_low_latency_ms"] = round((time.time() - t0) * 1000)
    page.screenshot(
        path=os.path.join(SHOTS, "flow-03-result-below50k.png"), full_page=True
    )

    # expand the fairness probe (collapsed by default)
    page.locator("details").last.click()
    page.wait_for_timeout(600)
    page.screenshot(
        path=os.path.join(SHOTS, "flow-04-fairness-probe-open.png"), full_page=True
    )

    # the "models disagree" preset
    page.get_by_role("button", name="Where the two models disagree").click()
    page.wait_for_timeout(1500)
    page.screenshot(
        path=os.path.join(SHOTS, "flow-05-models-disagree.png"), full_page=True
    )

    # invalid input handling
    age = page.locator("input[inputmode=numeric]").first
    age.fill("abc")
    page.wait_for_timeout(400)
    flow["invalid_text_error"] = text_or_none(page, "text=/whole number/i")
    page.screenshot(path=os.path.join(SHOTS, "flow-06-invalid-input.png"), full_page=True)
    flow["submit_disabled_on_error"] = page.get_by_role(
        "button", name="Predict and explain"
    ).is_disabled()

    age.fill("999")
    page.wait_for_timeout(400)
    flow["out_of_range_error"] = text_or_none(page, "text=/Must be between/i")
    page.screenshot(
        path=os.path.join(SHOTS, "flow-07-out-of-range.png"), full_page=True
    )
    age.fill("37")
    page.wait_for_timeout(300)

    # currency switch, an affordance inherited from Milestone 2
    if page.get_by_role("button", name="INR").count():
        page.get_by_role("button", name="INR").click()
        page.wait_for_timeout(500)
        page.screenshot(
            path=os.path.join(SHOTS, "flow-08-currency-inr.png"), full_page=True
        )

    flow["events"] = sink
    flow["explain_calls"] = len(explain_calls)
    report["explanation_flow"] = flow
    ctx.close()

    browser.close()

out = os.path.join(LOGS, "inspection_log.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print("\nWrote " + out)
print("Screenshots in " + SHOTS)
