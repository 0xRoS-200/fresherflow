# FresherFlow

India fresher job search with resume matching.

## What it does

- Loads fresher jobs from the bundled local feed immediately
- Matches jobs against pasted or uploaded resume text
- Supports PDF, DOCX, TXT, and MD resume parsing
- Refreshes the live job cache automatically while the server is running
- Sorts results by newest posted jobs or best match

## Run locally

```bash
bash run.sh
```

Open http://localhost:8080 and keep that terminal running. Do not open `index.html` directly from disk, because the app expects to be served over HTTP.

## Manual refresh

If you want to rebuild the live job cache yourself:

```bash
python3 scripts/refresh_jobs_cache.py
```

## Project structure

- `app.js` - frontend logic for matching, filtering, and ranking jobs
- `index.html` - app shell
- `styles.css` - UI styling
- `data/` - job feeds and cache files used by the app
- `scripts/` - cache refresh, parsing, and server helpers
- `vendor/` - local PDF parsing assets

## Notes

- Keep `data/jobs_live_cache.json`, `data/jobs.json`, and `data/india_seed_jobs.json` in the repo, because the app reads them at runtime
- Generated Python caches such as `scripts/__pycache__/` are ignored through [`.gitignore`](.gitignore)
- Default sort order is newest posted first; you can switch to best match or company name in the UI
