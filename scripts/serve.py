#!/usr/bin/env python3
"""Static app server + reliable resume parsing (PDF/DOCX) for local dev."""
import cgi
import io
import json
import sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
DEFAULT_PORT = 8080

if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
	sys.path.insert(0, str(SCRIPTS))
from job_cache import get_jobs_payload, is_cache_stale, refresh_cache, start_background_refresh  # noqa: E402


def pick_port(start=DEFAULT_PORT):
	import socket
	for port in range(start, start + 20):
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
			try:
				sock.bind(('', port))
				return port
			except OSError:
				continue
	return start


def extract_pdf(data: bytes) -> str:
	import pdfplumber

	parts = []
	with pdfplumber.open(io.BytesIO(data)) as pdf:
		for page in pdf.pages:
			text = page.extract_text() or ''
			if text.strip():
				parts.append(text.strip())
	return '\n\n'.join(parts)


def extract_docx(data: bytes) -> str:
	from docx import Document

	doc = Document(io.BytesIO(data))
	return '\n'.join(p.text for p in doc.paragraphs if p.text and p.text.strip())


def parse_upload(field) -> str:
	if field is None or getattr(field, 'file', None) is None:
		raise ValueError('No file uploaded.')
	data = field.file.read()
	if not data:
		raise ValueError('Uploaded file is empty.')
	filename = (field.filename or '').lower()
	if filename.endswith('.pdf') or field.type == 'application/pdf':
		return extract_pdf(data)
	if filename.endswith('.docx') or 'wordprocessingml' in (field.type or ''):
		return extract_docx(data)
	if filename.endswith('.txt') or filename.endswith('.md'):
		return data.decode('utf-8', errors='replace')
	raise ValueError('Unsupported file type. Use PDF, DOCX, TXT, or MD.')


def run_llm_parser(data: bytes, filename: str):
	import tempfile
	import os
	import traceback

	filename_lower = filename.lower()
	try:
		from parser_agent import ParserAgent
		from master_cv import MasterCV, Location

		if filename_lower.endswith('.pdf'):
			temp_path = None
			try:
				with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
					tmp.write(data)
					temp_path = tmp.name

				agent = ParserAgent()
				cv = agent.parse_workflow(temp_path)
				return cv.to_json()
			finally:
				if temp_path and os.path.exists(temp_path):
					try:
						os.remove(temp_path)
					except:
						pass

		# For non-pdf files, extract text and parse using LLM
		raw_text = ""
		if filename_lower.endswith('.docx'):
			raw_text = extract_docx(data)
		elif filename_lower.endswith('.txt') or filename_lower.endswith('.md'):
			raw_text = data.decode('utf-8', errors='replace')
		else:
			return None

		if not raw_text or not raw_text.strip():
			return None

		agent = ParserAgent()
		basic_cv = MasterCV(
			name="",
			email="",
			phone="",
			location=Location(city="", country=""),
			metadata={"source": "pdf"}
		)
		basic_cv.mark_null_fields()
		enhanced_cv = agent._enhance_with_llm(raw_text, basic_cv)
		return enhanced_cv.to_json()

	except Exception as e:
		print(f"[serve.py] LLM Parser failed: {e}. Falling back to basic parser.")
		traceback.print_exc()
		return None


# ────────────────────────────────────────────────────────────────────
# SKILL KEYWORD VOCABULARY (mirrors SKILL_DICTIONARY in app.js)
# ────────────────────────────────────────────────────────────────────
_SKILL_VOCAB = [
	'java','kotlin','android','jetpack compose','xml','python','sql','excel',
	'react','javascript','typescript','node','aws','docker','linux','testing',
	'selenium','qa','data analysis','machine learning','pytorch','tensorflow',
	'rest api','git','c++','c#','html','css','communication','problem solving',
	'figma','power bi','tableau','spring boot','firebase','room','opencv','nlp',
	'fastapi','django','flask','express','mongodb','postgresql','mysql','redis',
	'kubernetes','terraform','ansible','jenkins','gcp','azure','graphql','rust',
	'go','golang','swift','scala','ruby','php','r','matlab','pandas','numpy',
	'scikit-learn','keras','huggingface','langchain','llm','openai','gemini',
	'ci/cd','devops','microservices','agile','scrum','jira','confluence','linux',
	'bash','shell','next.js','vue','angular','svelte','tailwind','bootstrap',
	'react native','flutter','unity','unreal','blockchain','solidity','web3',
]


