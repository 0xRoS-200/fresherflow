"""Fetch India tech jobs from public APIs (used by serve.py /api/jobs)."""
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]



INDIA_LOC_RE = re.compile(
	r'india|indian|bengaluru|bangalore|hyderabad|pune|chennai|mumbai|delhi|gurugram|gurgaon|noida|kolkata|ahmedabad|karnataka|maharashtra|telangana|tamil nadu',
	re.I,
)

TECH_TITLE_RE = re.compile(
	r'engineer|developer|sde|swe|programmer|frontend|backend|full[\s-]?stack|android|ios|devops|intern\b|graduate',
	re.I,
)

NON_TECH_TITLE_RE = re.compile(
	r'product management|account executive|business development|sales|marketing|recruiting|human resources|\bhr\b|finance|legal|collections|customer success|scrum master|consultant|analyst|operations',
	re.I,
)



SENIOR_TITLE_RE = re.compile(
	r'senior|principal|staff\b|lead\b|manager|director|head of|architect|\b(iii|iv|v)\b|'
	r'engineer\s*[3-9]|engineer\s*iii|sde\s*iii|technical lead|engineering manager',
	re.I,
)

STRIP_HTML_RE = re.compile(r'<[^>]+>')


def strip_html(text):
	raw = unescape(text or '')
	return re.sub(r'\s+', ' ', STRIP_HTML_RE.sub(' ', raw)).strip()


def is_india_location(location):
	return bool(INDIA_LOC_RE.search(location or ''))


def is_tech_title(title):
	t = title or ''
	if not TECH_TITLE_RE.search(t):
		return False
	if NON_TECH_TITLE_RE.search(t):
		return False
	return True


def estimate_posted_days(created_at):
	if not created_at:
		return 0
	try:
		from datetime import datetime, timezone
		created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
		if created.tzinfo is None:
			created = created.replace(tzinfo=timezone.utc)
		delta = datetime.now(timezone.utc) - created
		return max(0, delta.days)
	except Exception:
		return 0





def from_themuse(item):
	locations = item.get('locations') or []
	location_text = ', '.join(l.get('name') or '' for l in locations if l.get('name')) or 'Remote'
	mode = 'Remote' if any(re.search(r'remote|flexible', (l.get('name') or ''), re.I) for l in locations) else 'Onsite'
	categories = item.get('categories') or []
	levels = item.get('levels') or []
	tags = [(c.get('name') or '').lower() for c in categories if c.get('name')]
	tags += [(l.get('name') or '').lower() for l in levels if l.get('name')]
	
	level_names = [l.get('name', '').lower() for l in levels if l.get('name')]
	is_entry = any('entry' in ln or 'intern' in ln or 'junior' in ln for ln in level_names)
	is_senior = any('senior' in ln or 'lead' in ln or 'principal' in ln or 'manager' in ln for ln in level_names)
	exp_max = 1 if is_entry else (5 if is_senior else 3)

	return {
		'id': (item.get('refs') or {}).get('landing_page') or item.get('id') or item.get('name'),
		'title': item.get('name') or 'Unknown role',
		'company': (item.get('company') or {}).get('name') or 'Unknown',
		'location': location_text,
		'mode': mode,
		'jobType': (item.get('type') or item.get('job_type') or 'Full-time').replace('_', ' '),
		'postedDaysAgo': estimate_posted_days(item.get('publication_date')),
		'source': 'themuse',
		'salary': 'Salary not listed',
		'applyUrl': (item.get('refs') or {}).get('landing_page'),
		'experienceMax': exp_max,
		'tags': tags,
		'description': strip_html(item.get('contents') or item.get('description') or '')[:6000],
	}


def fetch_themuse_location(location, pages=5, timeout=10):
	jobs = []
	for page in range(1, pages + 1):
		try:
			q = location.replace(' ', '%20')
			url = f'https://www.themuse.com/api/public/jobs?page={page}&location={q}'
			req = Request(url, headers={'User-Agent': 'FresherFlow/1.0'})
			with urlopen(req, timeout=timeout) as resp:
				data = json.loads(resp.read().decode('utf-8'))
			results = data.get('results') or []
			if not results:
				break
			for item in results:
				job = from_themuse(item)
				if job.get('applyUrl') and (is_india_location(job.get('location')) or job.get('mode') == 'Remote') and is_tech_title(job.get('title')):
					jobs.append(job)
		except Exception:
			break
	return jobs


