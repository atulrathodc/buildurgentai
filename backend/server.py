#!/usr/bin/env python3
"""BuildUrgent AI product site server: static site + read-only JSON API.

The BuildUrgent AI site (https://ai.buildurgent.com) is a purely static site
(``index.html`` + ``assets/``) plus this small REST API that exposes the
product's own data (company/product info, showcase tiles, features, health).
Everything is implemented with the Python standard library - no dependencies,
no build step, and nothing is injected into the published page.

Usage:
    python3 server.py                 # http://0.0.0.0:8080
    python3 server.py --port 8149     # custom port
    PORT=8149 HOST=127.0.0.1 python3 server.py

API:
    GET /api/health     -> {"status": "ok", ...}
    GET /api/profile    -> company/product info (company/product/tagline/role/site)
    GET /api/projects   -> product showcase tiles discovered under assets/images
    GET /api/features   -> platform capabilities (agent orchestration, RAG, ...)

Documents:
    GET /privacy-policy    -> 302 to assets/download/PrivacyPolicy.pdf
    GET /terms-conditions  -> 302 to assets/download/TermsConditions.pdf
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import re
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
# backend/server.py -> repo root; a root-level copy of this module is the root itself.
ROOT = os.path.dirname(_HERE) if os.path.basename(_HERE) == "backend" else _HERE

API_PREFIX = "/api/"
#: Bumped whenever the JSON API contract changes (routes added/removed, payload keys
#: renamed). Exposed by GET /api/health so consumers can pin against a known contract.
#: 2.0 - the payload now carries the BuildUrgent AI product/company info (the personal
#: owner profile and its download entry are gone) and GET /api/features was added.
API_VERSION = "2.0"
#: The showcase tile images (p1..p18.svg) shipped with the product site.
SHOWCASE_DIR = os.path.join(ROOT, "assets", "images", "portfolio")
STARTED_AT = time.time()

SITE = {
    "company": "BuildUrgent",
    "product": "BuildUrgent AI",
    "tagline": "Ship AI agents that do real work.",
    "role": "Agentic AI platform for production workflows",
    "site": "https://ai.buildurgent.com",
    "docs": "https://ai.buildurgent.com/#about",
    "demo": "https://ai.buildurgent.com/#contact",
    "contact": "hello@buildurgent.com",
    "sales": "sales@buildurgent.com",
}

#: The platform capabilities exposed by GET /api/features (stable, documented shape).
FEATURES = [
    {
        "id": "agent-orchestration",
        "name": "Agent orchestration",
        "summary": "Compose, schedule and replay multi-agent workflows with deterministic "
                   "hand-offs, retries and human approval steps.",
    },
    {
        "id": "tool-api-integrations",
        "name": "Tool & API integrations",
        "summary": "Expose any REST, GraphQL or internal service as a typed, permissioned "
                   "tool your agents can call safely.",
    },
    {
        "id": "retrieval-pipelines",
        "name": "Retrieval (RAG) pipelines",
        "summary": "Ingest, chunk and embed your own documents, then ground every answer in "
                   "cited sources instead of model memory.",
    },
    {
        "id": "evaluations-guardrails",
        "name": "Evaluations & guardrails",
        "summary": "Score every change against golden datasets and block unsafe, off-policy "
                   "or drifting output before it reaches production.",
    },
    {
        "id": "run-observability",
        "name": "Run observability",
        "summary": "Trace each step, token and tool call with replayable run logs, latency "
                   "breakdowns and live cost dashboards.",
    },
    {
        "id": "enterprise-security",
        "name": "Enterprise security (SSO/RBAC)",
        "summary": "SAML/OIDC single sign-on, role-based access control, audit trails and "
                   "configurable data residency out of the box.",
    },
]

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _natural_key(name: str):
    """Sort p2.svg before p10.svg."""
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", name)]


def page_title() -> str:
    """Read the <title> straight from index.html so the API never drifts from the page."""
    try:
        with open(os.path.join(ROOT, "index.html"), encoding="utf-8", errors="replace") as fh:
            match = _TITLE_RE.search(fh.read())
        if match:
            return " ".join(match.group(1).split())
    except OSError:
        pass
    return ""


def projects():
    """Product showcase tiles = the images actually shipped in assets/images/portfolio.

    The page references exactly one file per tile, so the directory must yield one
    entry per base name. Historically the old portfolio rasters (p1.jpg … p6.jpg)
    sat alongside the live vectors, which made ``id`` (the stem) collide and
    ``project_count`` disagree with the page. Resolving per base name - preferring
    the ``.svg`` the page ships - keeps the API honest if a stray file reappears.
    """
    try:
        names = [n for n in os.listdir(SHOWCASE_DIR) if not n.startswith(".")]
    except OSError:
        return []

    by_stem: dict[str, str] = {}
    for name in names:
        stem, ext = os.path.splitext(name)
        # An .svg tile wins over any legacy raster with the same stem.
        if stem not in by_stem or ext.lower() == ".svg":
            by_stem[stem] = name

    return [
        {
            "id": stem,
            "image": "assets/images/portfolio/" + by_stem[stem],
            "url": "#portfolio",
        }
        for stem in sorted(by_stem, key=_natural_key)
    ]


def features():
    """The platform capabilities the BuildUrgent AI product ships with."""
    return [dict(item) for item in FEATURES]


def profile():
    data = dict(SITE)
    data["title"] = page_title()
    items = projects()
    data["project_count"] = len(items)
    data["features_count"] = len(features())
    return data


def health():
    return {
        "status": "ok",
        "service": "buildurgent-ai-api",
        "api_version": API_VERSION,
        "uptime_seconds": round(time.time() - STARTED_AT, 3),
        "routes": sorted(BuildUrgentHandler.ROUTES),
    }


class BuildUrgentHandler(http.server.SimpleHTTPRequestHandler):
    """Serves the repository root with sane MIME types, no caching, and the JSON API."""

    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".mjs": "application/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
        ".webmanifest": "application/manifest+json; charset=utf-8",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".ttf": "font/ttf",
        ".eot": "application/vnd.ms-fontobject",
    }

    server_version = "BuildUrgentAIHTTP/2.0"
    # HTTP/1.1 keep-alive: safe because every response path (static file, JSON API,
    # redirect) sets Content-Length, and it keeps strict HTTP/1.1-only clients happy.
    protocol_version = "HTTP/1.1"

    ROUTES = {
        "/api/health": staticmethod(health),
        "/api/profile": staticmethod(profile),
        "/api/projects": staticmethod(projects),
        "/api/features": staticmethod(features),
    }

    # Legacy / bookmarkable document URLs that must not 404 on the live server.
    REDIRECTS = {
        "/privacy-policy": "assets/download/PrivacyPolicy.pdf",
        "/terms-conditions": "assets/download/TermsConditions.pdf",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    # ---------- API ----------
    def _api_payload(self):
        """(status, payload) for the request path, or None when it is not an API route."""
        path = self.path.split("?", 1)[0].split("#", 1)[0].rstrip("/") or "/"
        if path == "/api":
            return 200, {"service": "buildurgent-ai-api", "routes": sorted(self.ROUTES)}
        if not (path + "/").startswith(API_PREFIX):
            return None
        handler = self.ROUTES.get(path)
        if handler is None:
            return 404, {"error": "not_found", "path": path, "routes": sorted(self.ROUTES)}
        return 200, handler()

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _maybe_api(self) -> bool:
        resolved = self._api_payload()
        if resolved is None:
            return False
        self._send_json(*resolved)
        return True

    def _maybe_redirect(self) -> bool:
        """Serve REDIRECTS (e.g. /privacy-policy) as a 302 onto the real document."""
        path = self.path.split("?", 1)[0].split("#", 1)[0].rstrip("/") or "/"
        target = self.REDIRECTS.get(path)
        if target is None:
            return False
        self.send_response(302)
        self.send_header("Location", "/" + target)
        self.send_header("Content-Length", "0")
        self.end_headers()
        return True

    def do_GET(self):  # noqa: N802 (stdlib naming)
        if self._maybe_redirect() or self._maybe_api():
            return
        super().do_GET()

    def do_HEAD(self):  # noqa: N802 (stdlib naming)
        if self._maybe_redirect() or self._maybe_api():
            return
        super().do_HEAD()

    # ---------- headers / logging ----------
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))
        sys.stderr.flush()


def build_server(host: str, port: int):
    """Returns a configured ThreadingHTTPServer for the BuildUrgent AI site root."""
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    return http.server.ThreadingHTTPServer((host, port), BuildUrgentHandler)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Serve the BuildUrgent AI static site and API.")
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    args = parser.parse_args(argv)

    with build_server(args.host, args.port) as httpd:
        print("buildurgent ai server on http://%s:%d  (root: %s)" % (args.host, args.port, ROOT), flush=True)
        print("api: http://%s:%d/api/health" % (args.host, args.port), flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nshutting down", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
