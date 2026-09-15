"""Contract tests for scroll performance ("small jerk on scroll").

Root cause, measured with a headless-Chrome probe that wrapped the forced-layout
read accessors (``offsetHeight``/``offsetWidth``/``offsetTop``/
``getBoundingClientRect``/``scrollTop``/``scrollHeight``/``clientHeight``/
``getComputedStyle``) with a call-site-attributing counter and drove a 20-step
scroll burst from the top of the page at DPR 2 (1440x900, document height
8341px, http://127.0.0.1:8111/):

* BEFORE - 926 forced layout reads for 20 scroll events (46 per event, 83 on the
  first event, 185 peak) and a 18.2ms frame median with 33 of 130 frames over
  20ms. The reads were attributed to:
  - ``assets/js/jquery.sticky.js`` (302) - the tick called
    ``$(document).height()`` and did 4 live ``offset()``/``outerHeight()`` reads
    *after* it had written ``width``/``position``/``top``, and ``metricsDirty``
    was never cleared, so the "cached" geometry was re-read on every tick;
  - ``assets/js/jquery.appear.js`` (197) - ``.appear()`` binds one ``scroll``
    handler PER ELEMENT (8 progress bars) running ``$(el).is(':visible')`` +
    ``offset()`` + ``height()`` on every event;
  - ``assets/js/bootsnav.js`` - three independent ``$(window).on("scroll")``
    handlers, each with its own live ``$(window).scrollTop()`` and an
    unconditional class write on the fixed, backdrop-filtered navbar.
* The user-visible "small jerk" is that mixture: the tick's write -> read pair
  forces a synchronous reflow inside the scroll frame (so the compositor scrolls
  on while the fixed navbar is repositioned a frame late), the redundant class /
  inline-style writes re-invalidate the blurred fixed layer every frame, and a
  global ``html { scroll-behavior: smooth }`` re-timed every programmatic scroll
  that ``custom.js`` already animates with ``easeInOutExpo``.

* AFTER - the assertions below pin the fix: the sticky scroll tick is write-only
  against cached geometry (``metricsDirty = false``), bootsnav has ONE passive
  rAF-coalesced scroll dispatcher, the progress bars are revealed with an
  ``IntersectionObserver`` instead of ``.appear()``, and ``html`` no longer
  declares ``scroll-behavior: smooth`` while JS owns programmatic scrolling.
  Re-measured with the same probe: 5 forced layout reads per scroll event.

These are pure text assertions on the live (comment-stripped) source, in the same
style as ``test_nav_scroll_contract.py`` - CSS/JS comments are stripped so a
comment that *documents* the old behaviour stays legal.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CUSTOM_JS = ROOT / "assets" / "js" / "custom.js"
STICKY_JS = ROOT / "assets" / "js" / "jquery.sticky.js"
ASTRA_JS = ROOT / "assets" / "js" / "astra3d.js"
PARALLAX_JS = ROOT / "assets" / "js" / "parallax3d.js"
BOOTSNAV_JS = ROOT / "assets" / "js" / "bootsnav.js"
STYLE_CSS = ROOT / "assets" / "css" / "style.css"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _live(text: str) -> str:
    """Drop ``/* ... */``, ``//`` and ``<!-- ... -->`` comments."""
    text = re.sub(r"/\*[\s\S]*?\*/", " ", text)
    text = re.sub(r"<!--[\s\S]*?-->", " ", text)
    return re.sub(r"(?m)^\s*//.*$", " ", text)


# --------------------------------------------------------------------------- #
# jquery.sticky.js - the hot path
# --------------------------------------------------------------------------- #
def test_sticky_scroll_work_is_coalesced_into_one_frame():
    """Scroll events must be coalesced, not one full layout pass per event."""
    js = _live(_read(STICKY_JS))

    assert "requestAnimationFrame" in js, (
        "the sticky scroll pass must be rAF-coalesced: a wheel burst must cost "
        "one pass per frame, not one per scroll event"
    )
    assert re.search(r"addEventListener\(\s*['\"]scroll['\"]\s*,\s*scheduleScroller", js), (
        "the scroll listener must be the coalescing scheduler, not the raw scroller"
    )


def test_sticky_scroll_listener_is_passive():
    """A non-passive scroll listener blocks the compositor's scroll handling."""
    js = _live(_read(STICKY_JS))

    assert re.search(r"addEventListener\(\s*['\"]scroll['\"]\s*,[^)]*passive\s*:\s*true", js), (
        "the sticky scroll listener must be registered `{ passive: true }`"
    )


