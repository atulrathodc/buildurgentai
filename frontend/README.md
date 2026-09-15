# frontend/

Frontend source for **BuildUrgent AI** (ai.buildurgent.com).

## Layout

| Path | Purpose |
|------|---------|
| `index.html` | Frontend source entry point. Delegates to the production document at `/`. |
| `../index.html` | The maintained production markup (served at `GET /`). |
| `../assets/css/` | Design system, Bootstrap/Bootsnav base, responsive rules. |
| `../assets/js/` | Vanilla JS: background stage, nav, scroll helpers. |
| `../assets/images/` | Showcase tiles (`portfolio/p*.svg`) and logos. |

## Serving

The stdlib server (`backend/server.py`, entry `server.py`) serves the
repository root, so `GET /` returns the production `index.html` and the
`assets/` bundle is reachable at `/assets/...`. `frontend/index.html`
redirects to `/` so the frontend source URL never diverges from production.

```bash
python3 server.py            # http://0.0.0.0:8080
python3 server.py --port 8139
```

There is no build step: the frontend is plain HTML/CSS/JS with **no external
dependencies** (no CDNs, no web-font fetches), so it renders in offline /
restricted networks.
