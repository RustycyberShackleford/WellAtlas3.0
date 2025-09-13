
# WellAtlas 3.0 — Cascade

- Header: WellAtlas 3.0
- Top bar: Customers, Job #, Customer ▾ / Site ▾ / Job # ▾, Search, Center on Me, **Add Site**
- Add Site: click map to prefill coords → select customer → create
- Job notes sortable by date (Newest/Oldest)
- Jobs index page
- Seed: ~400 jobs (40×10)
- Leaflet + MapTiler (env `MAPTILER_KEY`)
- Health: `/healthz`; Start: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120`