def extract_job_keywords(cv_data: dict, job_data: dict) -> dict:
	"""
	Extract matched and missing keywords by comparing candidate CV skills
	against the full job description text (not just a fixed dictionary).

	Returns:
		{
			'matched': [...],   # skills in CV that appear in job description
			'missing': [...],   # skills in job desc NOT in CV (worth weaving in)
			'job_keywords': [...] # all extracted job keywords
		}
	"""
	import re

	# Build job text haystack
	job_haystack = ' '.join(filter(None, [
		job_data.get('title', ''),
		job_data.get('description', ''),
		' '.join(job_data.get('tags', []) or []),
	])).lower()

	# Build candidate skill set from CV
	cv_skills_raw = cv_data.get('skills', []) or []
	cv_skill_names = set()
	for s in cv_skills_raw:
		if isinstance(s, dict):
			cv_skill_names.add((s.get('name') or '').lower().strip())
		elif isinstance(s, str):
			cv_skill_names.add(s.lower().strip())

	# Also extract from experience descriptions / responsibilities
	for exp in (cv_data.get('experience') or []):
		for acc in (exp.get('rawAccomplishments') or exp.get('responsibilities') or []):
			for kw in _SKILL_VOCAB:
				if kw in acc.lower():
					cv_skill_names.add(kw)

	# Find job keywords: iterate vocab + extract tech tokens from job text
	job_keywords = set()
	for kw in _SKILL_VOCAB:
		# For short terms (<=2 chars) use word boundary
		if len(kw) <= 2:
			if re.search(r'\b' + re.escape(kw) + r'\b', job_haystack):
				job_keywords.add(kw)
		else:
			if kw in job_haystack:
				job_keywords.add(kw)

	# Also extract capitalized tokens (likely tech names) from job description
	tech_pattern = re.findall(r'\b([A-Z][a-zA-Z0-9#+.]*(?:\s[A-Z][a-zA-Z0-9#+.]*)?)\b', job_data.get('description', ''))
	for tok in tech_pattern:
		if 2 < len(tok) < 30 and tok not in {'The', 'You', 'We', 'Our', 'Job', 'About', 'Your', 'What', 'This', 'Team', 'Role', 'Work', 'Help', 'Join'}:
			job_keywords.add(tok.lower())

	matched = sorted(kw for kw in job_keywords if kw in cv_skill_names)
	missing = sorted(kw for kw in job_keywords if kw not in cv_skill_names)

	return {
		'matched': matched[:12],
		'missing': missing[:10],
		'job_keywords': sorted(job_keywords)[:20],
	}


