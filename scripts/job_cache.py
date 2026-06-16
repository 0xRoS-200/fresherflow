"""Persist job feed and detect newly posted listings (2-hour refresh cycle)."""
import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

from job_fetch import fetch_live_jobs

ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT / 'data' / 'jobs_live_cache.json'
REFRESH_INTERVAL = timedelta(hours=2)

_lock = threading.Lock()


def _utc_now():
	return datetime.now(timezone.utc)


def _iso(dt):
	return dt.replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def _parse_iso(value):
	if not value:
		return None
	try:
		return datetime.fromisoformat(value.replace('Z', '+00:00'))
	except Exception:
		return None


def load_cache():
	if not CACHE_PATH.exists():
		return None
	try:
		return json.loads(CACHE_PATH.read_text(encoding='utf-8'))
	except Exception:
		return None


def save_cache(payload):
	CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
	CACHE_PATH.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def _first_seen_map(cache):
	mapping = {}
	for job in cache.get('jobs') or []:
		jid = job.get('id') or job.get('applyUrl')
		if jid and job.get('firstSeenAt'):
			mapping[jid] = job['firstSeenAt']
	return mapping


def refresh_cache(force=False):
	"""Fetch live jobs, merge cache, mark jobs not seen before as new."""
	with _lock:
		prev = load_cache() or {}
		prev_ids = set(prev.get('knownJobIds') or [])
		prev_seen = _first_seen_map(prev)

		live = fetch_live_jobs()
		now = _utc_now()
		now_iso = _iso(now)

		new_ids = []
		jobs = []
		for job in live.get('jobs') or []:
			jid = job.get('id') or job.get('applyUrl')
			if not jid:
				continue
			entry = dict(job)
			if jid not in prev_ids:
				entry['isNew'] = True
				entry['firstSeenAt'] = now_iso
				new_ids.append(jid)
			else:
				entry['isNew'] = False
				entry['firstSeenAt'] = prev_seen.get(jid) or prev.get('fetchedAt') or now_iso
			jobs.append(entry)

		known_ids = prev_ids | {j.get('id') or j.get('applyUrl') for j in jobs if j.get('id') or j.get('applyUrl')}

		payload = {
			'fetchedAt': now_iso,
			'nextRefreshAt': _iso(now + REFRESH_INTERVAL),
			'refreshIntervalHours': REFRESH_INTERVAL.total_seconds() / 3600,
			'newCount': len(new_ids),
			'newJobIds': new_ids,
			'knownJobIds': sorted(known_ids),
			'jobs': jobs,
			'sources': live.get('sources') or [],
			'errors': live.get('errors') or [],
		}
		save_cache(payload)
		return payload


def get_jobs_payload():
	"""Return cached jobs immediately (caller refreshes in background if stale)."""
	cache = load_cache()
	if cache:
		return cache
	return refresh_cache(force=True)


def is_cache_stale():
	cache = load_cache()
	if not cache:
		return True
	fetched = _parse_iso(cache.get('fetchedAt'))
	if not fetched:
		return True
	return (_utc_now() - fetched) >= REFRESH_INTERVAL


def start_background_refresh():
	"""Initial fetch + repeat every 2 hours while the server runs."""

	def loop():
		while True:
			try:
				refresh_cache(force=True)
				print('[jobs] Refreshed live cache (%s)' % CACHE_PATH.name, flush=True)
			except Exception as exc:
				print('[jobs] Refresh failed: %s' % exc, flush=True)
			# Sleep until next interval
			import time
			time.sleep(int(REFRESH_INTERVAL.total_seconds()))

	# Run first refresh in a thread so the server starts immediately
	def bootstrap():
		try:
			if load_cache() is None or is_cache_stale():
				refresh_cache(force=True)
				print('[jobs] Initial cache ready', flush=True)
		except Exception as exc:
			print('[jobs] Initial refresh failed: %s' % exc, flush=True)
		loop()

	thread = threading.Thread(target=bootstrap, name='job-refresh', daemon=True)
	thread.start()
	return thread
