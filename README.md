# BuildUrgent AI — Product Website

Marketing and product landing site for **BuildUrgent AI**, the agentic AI platform
that ships agents capable of doing real work. Served at
**[ai.buildurgent.com](https://ai.buildurgent.com)**.

The site is a static HTML/CSS/JS frontend backed by a small dependency-free Python
HTTP server that exposes JSON API endpoints and serves the static assets.

## Layout

```
.
├── index.html              # Product landing page (hero, features, pricing, API demo)
├── CNAME                   # Custom domain for GitHub Pages: ai.buildurgent.com
├── assets/
│   ├── css/                # Static styles
│   ├── js/                 # Frontend scripts (3-D WebGL background, interactions)
│   └── images/portfolio/   # SVG tiles used by the API demo dashboard
├── backend/
│   └── server.py           # Static file server + JSON APIs
└── tests/
    └── test_api_contract.py, test_hero_animation_contract.py
```

## Running locally

No third-party dependencies are required — only Python 3.

```bash
python3 backend/server.py            # serves on http://127.0.0.1:8111
python3 backend/server.py --port 8080
```

Then open <http://127.0.0.1:8111/>.

## API endpoints

| Method | Path            | Description                                        |
| ------ | --------------- | -------------------------------------------------- |
| GET    | `/api/profile`  | Company + product profile JSON                     |
| GET    | `/api/projects` | Product capability/project tiles (SVG images)      |
| GET    | `/api/features` | Platform feature list                              |
| GET    | `/api/health`   | Health check + page title                          |

All endpoints return `application/json`. The frontend consumes them for the live
demo section of the page.

## Tests

```bash
python3 -m pytest tests -q
```

Covers the API JSON contract and the static hero headline contract (no JS-only
hero animation, semantic markup, product value proposition copy).

## Deployment

The `CNAME` file targets GitHub Pages at `ai.buildurgent.com`. Push to the
publishing branch and point the domain's DNS `CNAME` record at the Pages host.

## Third-party scripts

Google AdSense and Google Analytics/GTM tags are included for site analytics and
monetisation. Ad requests are third-party network calls and may be blocked or
return errors in ad-blocked or offline environments; this does not affect the
page itself, which renders fully without JavaScript.