# ────────────────────────────────────────────────────────────────────
# ELITE RESUME STRATEGIST SYSTEM PROMPT (as specified by user)
# ────────────────────────────────────────────────────────────────────
_RESUME_STRATEGIST_SYSTEM_PROMPT = """\
You are an expert resume strategist and LaTeX typesetter embedded in a resume-building application. Every resume you generate must function as a sales document, not a biography: within seconds a reader should see what problem the candidate solved, how, and what impact resulted.

You will receive one JSON object per request describing a single candidate. Some fields may be empty — omit the corresponding resume section entirely rather than leaving it blank or inventing content to fill it.

== CANDIDATE TYPE & LENGTH ==
- Use the provided `profileType` ("fresher" or "experienced") and `totalExperienceYears` fields directly. Do not recalculate experience from raw dates yourself.
- If `profileType` is missing, infer it from `totalExperienceYears`: < 1 → fresher, >= 1 → experienced.
- FRESHER layout order: Education -> Projects -> Skills -> Internships/Experience (if any) -> Achievements.
- EXPERIENCED layout order: 2-3 line Summary -> Experience -> Projects (only if strong/relevant) -> Skills -> Education (compressed).
- Page limit: totalExperienceYears < 5 -> exactly ONE page. >= 5 -> up to two pages, never more.

== CONTENT RULES ==
1. Convert every responsibility into a result using: [Action verb] + [what was built/done] + [tool/method] + [quantified outcome]. Example: "Worked on AI chatbot implementation" -> "Launched an AI-powered support feature that reduced response time by 60%."
2. NEVER invent a metric that isn't present in `rawAccomplishments`. If a bullet has no number behind it, rewrite it as a strong qualitative impact statement instead, and append `% TODO: verify metric` as a LaTeX comment directly after that line so the candidate knows to fill it in.
3. Strip unproven buzzwords ("passionate," "synergy," "hardworking," "detail-oriented," "team player") unless the same bullet already demonstrates it concretely.
4. Reverse-chronological order within every section.
5. Use only the data given — if a field/array is empty, omit that section or bullet. Under no circumstances should you invent or hallucinate any projects, experiences, achievements, or credentials. Do not pad with filler. If the user's CV does not contain any experience or projects, do not make them up.
6. KEYWORD INJECTION: The candidate JSON includes `matchedKeywords` (already in CV) and `missingKeywords` (from job description, NOT in CV). Weave `missingKeywords` naturally into bullet rewrites where the underlying accomplishment genuinely supports it. Never force-insert a keyword where it doesn't fit — context must be authentic.

== ATS / LATEX TECHNICAL RULES ==
- Single-column layout only. No tables, multicol environments, text boxes, images, icons, or colored backgrounds.
- Standard section headings only: "Summary," "Experience," "Education," "Skills," "Projects," "Certifications," "Achievements."
- Escape every LaTeX special character: % -> \%, & -> \&, $ -> \$, # -> \#, _ -> \_, { -> \{, } -> \}, ~ -> \textasciitilde{}, ^ -> \textasciicircum{}, \ -> \textbackslash{}.
- Use \href{}{} for links (LinkedIn/GitHub/portfolio).
- Standard LaTeX font (Latin Modern or Charter): 10-11.5pt body, 14-16pt name, 0.5"-0.75" margins.
- The compiled PDF text must be fully selectable.
- Define these custom commands:
  \newcommand{\resumeItem}[1]{\item\small{#1 \vspace{-2pt}}}
  \newcommand{\resumeSubheading}[4]{\vspace{-2pt}\item\begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}\textbf{#1} & #2 \\\textit{\small#3} & \textit{\small #4} \\\end{tabular*}\vspace{-7pt}}
  \newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
  \newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
  \newcommand{\resumeItemListStart}{\begin{itemize}}
  \newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-5pt}}

== OUTPUT FORMAT ==
Return ONLY the complete, compilable .tex source: full preamble through \end{document}. No explanations, no markdown code fences, no text before or after. Your entire response body IS the file contents.
"""


