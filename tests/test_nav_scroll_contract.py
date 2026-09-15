"""Contract tests for in-page anchor navigation (header -> section scrolling).

Runtime verification caught the real, user-visible bug: clicking a header link
scrolled the section heading to `top: 0` - i.e. BEHIND the ~190px fixed navbar -
and several anchors (the header "book a demo" CTA, the hero CTAs, the showcase
tiles, the footer links) were not wired at all because the old handler only
bound `li.smooth-menu a`.

There were two independent defects, and both are pinned here:

* LAYOUT - ``html, body { height: 100% }`` (plus ``body { overflow-x: hidden }``,
  which makes ``overflow-y`` compute to ``auto``) made **body** the scroll
  container: ``documentElement.scrollHeight`` was pinned to the viewport height,
  so the document itself could not scroll. Native ``#anchor`` jumps were no-ops
  and ``window`` scroll events never fired (dead sticky nav / back-to-top /
  parallax). body must grow with its content (``height: auto``).
* OFFSET/COVERAGE - the handler must subtract the live navbar height and must
  cover every in-page anchor, not just ``li.smooth-menu a``; the CSS
  ``scroll-margin-top: var(--nav-h)`` fallback covers the browser's own hash
  navigation (deep link, JS disabled) with the same token.

Pure text assertions (no browser, no server), in the same style as the existing
hero-animation and API contracts. CSS/JS comments are stripped before scanning so
a comment that *documents* the old behaviour stays legal - only live code counts.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INDEX_HTML = ROOT / "index.html"
STYLE_CSS = ROOT / "assets" / "css" / "style.css"
CUSTOM_JS = ROOT / "assets" / "js" / "custom.js"

#: The fixed navbar's own height, in px, as measured at runtime (desktop).
NAVBAR_HEIGHT_PX = 190

#: The gap custom.js adds below the navbar (``NAV_GAP``).
NAV_GAP_PX = 16


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _strip_comments(text: str) -> str:
    """Drop ``/* ... */``, ``//`` and ``<!-- ... -->`` comments."""
    text = re.sub(r"/\*[\s\S]*?\*/", " ", text)
    text = re.sub(r"<!--[\s\S]*?-->", " ", text)
    return re.sub(r"(?m)^\s*//.*$", " ", text)


def _live(html_or_css_or_js: str) -> str:
    return _strip_comments(html_or_css_or_js)


def _rule_body(css: str, selector: str) -> str:
    """Every declaration block of the rules whose selector list contains *selector*.

    A selector may be declared by several rules (``body`` has both the legacy
    typography rule and the scroll-container rule), so all of them are joined.
    """
    css = _live(css)
    bodies = []
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        parts = [p.strip() for p in selectors.split(",")]
        if selector in parts:
            bodies.append(body)
    if not bodies:
        raise AssertionError("no rule declaring selector %r in style.css" % selector)
    return "\n".join(bodies)


def _anchor_hrefs(html: str):
    """Every in-page fragment target referenced by the page."""
    out = []
    for chunk in html.split("href=" + chr(34))[1:]:
        fragment = chunk.split(chr(34))[0]
        if fragment.startswith("#"):
            out.append((fragment, fragment[1:]))
    return out


# --------------------------------------------------------------------------- #
# no dead anchors
# --------------------------------------------------------------------------- #
def test_every_in_page_anchor_points_at_a_real_element():
    """A hash that names nothing scrolls nowhere - the classic dead nav link.

    Pins the header nav (how it works / capabilities / use cases / showcase /
    integrations / contact) plus the header CTA, hero CTAs and footer links
    against the ids that actually exist in the markup.
    """
    html = _live(_read(INDEX_HTML))
    ids = set(re.findall(r'id="([^"]+)"', html))
    dead = sorted({frag for frag, name in _anchor_hrefs(html) if name and name not in ids})

    assert not dead, "in-page anchors that match no element id: %s" % dead

    for required in ("how-it-works", "capabilities", "use-cases", "showcase", "integrations", "contact"):
        assert required in ids, "header nav target #%s must exist in index.html" % required