def test_sticky_does_not_read_layout_per_scroll_tick():
    """The per-tick `offset()`/`outerHeight()` + `css('height')` thrash must stay gone."""
    js = _live(_read(STICKY_JS))

    assert not re.search(
        r"stickyWrapper\.css\(\s*['\"]height['\"]\s*,\s*s\.stickyElement\.outerHeight\(\)\s*\)", js
    ), (
        "the wrapper height must not be re-read AND re-written on every scroll "
        "tick - that read/write pair forced a synchronous reflow per event"
    )
    assert "refreshMetrics" in js and "metricsDirty" in js, (
        "the geometry must be cached (`refreshMetrics`) and invalidated only on "
        "resize / DOM mutation (`metricsDirty`)"
    )
    assert re.search(r"wrapperHeight\s*!==\s*s\.elementHeight", js), (
        "the wrapper height write must be guarded by an actual change"
    )
    assert re.search(r"elementTop\s*=\s*s\.elementTop", js), (
        "the per-tick element position must come from the cache, not a live offset()"
    )


# --------------------------------------------------------------------------- #
# custom.js - the back-to-top handler
# --------------------------------------------------------------------------- #
def test_return_to_top_scroll_handler_is_raf_coalesced():
    """No `.fadeIn()`/`.fadeOut()` jQuery animation may run per scroll event."""
    js = _live(_read(CUSTOM_JS))

    handler = re.search(r"\$\(window\)\.on\(\s*['\"]scroll['\"][\s\S]*?\n\s*\}\);", js)
    assert handler, "the return-to-top scroll handler must exist"

    body = handler.group(0)
    assert "requestAnimationFrame" in body, (
        "the scroll handler must defer its work to one rAF tick"
    )
    assert "fadeIn" not in body and "fadeOut" not in body, (
        "the scroll handler must not start a jQuery fade per scroll event: each "
        "call runs the `:visible` filter (forced reflow) and queues an animation"
    )
    assert re.search(r"(shouldShow\s*===\s*returnTopShown|returnTopShown\s*===\s*shouldShow)", js), (
        "the fade must be guarded by a visibility state change, not fired per event"
    )


# --------------------------------------------------------------------------- #
# one background driver at a time
# --------------------------------------------------------------------------- #
def test_webgl_takes_the_stage_over_from_the_css_parallax_driver():
    """parallax3d.js is parsed before the deferred astra3d.js, so its own guard
    cannot fire: the handover must be explicit, or both drivers animate every
    scroll frame (one of them writing transforms on display:none layers)."""
    astra = _live(_read(ASTRA_JS))
    parallax = _live(_read(PARALLAX_JS))

    assert re.search(r"P3D\.destroy\(", astra), (
        "astra3d.js must hand the stage over (window.P3D.destroy()) once WebGL boots"
    )
    assert re.search(r"destroy\s*:\s*function", parallax), (
        "parallax3d.js must expose a destroy() that stops its loop + listeners"
    )
    assert re.search(r"P3D\.revive\(", astra), (
        "if WebGL is lost, astra3d.js must revive the CSS driver instead of "
        "leaving the stage dead"
    )


# --------------------------------------------------------------------------- #
# no native smooth scroll on top of the JS animation
# --------------------------------------------------------------------------- #
def test_no_global_smooth_scroll_fights_the_js_animation():
    """`scroll-behavior: smooth` must not be declared while JS owns the scrolling.

    custom.js animates every in-page jump itself (`$(...)..animate({scrollTop},
    900, 'easeInOutExpo')`), re-snaps the landing in `align()` and animates the
    back-to-top button. A native smooth-scroll animation on the same scroller
    cannot be combined with those writes: the browser re-times/competes with the
    jQuery curve and the page visibly stutters mid-flight. JS owns programmatic
    scrolling, so the native behaviour is `auto` - the smooth landing is
    unchanged because jQuery animates it.
    """
    css = _live(_read(STYLE_CSS))
    js = _live(_read(CUSTOM_JS))

    assert not re.search(r"scroll-behavior\s*:\s*smooth", css), (
        "`scroll-behavior: smooth` must not be declared while custom.js owns "
        "programmatic scrolling - the two smooth-scroll animations fight"
    )
    assert re.search(r"scroll-behavior\s*:\s*auto", css), (
        "html must pin the native behaviour to `auto`"
    )
    # ...and the JS animation that replaces it must still exist
    assert re.search(r"\.animate\(\s*\{[^}]*scrollTop", js), (
        "the programmatic jump must still be animated by custom.js"
    )
    assert "easeInOutExpo" in js, "the animated jump must keep its easing"