def _extract_preview_data_from_latex(latex_code: str, cv_data: dict) -> dict:
	"""
	Extract structured preview data from generated LaTeX for the frontend
	resume preview panel (summary, skills list, experience bullets).
	"""
	import re

	# Extract summary (between \section{Summary/Professional Summary} and next \section)
	tailored_summary = ""
	summary_match = re.search(
		r'\\section\{[^}]*(?:Summary|Profile)[^}]*\}\s*\\small\{([^}]+)\}',
		latex_code, re.IGNORECASE | re.DOTALL
	)
	if summary_match:
		tailored_summary = summary_match.group(1).strip()
	if not tailored_summary and cv_data.get('summary'):
		tailored_summary = cv_data['summary']

	# Extract skills from \textbf{...}{: ...} pattern
	optimized_skills = []
	for m in re.finditer(r'\\textbf\{[^}]+\}\{:\s*([^}]+)\}', latex_code):
		skills_str = m.group(1)
		# Strip LaTeX escapes for display
		skills_str = re.sub(r'\\[a-zA-Z]+\{?', '', skills_str).replace('}', '').strip()
		for sk in skills_str.split(','):
			sk = sk.strip()
			if sk and len(sk) > 1:
				optimized_skills.append(sk)
	if not optimized_skills:
		# Fallback: collect skills from cv_data
		for s in (cv_data.get('skills') or []):
			if isinstance(s, dict):
				optimized_skills.append(s.get('name', ''))
			elif isinstance(s, str):
				optimized_skills.append(s)

	# Extract experience bullets from \resumeItem{...} blocks
	tailored_experience = []
	exp_list = cv_data.get('experience') or []
	for exp in exp_list:
		role = exp.get('role', '') if isinstance(exp, dict) else getattr(exp, 'role', '')
		company = exp.get('company', '') if isinstance(exp, dict) else getattr(exp, 'company', '')
		# Find bullets near this company name in latex
		escaped_company = re.escape(company[:20]) if company else ''
		bullets = []
		if escaped_company:
			block_match = re.search(
				r'\{' + escaped_company + r'[^}]*\}.*?\\resumeItemListEnd',
				latex_code, re.DOTALL | re.IGNORECASE
			)
			if block_match:
				for bm in re.finditer(r'\\resumeItem\{([^}]+)\}', block_match.group()):
					bullet_text = re.sub(r'\\[a-zA-Z]+\{?', '', bm.group(1)).replace('}', '').strip()
					if bullet_text:
						bullets.append(bullet_text)
		if role or company:
			tailored_experience.append({'role': role, 'company': company, 'bullets': bullets})

	return {
		'tailored_summary': tailored_summary,
		'optimized_skills': optimized_skills[:15],
		'tailored_experience': tailored_experience,
	}


def run_llm_tailor(cv_data, job_data, matched_keywords=None, missing_keywords=None):
	import json
	from parser_agent import invoke_llm_with_fallback

	# Step 1: Extract keyword gap if not provided by frontend
	if matched_keywords is None or missing_keywords is None:
		keyword_gap = extract_job_keywords(cv_data, job_data)
		matched_keywords = keyword_gap['matched']
		missing_keywords = keyword_gap['missing']

	# Step 2: Build candidate JSON in the exact schema the elite prompt expects
	# Try using build_tailor_schema() if cv_data came from MasterCV, else build manually
	try:
		from master_cv import MasterCV, Location
		# Re-inflate MasterCV if possible for access to build_tailor_schema()
		cv_obj = MasterCV(**cv_data)
		candidate_json = cv_obj.build_tailor_schema()
	except Exception:
		# Fallback: manually build schema from raw cv_data dict
		skills_raw = cv_data.get('skills') or []
		skill_names = [s.get('name', s) if isinstance(s, dict) else s for s in skills_raw]
		candidate_json = {
			"profileType": cv_data.get('profileType', 'fresher'),
			"totalExperienceYears": float(cv_data.get('totalExperienceYears') or 0),
			"personalInfo": {
				"name": cv_data.get('name', ''),
				"phone": cv_data.get('phone', ''),
				"email": cv_data.get('email', ''),
				"location": (
					f"{cv_data.get('location', {}).get('city', '')}, "
					f"{cv_data.get('location', {}).get('country', '')}"
				).strip(', '),
				"linkedin": (cv_data.get('socialLinks') or {}).get('linkedin', ''),
				"github": (cv_data.get('socialLinks') or {}).get('github', ''),
			},
			"targetRole": cv_data.get('targetRole', ''),
			"jobDescription": job_data.get('description', '')[:1500],
			"education": [
				{
					"degree": e.get('degree', ''),
					"institution": e.get('university') or e.get('institution', ''),
					"gpa": str(e.get('gpa', '')) if e.get('gpa') else '',
					"startDate": e.get('startDate', ''),
					"endDate": e.get('endDate', '') or str(e.get('graduationYear', '')),
				}
				for e in (cv_data.get('education') or [])
			],
			"experience": [
				{
					"company": exp.get('company', ''),
					"role": exp.get('role', ''),
					"startDate": exp.get('startDate', ''),
					"endDate": exp.get('endDate', 'present'),
					"rawAccomplishments": (
						exp.get('rawAccomplishments') or
						exp.get('responsibilities') or
						([exp['description']] if exp.get('description') else [])
					),
				}
				for exp in (cv_data.get('experience') or [])
			],
			"projects": [
				{
					"name": p.get('title', p.get('name', '')),
					"techStack": (
						p.get('techStack') or
						', '.join(p.get('technologies') or [])
					),
					"rawAccomplishments": (
						p.get('rawAccomplishments') or
						([p['description']] if p.get('description') else [])
					),
				}
				for p in (cv_data.get('projects') or [])
			],
			"skills": {
				"languages": skill_names[:8],
				"frameworks": [],
				"tools": [],
			},
			"certifications": [
				c.get('name', '') for c in (cv_data.get('certifications') or [])
			],
			"achievements": cv_data.get('achievements') or [],
		}

	# Inject keyword context into candidate JSON
	candidate_json['matchedKeywords'] = matched_keywords
	candidate_json['missingKeywords'] = missing_keywords
	candidate_json['targetJobTitle'] = job_data.get('title', '')
	candidate_json['jobDescription'] = job_data.get('description', '')[:1500]

	# Step 3: Call LLM with elite system prompt — response is raw LaTeX
	print(f"[Tailor] Calling elite resume strategist (matched={len(matched_keywords)}, missing={len(missing_keywords)} keywords)...")

	latex_code = invoke_llm_with_fallback(
		system_message=_RESUME_STRATEGIST_SYSTEM_PROMPT,
		prompt_message=json.dumps(candidate_json, indent=2),
		temperature=0.15  # low temperature for precise, consistent LaTeX output
	).strip()

	# Strip markdown fences if the LLM wrapped the output
	if latex_code.startswith('```'):
		lines = latex_code.split('\n')
		latex_code = '\n'.join(
			line for line in lines
			if not line.strip().startswith('```')
		).strip()

	print(f"[Tailor] LaTeX generated ({len(latex_code)} chars). Extracting preview data...")

	# Step 4: Extract preview-friendly data from the LaTeX
	preview = _extract_preview_data_from_latex(latex_code, cv_data)

	return {
		'latex_code': latex_code,
		'tailored_summary': preview['tailored_summary'],
		'optimized_skills': preview['optimized_skills'],
		'tailored_experience': preview['tailored_experience'],
		'matched_keywords': matched_keywords,
		'missing_keywords': missing_keywords,
	}



