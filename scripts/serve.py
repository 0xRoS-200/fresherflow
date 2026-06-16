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
		if self.path != '/api/parse-resume':
			self.send_error(404, 'Not found')
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
			text = parse_upload(field)
			if not text or not text.strip():
				raise ValueError('No readable text found in this file.')
			body = json.dumps({'text': text}).encode('utf-8')
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
