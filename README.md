
# WellAtlas 3.0 — Cascade Filters

- Header: **WellAtlas 3.0**
- Top bar: **Customers**, **Job #**, **Customer ▾ / Site ▾ / Job # ▾**, **Search**, **Center on Me**
- No standalone Sites page (sites shown inside customer pages + dropdown)
- BigSeed+Details seed (~400 jobs across 40×10)
- Leaflet + MapTiler (set `MAPTILER_KEY`); background `static/wallpaper.jpg`
- Health check: `/healthz`

Deploy: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120`