def run_ai_fill_cv(cv_data: dict, resume_text: str = "") -> dict:
	"""
	Use LLM to infer and populate missing projects + certifications
	using the candidate's extracted skills, education, experience, and raw resume text.
	"""
	import json
	from parser_agent import invoke_llm_with_fallback

	skills = [s.get('name', s) if isinstance(s, dict) else s for s in (cv_data.get('skills') or [])]
	existing_projects = cv_data.get('projects') or []
	existing_certs = cv_data.get('certifications') or []
	experience = cv_data.get('experience') or []
	education = cv_data.get('education') or []

	prompt = f"""
You are an expert career consultant and resume builder. Based on the candidate profile below, intelligently infer and generate realistic projects and certifications that they likely have, based on their skills, education, and experience. Be realistic - only suggest things plausible given their background.

Candidate Profile:
- Name: {cv_data.get('name', 'Unknown')}
- Skills: {', '.join(skills)}
- Education: {json.dumps(education, indent=2)}
- Experience: {json.dumps(experience, indent=2)}
- Existing Projects (already extracted): {json.dumps(existing_projects, indent=2)}
- Existing Certifications (already extracted): {json.dumps(existing_certs, indent=2)}
- Raw Resume Text (for extra context):
{resume_text[:3000]}

Instructions:
1. If projects list is empty or has <2 items, suggest 2-3 plausible projects using their tech stack. Each project should be something a student/fresher with their background would realistically build.
2. If certifications list is empty, suggest 1-2 relevant free/popular certifications they likely have (e.g., Google, AWS free tier, Coursera, etc.) given their skills.
3. Do NOT invent fake company names or dates. Use approximate realistic dates.
4. Keep descriptions concise and ATS-friendly (2-3 sentences max).
5. CRITICAL: If the candidate profile has no skills, no experience, and no education, DO NOT generate any projects or certifications. Under no circumstances should you invent fake details from a blank profile. Only suggest things plausible and strictly based on their real background.

Return ONLY valid JSON matching this schema:
{{
  "projects": [
    {{
      "title": "string",
      "date": "YYYY-MM",
      "repositoryUrl": "null or URL string",
      "technologies": ["string"],
      "description": "string - 2-3 sentence ATS-friendly description"
    }}
  ],
  "certifications": [
    {{
      "name": "string",
      "issuer": "string",
      "issueDate": 2023,
      "credentialUrl": "null or URL string"
    }}
  ]
}}

Return ONLY the JSON, no other text.
"""

	try:
		response_text = invoke_llm_with_fallback(
			system_message="You are an expert resume consultant. Return valid JSON only.",
			prompt_message=prompt,
			temperature=0.3
		).strip()
		try:
			result = json.loads(response_text)
		except json.JSONDecodeError:
			import re
			json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
			if json_match:
				result = json.loads(json_match.group())
			else:
				return {'projects': existing_projects, 'certifications': existing_certs}

		# Merge: keep existing items, only add AI-generated ones if section was empty
		final_projects = existing_projects if existing_projects else result.get('projects', [])
		final_certs = existing_certs if existing_certs else result.get('certifications', [])

		return {'projects': final_projects, 'certifications': final_certs}
	except Exception as e:
		print(f"[serve.py] AI fill CV failed: {e}")
		return {'projects': existing_projects, 'certifications': existing_certs}



