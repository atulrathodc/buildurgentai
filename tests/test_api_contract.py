"""Contract tests for the read-only JSON API in ``backend/server.py``.

These pin the behaviour that runtime verification caught drifting: the showcase
tiles must be *the* images the page ships - one entry per tile, unique ids, no
dead files - and the product/company identity must stay the BuildUrgent AI one.

The tests import the handler's route functions directly (no socket, no server),
so they are hermetic and run anywhere next to the hero-animation contract.
"""

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "index.html"
SERVER_PY = ROOT / "backend" / "server.py"

#: The one mailbox the product is contactable at (owner's real mail id). The page prints
#: it and GET /api/profile exposes it, so it legitimately contains the personal tokens the
#: resume leak-guard below bans. The guard therefore scans the markup with this address
#: removed instead of being weakened - any *other* occurrence still fails the test.
CONTACT_EMAIL = "atulrathodc@gmail.com"
#: Placeholder addresses that must never come back.
STALE_CONTACTS = ("hello@buildurgent.com", "sales@buildurgent.com")


def _load_server():
    """Import backend/server.py by path (it is not an installed package)."""
    spec = importlib.util.spec_from_file_location("buildurgent_server", SERVER_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


server = _load_server()

#: Asset paths the page actually references (``<img src>`` etc.).
#: The attribute-quote pair is built with ``chr()`` so the pattern needs no string
#: escapes - it is exactly ``["\'](assets/[^"\']+)["\']``.
_ATTR_QUOTES = chr(34) + chr(39)
_REFERENCED = set(
    re.findall(
        "[" + _ATTR_QUOTES + "](assets/[^" + _ATTR_QUOTES + "]+)[" + _ATTR_QUOTES + "]",
        INDEX_HTML.read_text(encoding="utf-8"),
    )
)


def _referenced_tiles():
    return {p for p in _REFERENCED if p.startswith("assets/images/portfolio/")}


# --------------------------------------------------------------------------- #
# showcase tiles
# --------------------------------------------------------------------------- #
def test_showcase_tiles_have_unique_ids():
    """`id` identifies a tile, so it must never repeat.

    Regression guard: the directory used to hold both ``p1.jpg`` (old portfolio
    raster) and ``p1.svg`` (the shipped vector), and ``id`` - the file stem -
    collided, silently emitting two tiles for one id.
    """
    ids = [tile["id"] for tile in server.projects()]

    assert ids, "GET /api/projects must return the showcase tiles"
    assert len(ids) == len(set(ids)), "duplicate showcase tile ids: %s" % (
        sorted(i for i in ids if ids.count(i) > 1)
    )


def test_showcase_tiles_are_the_images_the_page_ships():
    """Every tile must be a file the page references, and vice versa."""
    returned = {tile["image"] for tile in server.projects()}

    assert returned == _referenced_tiles(), (
        "the API must list exactly the tile images index.html references "
        "(unreferenced: %s; missing: %s)"
        % (sorted(returned - _referenced_tiles()), sorted(_referenced_tiles() - returned))
    )


def test_showcase_tile_files_exist_on_disk():
    """A tile that 404s is worse than no tile - every path must resolve."""
    missing = [t["image"] for t in server.projects() if not (ROOT / t["image"]).is_file()]

    assert not missing, "showcase tiles point at missing files: %s" % missing


def test_no_stale_raster_tiles_remain():
    """The old portfolio rasters must not creep back into the shipped directory."""
    leftovers = sorted(
        p.name for p in (ROOT / "assets" / "images" / "portfolio").glob("*.jpg")
    )

    assert not leftovers, (
        "legacy raster tiles must not ship (they collide with the .svg ids): %s"
        % leftovers
    )


def test_project_count_matches_the_listed_tiles():
    """`project_count` must describe the payload, not the raw directory."""
    assert server.profile()["project_count"] == len(server.projects())


# --------------------------------------------------------------------------- #
# product / company identity
# --------------------------------------------------------------------------- #
def test_profile_identifies_the_buildurgent_ai_product():
    """The API must describe the company's product, not the old personal site."""
    data = server.profile()

    assert data["company"] == "BuildUrgent"
    assert data["product"] == "BuildUrgent AI"
    assert data["site"] == "https://ai.buildurgent.com"
    # 18 showcase SVGs (p1..p18) are referenced by the page, one element each.
    assert data["project_count"] == 18
    assert "agent" in (data["tagline"] + data["role"]).lower()


def test_profile_reports_the_six_platform_capabilities():
    """`features_count` must track GET /api/features."""
    assert server.profile()["features_count"] == len(server.features()) == 6


def test_health_describes_the_service():
    """The health payload is the versioned entry point clients pin against."""
    payload = server.health()

    assert payload["status"] == "ok"
    assert payload["service"] == "buildurgent-ai-api"
    assert payload["api_version"] == server.API_VERSION == "2.0"


def test_no_personal_resume_is_shipped():
    """The previous owner's résumé must not be downloadable from the product site."""
    assert not (ROOT / "assets" / "download" / "AtulRathod_Fullstack_Resume.pdf").exists()


def test_no_personal_content_in_live_markup():
    """The shipped page must read as the product site, not a personal portfolio.

    The sanctioned contact address (``CONTACT_EMAIL``) contains the owner's name, so it is
    scrubbed out of the markup *before* the banned-token scan: the guard still catches a
    résumé/hire-me leak anywhere else on the page, while the one legitimate occurrence -
    the contact mailbox - is allowed (and separately asserted below).
    """
    live = INDEX_HTML.read_text(encoding="utf-8").lower()

    assert CONTACT_EMAIL in live, "the page must print the real contact address"
    scrubbed = live.replace(CONTACT_EMAIL, "<contact-email>")

    for token in ("atul", "rathod", "my resume", "hire me", "download resume"):
        assert token not in scrubbed, "personal token %r leaked into index.html" % token
    assert "buildurgent ai" in live


def test_live_page_uses_the_real_contact_email():
    """Markup and API must advertise one address: ``atulrathodc@gmail.com``."""
    live = INDEX_HTML.read_text(encoding="utf-8")

    for stale in STALE_CONTACTS:
        assert stale not in live.lower(), (
            "placeholder contact address %r is still shipped in index.html" % stale
        )
    assert 'fs=1&to=%s"' % CONTACT_EMAIL in live, (
        "the 'book a demo' GMail compose link must target %s" % CONTACT_EMAIL
    )

    data = server.profile()
    assert data["contact"] == CONTACT_EMAIL
    assert data["sales"] == CONTACT_EMAIL