def fetch_themuse_india():
	locations = ['Bengaluru', 'Hyderabad', 'Pune', 'Chennai', 'Mumbai', 'Delhi', 'India', 'Remote']
	jobs = []
	with ThreadPoolExecutor(max_workers=8) as pool:
		futures = {pool.submit(fetch_themuse_location, loc): loc for loc in locations}
		for fut in as_completed(futures):
			try:
				jobs.extend(fut.result())
			except Exception:
				pass
	return jobs


def fetch_arbeitnow_jobs(timeout=10):
	try:
		url = 'https://www.arbeitnow.com/api/job-board-api'
		req = Request(url, headers={'User-Agent': 'FresherFlow/1.0'})
		with urlopen(req, timeout=timeout) as resp:
			data = json.loads(resp.read().decode('utf-8'))
		jobs = []
		for item in data.get('data') or []:
			loc = item.get('location') or 'Remote'
			if not is_india_location(loc) and not item.get('remote'):
				continue
			title = item.get('title') or 'Unknown role'
			desc = strip_html(item.get('description') or '')
			loc_lower = loc.lower()
			entry_hint = re.search(
				r'intern|junior|entry|fresher|graduate|trainee|new grad|engineer i\b|sde i\b',
				f'{title} {desc[:2000]}',
				re.I,
			)
			jobs.append({
				'id': f'arbeitnow-{item.get("slug") or item.get("url")}',
				'title': title,
				'company': item.get('company_name') or 'Unknown',
				'location': loc,
				'mode': 'Remote' if item.get('remote') or re.search(r'remote|wfh', loc_lower, re.I) else 'Onsite',
				'jobType': 'Full-time',
				'postedDaysAgo': 1,
				'source': 'arbeitnow',
				'salary': 'Salary not listed',
				'applyUrl': item.get('url'),
				'experienceMax': 1 if entry_hint else 3,
				'tags': ['remote'] if item.get('remote') else [],
				'description': desc[:6000],
			})
		return jobs
	except Exception:
		return []


def fetch_jobicy_jobs(timeout=10):
	try:
		url = 'https://jobicy.com/api/v2/remote-jobs'
		req = Request(url, headers={'User-Agent': 'FresherFlow/1.0'})
		with urlopen(req, timeout=timeout) as resp:
			data = json.loads(resp.read().decode('utf-8'))
		jobs = []
		for item in data.get('jobs') or []:
			title = item.get('jobTitle') or 'Unknown role'
			desc = strip_html(item.get('jobDescription') or '')
			loc = item.get('jobGeo') or 'Remote'
			loc_lower = loc.lower()
			if 'india' not in loc_lower and 'anywhere' not in loc_lower and 'world' not in loc_lower and 'global' not in loc_lower:
				continue
			entry_hint = re.search(
				r'intern|junior|entry|fresher|graduate|trainee|new grad|engineer i\b|sde i\b',
				f'{title} {desc[:2000]}',
				re.I,
			)
			jobs.append({
				'id': f'jobicy-{item.get("id")}',
				'title': title,
				'company': item.get('companyName') or 'Unknown',
				'location': loc,
				'mode': 'Remote',
				'jobType': (item.get('jobType') or 'Full-time').replace('_', ' '),
				'postedDaysAgo': estimate_posted_days(item.get('pubDate')),
				'source': 'jobicy',
				'salary': item.get('annualSalaryMin') or 'Salary not listed',
				'applyUrl': item.get('url'),
				'experienceMax': 1 if entry_hint else 3,
				'tags': [t.strip().lower() for t in item.get('jobIndustry', '').split(',') if t.strip()],
				'description': desc[:6000],
			})
		return jobs
	except Exception:
		return []


def fetch_lever_jobs(company_id, timeout=10):
	jobs = []
	try:
		url = f'https://api.lever.co/v0/postings/{company_id}?mode=json'
		req = Request(url, headers={'User-Agent': 'FresherFlow/1.0'})
		with urlopen(req, timeout=timeout) as resp:
			data = json.loads(resp.read().decode('utf-8'))
		for item in data:
			title = item.get('text') or item.get('title') or ''
			if not is_tech_title(title):
				continue
			categories = item.get('categories') or {}
			location = categories.get('location') or 'Remote'
			if not is_india_location(location) and 'remote' not in (categories.get('commitment') or '').lower():
				continue
			description = item.get('descriptionPlain') or item.get('description') or ''
			description = strip_html(description)[:6000]
			mode = 'Remote' if 'remote' in (categories.get('commitment') or '').lower() or 'remote' in location.lower() else 'Onsite'
			jobs.append({
				'id': f"lever-{item.get('id')}",
				'title': title,
				'company': company_id.upper(),
				'location': location,
				'mode': mode,
				'jobType': categories.get('commitment') or 'Full-time',
				'postedDaysAgo': 2,
				'source': 'lever',
				'salary': 'Salary not listed',
				'applyUrl': item.get('applyUrl'),
				'experienceMax': 1 if any(w in title.lower() for w in ['intern', 'junior', 'entry', 'fresher', 'grad']) else 3,
				'tags': [categories.get('team') or 'Tech', categories.get('department') or 'Engineering'],
				'description': description,
			})
	except Exception:
		pass
	return jobs