def compile_latex_to_pdf(latex_code: str) -> bytes:
	"""
	Compile LaTeX code to PDF using the portable TinyTeX installation.
	"""
	import subprocess
	import tempfile
	import os
	import shutil
	import re
	from parser_agent import TerminalSpinner

	# Strip \usepackage[english]{babel} (with any spacing/options) to avoid compile hangs/errors
	latex_code = re.sub(r'\\usepackage\s*\[\s*english\s*\]\s*\{\s*babel\s*\}', '', latex_code)

	# 1. Resolve pdflatex path inside %APPDATA%/TinyTeX
	appdata_path = os.environ.get('APPDATA')
	if not appdata_path:
		appdata_path = os.path.expandvars('%APPDATA%')
	
	pdflatex_path = os.path.join(appdata_path, 'TinyTeX', 'bin', 'windows', 'pdflatex.exe')
	if not os.path.exists(pdflatex_path):
		userprofile = os.environ.get('USERPROFILE')
		if userprofile:
			pdflatex_path = os.path.join(userprofile, 'AppData', 'Roaming', 'TinyTeX', 'bin', 'windows', 'pdflatex.exe')
	
	if not os.path.exists(pdflatex_path):
		raise FileNotFoundError(f"pdflatex.exe not found at: {pdflatex_path}. Ensure TinyTeX is installed.")

	# 2. Create a temporary folder inside the workspace
	workspace_tmp = ROOT / 'tmp_compile'
	workspace_tmp.mkdir(exist_ok=True)
	
	temp_dir = tempfile.mkdtemp(dir=str(workspace_tmp))
	try:
		tex_file_path = os.path.join(temp_dir, 'resume.tex')
		with open(tex_file_path, 'w', encoding='utf-8') as f:
			f.write(latex_code)
		
		# 3. Invoke pdflatex.exe
		cmd = [
			pdflatex_path,
			'-interaction=nonstopmode',
			'-halt-on-error',
			'resume.tex'
		]
		print(f"[serve.py] Compiling LaTeX with TinyTeX: {' '.join(cmd)}")
		
		with TerminalSpinner("Compiling LaTeX resume to PDF via TinyTeX..."):
			# First pass
			result = subprocess.run(
				cmd,
				cwd=temp_dir,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				text=True,
				timeout=20
			)
			
			if result.returncode != 0:
				print(f"[serve.py] pdflatex failed with exit code {result.returncode}")
				print(f"Stdout:\n{result.stdout}")
				print(f"Stderr:\n{result.stderr}")
				
				error_lines = [line for line in (result.stdout or "").split('\n') if line.startswith('!') or 'Error' in line]
				error_msg = "\n".join(error_lines[:5])
				raise RuntimeError(f"LaTeX compile error:\n{error_msg}")

			# Second pass to resolve hyperref links and table columns
			subprocess.run(
				cmd,
				cwd=temp_dir,
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				timeout=15
			)
		
		pdf_file_path = os.path.join(temp_dir, 'resume.pdf')
		if not os.path.exists(pdf_file_path):
			raise FileNotFoundError("pdflatex reported success but resume.pdf was not created.")
			
		with open(pdf_file_path, 'rb') as f:
			pdf_data = f.read()
			
		return pdf_data

	finally:
		try:
			shutil.rmtree(temp_dir)
		except Exception as e:
			print(f"[serve.py] Warning: failed to clean up temp dir {temp_dir}: {e}")


