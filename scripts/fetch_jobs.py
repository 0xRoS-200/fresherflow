#!/usr/bin/env python3
"""Refresh India job cache (same pipeline as the web server)."""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

from job_cache import refresh_cache  # noqa: E402


def main():
	payload = refresh_cache(force=True)
	print(
		'Wrote %d jobs (%d new) to data/jobs_live_cache.json at %s'
		% (len(payload.get('jobs', [])), payload.get('newCount', 0), payload.get('fetchedAt'))
	)
	if payload.get('errors'):
		print('Warnings:', '; '.join(payload['errors']))


if __name__ == '__main__':
	main()