def fetch_greenhouse_jobs(company_id, timeout=10):
	jobs = []
	try:
		url = f'https://boards-api.greenhouse.io/v1/boards/{company_id}/jobs?content=true'
		req = Request(url, headers={'User-Agent': 'FresherFlow/1.0'})
		with urlopen(req, timeout=timeout) as resp:
			data = json.loads(resp.read().decode('utf-8'))
		for item in data.get('jobs') or []:
			title = item.get('title') or ''
			if not is_tech_title(title):
				continue
			location = (item.get('location') or {}).get('name') or 'Remote'
			if not is_india_location(location):
				continue
			desc = strip_html(item.get('content') or '')
			departments = [d.get('name') for d in item.get('departments') or [] if d.get('name')]
			jobs.append({
				'id': f"greenhouse-{item.get('id')}",
				'title': title,
				'company': company_id.upper(),
				'location': location,
				'mode': 'Remote' if 'remote' in location.lower() else 'Onsite',
				'jobType': 'Full-time',
				'postedDaysAgo': 2,
				'source': 'greenhouse',
				'salary': 'Salary not listed',
				'applyUrl': item.get('absolute_url'),
				'experienceMax': 1 if any(w in title.lower() for w in ['intern', 'junior', 'entry', 'fresher', 'grad']) else 3,
				'tags': departments or ['Tech'],
				'description': desc[:6000],
			})
	except Exception:
		pass
	return jobs


def dedupe_jobs(jobs):
	seen = {}
	for job in jobs:
		key = job.get('id') or job.get('applyUrl')
		if key and key not in seen:
			seen[key] = job
	return list(seen.values())


def load_seed_jobs():
	path = ROOT / 'data' / 'india_seed_jobs.json'
	try:
		data = json.loads(path.read_text(encoding='utf-8'))
		return [j for j in data.get('jobs', []) if j.get('applyUrl')]
	except Exception:
		return []


LEVER_COMPANIES = ['cred', 'meesho', 'epifi', 'fi']
GREENHOUSE_COMPANIES = ['phonepe', 'postman', 'inmobi']


def fetch_live_jobs():
	errors = []
	sources = []
	jobs = []
	try:
		muse = fetch_themuse_india()
		if muse:
			jobs.extend(muse)
			sources.append(f'The Muse India ({len(muse)})')
	except Exception as exc:
		errors.append(f'The Muse: {exc}')
	try:
		an = fetch_arbeitnow_jobs()
		if an:
			jobs.extend(an)
			sources.append(f'Arbeitnow ({len(an)})')
	except Exception as exc:
		errors.append(f'Arbeitnow: {exc}')
	try:
		jc = fetch_jobicy_jobs()
		if jc:
			jobs.extend(jc)
			sources.append(f'Jobicy ({len(jc)})')
	except Exception as exc:
		errors.append(f'Jobicy: {exc}')

	company_jobs = []
	with ThreadPoolExecutor(max_workers=10) as pool:
		lever_futures = {pool.submit(fetch_lever_jobs, c): c for c in LEVER_COMPANIES}
		greenhouse_futures = {pool.submit(fetch_greenhouse_jobs, c): c for c in GREENHOUSE_COMPANIES}
		for fut in as_completed(lever_futures):
			c = lever_futures[fut]
			try:
				res = fut.result()
				if res:
					company_jobs.extend(res)
					sources.append(f'Lever-{c.upper()} ({len(res)})')
			except Exception as exc:
				errors.append(f'Lever-{c}: {exc}')
		for fut in as_completed(greenhouse_futures):
			c = greenhouse_futures[fut]
			try:
				res = fut.result()
				if res:
					company_jobs.extend(res)
					sources.append(f'Greenhouse-{c.upper()} ({len(res)})')
			except Exception as exc:
				errors.append(f'Greenhouse-{c}: {exc}')

	if company_jobs:
		jobs.extend(company_jobs)

	seed = load_seed_jobs()
	if seed:
		jobs.extend(seed)
		sources.append(f'India seed listings ({len(seed)})')
	return {
		'jobs': dedupe_jobs(jobs),
		'sources': sources,
		'errors': errors,
		'fetchedAt': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
	}