class FresherFlowHandler(SimpleHTTPRequestHandler):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, directory=str(ROOT), **kwargs)

	def log_message(self, fmt, *args):
		sys.stderr.write('%s - - [%s] %s\n' % (self.address_string(), self.log_date_time_string(), fmt % args))

	def _send_json(self, status, payload):
		body = json.dumps(payload).encode('utf-8')
		self.send_response(status)
		self.send_header('Content-Type', 'application/json; charset=utf-8')
		self.send_header('Content-Length', str(len(body)))
		self.send_header('Cache-Control', 'no-store')
		self.end_headers()
		self.wfile.write(body)

	def do_GET(self):
		if self.path == '/api/jobs' or self.path.startswith('/api/jobs?'):
			try:
				force = 'refresh=1' in self.path or 'force=1' in self.path
				if force:
					payload = refresh_cache(force=True)
				else:
					payload = get_jobs_payload()
					if is_cache_stale():
						import threading
						threading.Thread(target=refresh_cache, kwargs={'force': True}, daemon=True).start()
				self._send_json(200, payload)
			except Exception as exc:
				self._send_json(500, {'jobs': [], 'sources': [], 'errors': [str(exc)]})
			return
		return super().do_GET()

	def do_POST(self):
		if self.path not in ('/api/parse-resume', '/api/tailor-resume', '/api/ai-fill-cv', '/api/job-keywords', '/api/compile-pdf'):
			self.send_error(404, 'Not found')
			return

		if self.path == '/api/job-keywords':
			try:
				length = int(self.headers.get('Content-Length', '0') or 0)
				post_data = self.rfile.read(length).decode('utf-8')
				payload = json.loads(post_data)
				cv_data = payload.get('cv', {})
				job_data = payload.get('job', {})
				result = extract_job_keywords(cv_data, job_data)
				self._send_json(200, result)
			except Exception as exc:
				self._send_json(400, {'error': str(exc)})
			return

		if self.path == '/api/ai-fill-cv':
			try:
				length = int(self.headers.get('Content-Length', '0') or 0)
				post_data = self.rfile.read(length).decode('utf-8')
				payload = json.loads(post_data)
				cv_data = payload.get('cv', {})
				resume_text = payload.get('resume_text', '')

				# Validate that there is relevant info to base suggestions on
				skills = cv_data.get('skills', [])
				experience = cv_data.get('experience', [])
				education = cv_data.get('education', [])
				if not skills and not experience and not education:
					raise ValueError("No profile details found (skills, experience, and education are empty). Please enter some information first.")

				result = run_ai_fill_cv(cv_data, resume_text)
				self._send_json(200, result)
			except Exception as exc:
				self._send_json(400, {'error': str(exc)})
			return



		if self.path == '/api/tailor-resume':
			try:
				length = int(self.headers.get('Content-Length', '0') or 0)
				post_data = self.rfile.read(length).decode('utf-8')
				payload = json.loads(post_data)
				cv_data = payload.get('cv')
				job_data = payload.get('job')
				# Accept pre-computed keywords from frontend (optional)
				matched_kw = payload.get('matched_keywords')
				missing_kw = payload.get('missing_keywords')

				if not cv_data or not job_data:
					raise ValueError('Both cv and job payloads are required.')

				tailor_result = run_llm_tailor(cv_data, job_data, matched_kw, missing_kw)
				self._send_json(200, tailor_result)
			except Exception as exc:
				self._send_json(400, {'error': str(exc)})
			return

		if self.path == '/api/compile-pdf':
			try:
				length = int(self.headers.get('Content-Length', '0') or 0)
				post_data = self.rfile.read(length).decode('utf-8')
				payload = json.loads(post_data)
				latex_code = payload.get('latex_code')
				if not latex_code:
					raise ValueError('latex_code is required.')

				pdf_data = compile_latex_to_pdf(latex_code)
				if not pdf_data:
					raise RuntimeError('Failed to compile LaTeX to PDF.')

				self.send_response(200)
				self.send_header('Content-Type', 'application/pdf')
				self.send_header('Content-Length', str(len(pdf_data)))
				self.send_header('Cache-Control', 'no-store')
				self.end_headers()
				self.wfile.write(pdf_data)
			except Exception as exc:
				self._send_json(400, {'error': str(exc)})
			return

		try:
			ctype = self.headers.get('Content-Type', '')
			if 'multipart/form-data' not in ctype:
				raise ValueError('Expected multipart form upload.')
			length = int(self.headers.get('Content-Length', '0') or 0)
			form = cgi.FieldStorage(
				fp=self.rfile,
				headers=self.headers,
				environ={
					'REQUEST_METHOD': 'POST',
					'CONTENT_TYPE': ctype,
					'CONTENT_LENGTH': str(length),
				},
			)
			field = form['file']
			if isinstance(field, list):
				field = field[0]

			if field is None or getattr(field, 'file', None) is None:
				raise ValueError('No file uploaded.')

			data = field.file.read()
			if not data:
				raise ValueError('Uploaded file is empty.')

			filename = (field.filename or '').lower()

			# Try LLM parsing
			result = None
			try:
				result = run_llm_parser(data, filename)
			except Exception as e:
				print(f"[serve.py] Error in run_llm_parser: {e}")

			if filename.endswith('.pdf') or field.type == 'application/pdf':
				raw_text = extract_pdf(data)
			elif filename.endswith('.docx') or 'wordprocessingml' in (field.type or ''):
				raw_text = extract_docx(data)
			elif filename.endswith('.txt') or filename.endswith('.md'):
				raw_text = data.decode('utf-8', errors='replace')
			else:
				raise ValueError('Unsupported file type. Use PDF, DOCX, TXT, or MD.')

			if not raw_text or not raw_text.strip():
				raise ValueError('No readable text found in this file.')

			response_payload = {"text": raw_text}
			if result:
				response_payload.update(result)

			body = json.dumps(response_payload).encode('utf-8')
			self.send_response(200)
			self.send_header('Content-Type', 'application/json; charset=utf-8')
			self.send_header('Content-Length', str(len(body)))
			self.end_headers()
			self.wfile.write(body)
		except Exception as exc:
			body = json.dumps({'error': str(exc)}).encode('utf-8')
			self.send_response(400)
			self.send_header('Content-Type', 'application/json; charset=utf-8')
			self.send_header('Content-Length', str(len(body)))
			self.end_headers()
			self.wfile.write(body)


def main():
	try:
		import pdfplumber  # noqa: F401
	except ImportError:
		print('Install dependencies: pip3 install -r requirements.txt')
		sys.exit(1)
	port = pick_port()
	server = ThreadingHTTPServer(('', port), FresherFlowHandler)
	print(f'FresherFlow running at http://localhost:{port}')
	if port != DEFAULT_PORT:
		print(f'(Port {DEFAULT_PORT} was busy — stop old servers with: lsof -ti:{DEFAULT_PORT} | xargs kill)')
	print('Resume PDF/DOCX parsing: POST /api/parse-resume')
	print('Live India jobs: GET /api/jobs')
	print('Background job fetch: every 2 hours (keep this terminal open)')
	start_background_refresh()
	server.serve_forever()


if __name__ == '__main__':
	main()