def test_no_duplicate_ids_for_anchor_targets():
    """Duplicate ids make the browser pick an arbitrary target for the hash."""
    html = _live(_read(INDEX_HTML))
    ids = re.findall(r'id="([^"]+)"', html)
    dupes = sorted({i for i in ids if ids.count(i) > 1})

    assert not dupes, "duplicate element ids would break hash navigation: %s" % dupes


# --------------------------------------------------------------------------- #
# the scroll container is the document again
# --------------------------------------------------------------------------- #
def test_body_is_not_pinned_to_the_viewport_height():
    """``html, body { height: 100% }`` is the layout half of the bug.

    Pinning body's height while it also clips horizontally
    (``overflow-x: hidden`` -> ``overflow-y: auto``) turns body into the scroll
    container, so the page itself cannot scroll and window scroll events die.
    """
    css = _live(_read(STYLE_CSS))

    assert not re.search(r"html\s*,\s*body\s*\{[^}]*height\s*:\s*100%", css), (
        "`html, body { height: 100% }` must not come back: it makes body the "
        "scroll container, which kills native hash navigation"
    )
    body = _rule_body(_read(STYLE_CSS), "body")

    assert re.search(r"height\s*:\s*auto", body), "body must grow with its content (height: auto)"
    assert re.search(r"min-height\s*:\s*100%", body), "body must stay at least viewport-tall"


# --------------------------------------------------------------------------- #
# the fixed-navbar offset (CSS fallback + JS)
# --------------------------------------------------------------------------- #
def test_css_reserves_the_fixed_navbar_height_for_anchor_targets():
    """Native hash navigation needs a margin: the navbar overlays the content."""
    css = _live(_read(STYLE_CSS))

    assert re.search(r"--nav-h\s*:\s*\d+px", css), "--nav-h token must be declared in style.css"
    assert re.search(r"scroll-margin-top\s*:\s*var\(--nav-h\)", css), (
        "anchor targets must declare `scroll-margin-top: var(--nav-h)` so the "
        "browser's own hash jump clears the fixed navbar"
    )

    declared = int(re.search(r"--nav-h\s*:\s*(\d+)px", css).group(1))
    assert declared >= NAVBAR_HEIGHT_PX, (
        "--nav-h (%dpx) must cover the fixed navbar (%dpx) or headings sit behind it"
        % (declared, NAVBAR_HEIGHT_PX)
    )


def test_js_offset_is_read_live_from_the_navbar():
    """The scroll offset must be derived from the navbar, never hard-coded."""
    js = _live(_read(CUSTOM_JS))

    assert "outerHeight()" in js, "the nav offset must come from the navbar's live height"
    assert re.search(r"offset\(\)\.top\s*-\s*navOffset\(\)", js), (
        "the handler must subtract navOffset() (navbar height + gap) from the "
        "target's offset - scrolling to a bare offset().top hides the heading "
        "behind the fixed header"
    )
    assert not re.search(r"offset\(\)\.top\s*-\s*0", js), "the old zero-offset must not return"
    assert re.search(r"Math\.max\(\s*0\s*,", js), "the computed scroll top must be clamped at 0"


def test_every_in_page_anchor_is_handled_and_the_mobile_menu_closes():
    """One delegated handler covers the whole page, incl. the mobile collapse."""
    js = _live(_read(CUSTOM_JS))

    assert ("$(document).on(" in js and "click" in js and "href^=" + chr(34) + "#" + chr(34) in js), (
        "a single delegated handler for `a[href^=\"#\"]` must cover the header "
        "nav, the header CTA, the hero CTAs and the footer links alike"
    )
    assert "li.smooth-menu a" not in js, (
        "the narrow `li.smooth-menu a` binding must not come back - it left every "
        "other in-page anchor unhandled"
    )
    assert ("collapse(" in js and "hide" in js), (
        "the mobile menu must close after navigating, or the target stays hidden"
    )
    assert "pushState" in js, (
        "the hash must be updated with pushState so the browser does not jump "
        "again and undo the header offset"
    )