# --------------------------------------------------------------------------- #
# the sticky tick must not read layout at all
# --------------------------------------------------------------------------- #
def test_sticky_tick_trusts_its_geometry_cache():
    """A `metricsDirty` flag that is never cleared means the cache is ignored.

    That was the actual defect behind the tick cost: the read pass ran (and
    re-read `$(document).height()`, `offset()` and `outerHeight()`) on *every*
    scroll event, right after the write pass had invalidated the layout.
    """
    js = _live(_read(STICKY_JS))

    assert re.search(r"metricsDirty\s*=\s*false", js), (
        "the read pass must clear metricsDirty, otherwise the cached geometry is "
        "re-read - and layout re-flushed - on every scroll tick"
    )
    assert "refreshPageMetrics" in js, (
        "the page-level geometry ($(document).height() / viewport) must be cached "
        "too: it used to be re-read per scroll event"
    )

    body = js[js.index("scroller = function"):]
    body = body[:body.index("resizer = function")]
    for read in (".offset(", ".outerHeight(", ".height(", "getBoundingClientRect"):
        assert read not in body, (
            "the scroll tick must be write-only against the cached geometry "
            "(refreshMetrics / refreshPageMetrics); a live `%s` in the tick "
            "forces a synchronous reflow inside the scroll frame:\n%s" % (read, body)
        )
    assert "$window.scrollTop()" in body, (
        "the tick still needs the scroll position - it must keep using "
        "`$window.scrollTop()`, which is `pageYOffset` and does not touch layout"
    )
    assert re.search(r"if\s*\(\s*unstick\s*!==\s*s\.unstuck\s*\)", js), (
        "the unstick/re-pin style write must be guarded by a state change: it "
        "used to rewrite position/top/bottom/z-index on the fixed, blurred "
        "navbar on every event"
    )
    assert re.search(r"metricsDirty = true", js) and re.search(r"ResizeObserver", js), (
        "the cache must be invalidated by resize / DOM mutation / page growth "
        "(ResizeObserver on <body>), not by re-reading layout every tick"
    )


# --------------------------------------------------------------------------- #
# bootsnav's three scroll handlers -> one passive coalesced dispatcher
# --------------------------------------------------------------------------- #
def test_bootsnap_scroll_handlers_are_one_passive_coalesced_listener():
    """No per-handler `$(window).on("scroll")` + live `$(window).scrollTop()`."""
    js = _live(_read(BOOTSNAV_JS))

    assert not re.search(r"\$\(window\)\.on\(\s*['\"]scroll['\"]", js), (
        "the per-handler scroll bindings must be replaced by the shared "
        "rAF-coalesced dispatcher (onWindowScroll)"
    )
    assert re.search(
        r"addEventListener\(\s*['\"]scroll['\"]\s*,\s*scheduleScrollFrame\s*,\s*"
        r"\{\s*passive\s*:\s*true",
        js,
    ), "the single scroll listener must be registered `{ passive: true }`"
    assert "requestAnimationFrame" in js, "the dispatcher must be rAF-coalesced"
    assert re.search(r"function\s+onWindowScroll\s*\(", js) and re.search(
        r"function\s+runScrollSubscribers\s*\(", js
    ), "the shared dispatcher (onWindowScroll / runScrollSubscribers) must exist"

    # A live `$(window).scrollTop()` may only survive in the click handler (one
    # read per click); it must be gone from every scroll path.
    occurrences = js.count("$(window).scrollTop()")
    assert occurrences <= 1, (
        "a scroll handler must not do its own live $(window).scrollTop() read - "
        "the dispatcher reads the position once per frame (%d occurrences left)"
        % occurrences
    )
    assert "pageYOffset" in js, "the dispatcher must read `window.pageYOffset` once"


# --------------------------------------------------------------------------- #
# the progress-bar reveal must not bind a scroll handler per element
# --------------------------------------------------------------------------- #
def test_progress_bars_are_revealed_without_a_per_event_scroll_handler():
    """`.appear()` binds a `scroll` handler per element running the `:visible`
    filter (`offsetWidth`/`offsetHeight`) + `offset()` + `height()` on every
    event - the single biggest per-event forced-layout source on this page."""
    js = _live(_read(CUSTOM_JS))

    assert "IntersectionObserver" in js, (
        "the progress-bar reveal must use an IntersectionObserver (no scroll "
        "handler, no layout read) instead of `.appear()`"
    )
    assert re.search(r"else\s*\{[^}]*progressBar\.appear\(", js), (
        "`.appear()` may only remain as the documented no-IntersectionObserver "
        "fallback"
    )
