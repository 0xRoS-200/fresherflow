const SKILL_DICTIONARY = ['java','kotlin','android','jetpack compose','xml','python','sql','excel','react','javascript','typescript','node','aws','docker','linux','testing','selenium','qa','data analysis','machine learning','pytorch','tensorflow','rest api','git','c++','c','html','css','communication','problem solving','figma','power bi','tableau','spring boot','firebase','room','opencv','nlp'];
const trustedSources = new Set(['arbeitnow','remotive','themuse','jobicy','lever','manual','company-site','official-portal','greenhouse']);
const PDF_CMAP_URL = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/cmaps/';
const JOB_REFRESH_MS = 2 * 60 * 60 * 1000;
let jobsLoading = false;
let jobsAutoRefreshTimer = null;
let state = { extractedSkills: [], saved: new Set(), showSavedOnly: false, jobs: [], mlMode: true, agentMatches: [], agentStatus: 'Agent is idle.', agentActive: false, jobsFeedMeta: null };
const el = id => document.getElementById(id);
const unique = a => [...new Set(a)];
function skillInHay(hay, skill){
	const s = (skill || '').toLowerCase();
	if(s.length <= 2){
		const re = new RegExp(`\\b${s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
		return re.test(hay);
	}
	return hay.includes(s);
}
const includesAny = (t, terms) => terms.filter(x => skillInHay(t, x));
const DEFAULT_ROLE_KEYWORDS = ['software engineer','software development engineer','developer','engineer','sde','swe','programmer','backend','frontend','full stack','fullstack','web developer','react','mern'];
const INDIA_MARKERS = ['india','indian','bengaluru','bangalore','hyderabad','pune','chennai','mumbai','delhi','gurugram','gurgaon','noida','kolkata','ahmedabad'];
const NON_INDIA_MARKERS = ['czechia','czech republic','prague','germany','serbia','romania','buenos aires','argentina','poland','hungary','spain','uk only','united kingdom only','usa ·','· usa','japan','korea'];
const SENIOR_RE = /\b(senior|sr|lead|principal|staff|architect|head of|director|manager|technical lead|engineering manager)\b|\b(engineer|sde|sre|qa|developer|analyst)[\s-]*([2-9]|ii+|iv|v|vi*)\b/i;
const ENTRY_RE = /\b(fresher|entry[- ]?level|graduate|internship|\bintern\b|junior|jr\.?\s|trainee|new grad|0[-–]2\s*years?|1[-–]3\s*years?|up to 3 years|0-3 years)\b/i;
const NON_ENTRY_EXP_RE = /\b(at least 3 years|minimum 3 years|3\+ years|4\+ years|5\+ years|6\+ years|7\+ years|8\+ years|10\+ years|three years of|five years of)\b/i;
const NON_SOFTWARE_TITLE_RE = /\b(bot developer|data scraping|data analyst|data scientist|machine learning engineer|ml engineer|data engineer|product manager|product design|site reliability|sre\b|customer support|technical support engineer|salesforce|freelance|werkstudent|compliance engineer|business development|risk analyst|marketing manager|sales development)\b/i;
function escapeHtml(text){
	return String(text ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function jobHaystack(job){return [job.title,job.description,job.location,...(job.tags||[])].join(' ').toLowerCase();}
function isIndiaJob(job){
	const loc = (job.location||'').toLowerCase();
	const hay = `${loc} ${(job.description||'').slice(0,400).toLowerCase()}`;
	if(INDIA_MARKERS.some(m => loc.includes(m) || hay.includes(m))) return true;
	if(NON_INDIA_MARKERS.some(m => hay.includes(m)) && !INDIA_MARKERS.some(m => hay.includes(m))) return false;
	return false;
}
function locationMatches(job, location){
	if(!location) return true;
	const wanted = location.toLowerCase();
	if(wanted === 'india') return isIndiaJob(job);
	const jobLocation = (job.location||'').toLowerCase();
	if(wanted === 'remote') return job.mode==='Remote' && (jobLocation.includes('india') || jobLocation.includes('flexible') || jobLocation.includes('remote'));
	if(wanted === 'delhi') return jobLocation.includes('delhi') || jobLocation.includes('noida') || jobLocation.includes('gurgaon') || jobLocation.includes('gurugram');
	if(wanted === 'mumbai') return jobLocation.includes('mumbai') || jobLocation.includes('thane') || jobLocation.includes('navi mumbai');
	if(jobLocation.includes(wanted)) return true;
	if(['bangalore','bengaluru'].includes(wanted)) return jobLocation.includes('bengaluru') || jobLocation.includes('bangalore');
	return false;
}
function extractSkills(text){const t=(text||'').toLowerCase(); return unique(SKILL_DICTIONARY.filter(s=>t.includes(s)));}
function isSeniorRole(job){
	const title = job.title || '';
	if(SENIOR_RE.test(title)) return true;
	const expPattern = /\b([3-9]|1[0-9])\s*(to|-|–|\+)?\s*([3-9]|1[0-9])?\s*(years?|yrs)\b/i;
	if(expPattern.test(title)) return true;
	const desc = job.description || '';
	if(expPattern.test(desc)) return true;
	return false;
}
function isEntryLevel(job){
	if(isSeniorRole(job)) return false;
	const title = (job.title||'').toLowerCase();
	const hay = jobHaystack(job);
	const tagHay = (job.tags || []).join(' ');
	if(NON_ENTRY_EXP_RE.test(hay) && !ENTRY_RE.test(title) && !ENTRY_RE.test(tagHay)) return false;
	if(ENTRY_RE.test(title) || ENTRY_RE.test(tagHay) || ENTRY_RE.test(hay.slice(0, 1200))) return true;
	if(/\/intern\b|internship|graduate trainee|fresher/i.test(hay.slice(0, 800))) return true;
	if(/\b(engineer|developer|sde|swe)\b/.test(title) && /\b(i\b| 1\b|level 1)\b/.test(title)) return true;
	const roleKeys = DEFAULT_ROLE_KEYWORDS;
	if(isSoftwareRole(job, roleKeys) && /\b(software engineer|software development engineer|frontend engineer|backend engineer|full[\s-]?stack|fullstack|web developer|sde|developer|programmer)\b/.test(title)){
		if(!NON_ENTRY_EXP_RE.test(hay.slice(0, 2200))) return true;
	}
	if(/\b(customer success engineer|technical services engineer)\b/.test(title) && !NON_ENTRY_EXP_RE.test(hay.slice(0, 2200))) return true;
	return false;
}
function isSoftwareRole(job, roleKeywords){
	const title = (job.title||'').toLowerCase();
	const isCustom = roleKeywords && roleKeywords.length > 0 && roleKeywords !== DEFAULT_ROLE_KEYWORDS;
	if(!isCustom && NON_SOFTWARE_TITLE_RE.test(title)) return false;
	const keywords = roleKeywords && roleKeywords.length ? roleKeywords : DEFAULT_ROLE_KEYWORDS;
	return includesAny(jobHaystack(job), keywords.map(k => k.toLowerCase())).length > 0;
}
function isFresher(job){return isEntryLevel(job) && isSoftwareRole(job, DEFAULT_ROLE_KEYWORDS);}
function getRoleKeywords(filters){
	return filters.roleKeywords.length ? filters.roleKeywords : DEFAULT_ROLE_KEYWORDS;
}
function buildJobHighlights(job, reasons, skillMatches){
	const bullets = [];
	bullets.push(`${job.company} · ${job.location} · ${job.mode} · ${job.jobType}`);
	if(skillMatches.length) bullets.push(`CV skills matched: ${skillMatches.slice(0,6).join(', ')}`);
	reasons.filter(r => !/CV skill/i.test(r)).slice(0,2).forEach(r => bullets.push(r));
	const desc = (job.description||'').replace(/\s+/g,' ').trim();
	const sentences = desc.split(/(?<=[.!?])\s+/).map(s => s.trim()).filter(Boolean);
	const picked = sentences.filter(s =>
		s.length >= 35 && s.length <= 200 &&
		!/company description|who we are|about us|our values|benefits include|equal opportunity|posting statement/i.test(s) &&
		/responsib|require|qualif|skill|engineer|develop|experience|year|india|remote|python|java|react|role/i.test(s)
	).slice(0, 3);
	bullets.push(...picked);
	return unique(bullets).slice(0, 5);
}
function buildFilters(){return { roleKeywords: el('roleKeywords').value.split(',').map(s=>s.trim().toLowerCase()).filter(Boolean), location: el('location').value, mode: el('mode').value, jobType: el('jobType').value, postedWithin: Number(el('postedWithin').value||365), minScore: 0, remoteOnly: el('remoteOnly').checked, fresherOnly: el('fresherOnly').checked, trustedOnly: el('trustedOnly').checked };}
function buildAgentFilters(){return buildFilters();}
function baseScore(job, filters){
	const hay = jobHaystack(job);
	const roleKeys = getRoleKeywords(filters);
	let score = 0, reasons = [];
	const skillMatches = includesAny(hay, state.extractedSkills);
	if(skillMatches.length){ score += Math.min(45, skillMatches.length * 10); reasons.push(`${skillMatches.length} CV skill matches`); }
	const roleMatches = includesAny(hay, roleKeys);
	if(roleMatches.length){ score += Math.min(20, roleMatches.length * 10); reasons.push(`${roleMatches.length} role matches`); }
	if(filters.location && locationMatches(job, filters.location)){ score += 12; reasons.push('India / preferred location'); }
	if(isEntryLevel(job) && isSoftwareRole(job, roleKeys)){ score += 14; reasons.push('entry-level software role'); }
	if(isSeniorRole(job)){ score -= 35; reasons.push('senior role — hidden by default'); }
	if(!isIndiaJob(job) && (filters.location || '').toLowerCase() === 'india'){ score -= 40; }
	if(job.mode === 'Remote'){ score += 6; reasons.push('remote option'); }
	score += Math.max(0, 10 - Math.min(job.postedDaysAgo || 0, 10));
	if((job.postedDaysAgo || 99) <= 7) reasons.push('recent');
	if(trustedSources.has((job.source || '').toLowerCase())){ score += 4; reasons.push('trusted source'); }
	return { score: Math.max(0, Math.min(score, 100)), reasons: unique(reasons), skillMatches };
}
function mlScore(job, filters){
	const base = baseScore(job, filters);
	const hay = jobHaystack(job);
	const roleKeys = getRoleKeywords(filters);
	const s = includesAny(hay, state.extractedSkills).length;
	const r = includesAny(hay, roleKeys).length;
	const entry = isEntryLevel(job) && isSoftwareRole(job, roleKeys) ? 1 : 0;
	const senior = isSeniorRole(job) ? 1 : 0;
	const india = filters.location && locationMatches(job, filters.location) ? 1 : 0;
	const remote = job.mode === 'Remote' ? 1 : 0;
	const trusted = trustedSources.has((job.source || '').toLowerCase()) ? 1 : 0;
	const recency = Math.max(0, 1 - Math.min(job.postedDaysAgo || 30, 30) / 30);
	let z = -2.2 + s * 0.55 + r * 0.35 + entry * 1.1 - senior * 1.4 + india * 0.65 + remote * 0.2 + trusted * 0.15 + recency * 0.35;
	const p = 1 / (1 + Math.exp(-z));
	return { score: Math.round(p * 100), reasons: base.reasons, skillMatches: base.skillMatches };
}
function passes(job, filters, scored){
	if(state.showSavedOnly && !state.saved.has(job.id)) return false;
	
	if(filters.fresherOnly) {
		if(isSeniorRole(job)) return false;
		if(!isEntryLevel(job)) return false;
		const roleKeys = getRoleKeywords(filters);
		if(!isSoftwareRole(job, roleKeys)) return false;
	} else {
		if(filters.roleKeywords.length > 0) {
			const hay = jobHaystack(job);
			if(includesAny(hay, filters.roleKeywords).length === 0) return false;
		}
	}
	
	if(filters.remoteOnly && job.mode !== 'Remote') return false;
	if(filters.trustedOnly && !trustedSources.has((job.source || '').toLowerCase())) return false;
	if(filters.location && !locationMatches(job, filters.location)) return false;
	if(state.extractedSkills.length){
		const hay = jobHaystack(job);
		const skillHits = includesAny(hay, state.extractedSkills);
		const roleKeys = getRoleKeywords(filters);
		const roleHits = includesAny(hay, roleKeys);
		if(!skillHits.length && !roleHits.length) return false;
	}
	if(filters.mode && job.mode !== filters.mode) return false;
	if(filters.jobType && job.jobType !== filters.jobType) return false;
	if((job.postedDaysAgo || 999) > filters.postedWithin) return false;
	if(scored.score < filters.minScore) return false;
	return true;
}
function renderChips(filters){const chips=[...state.extractedSkills.map(s=>`Skill: ${s}`)]; if(filters.roleKeywords.length) chips.push(`Roles: ${filters.roleKeywords.join(', ')}`); if(filters.location) chips.push(`Location: ${filters.location}`); if(filters.mode) chips.push(`Mode: ${filters.mode}`); if(filters.jobType) chips.push(`Type: ${filters.jobType}`); if(filters.postedWithin<365) chips.push(`Posted: ${filters.postedWithin}d`); if(filters.remoteOnly) chips.push('Remote only'); if(filters.fresherOnly) chips.push('Entry-level software'); if(filters.trustedOnly) chips.push('Trusted only'); if(state.showSavedOnly) chips.push('Saved only'); if(state.mlMode) chips.push('Relevance ranking'); el('activeChips').innerHTML = chips.map(c=>`<span class="chip">${c}</span>`).join(''); el('extractedSkills').innerHTML = state.extractedSkills.map(c=>`<span class="chip">${c}</span>`).join('');}
function getAgentMatches(filters, limit=3){const scorer=state.mlMode?mlScore:baseScore; return state.jobs.map(job=>({job,...scorer(job,filters)})).filter(row=>passes(row.job,filters,row)).sort((a,b)=>b.score-a.score).slice(0,limit);}
function updateAgentStatus(message){state.agentStatus = message; const target = el('agentStatus'); if(target) target.textContent = message;}
async function runAgent(){
	try{
		await loadJobs({ refresh: true });
	}catch(e){
		console.warn('Job refresh failed', e);
	}
	const filters = buildAgentFilters();
	if(!el('resumeText').value.trim() && state.extractedSkills.length===0){
		updateAgentStatus('Paste a resume or select a file before running the agent.');
		return;
	}
	if(state.extractedSkills.length===0){
		state.extractedSkills = extractSkills(el('resumeText').value);
	}
	const matches = sortJobRows(state.jobs.map(job => ({ job, ...(state.mlMode ? mlScore(job, filters) : baseScore(job, filters)) })).filter(row => passes(row.job, filters, row)), el('sortBy').value);
	state.agentMatches = matches; state.agentActive = true;
	if(!matches.length){
		updateAgentStatus('No matches yet. Extract skills, widen filters, or uncheck Entry-level only.');
		return;
	}
	const summary = matches.slice(0,5).map((m,i)=>`${i+1}. ${m.job.title} @ ${m.job.company} (${m.score}%)`).join(' | ');
	updateAgentStatus(`Agent found ${matches.length} personalized jobs. Top: ${summary}`);
	render();
}
function openAgentMatches(){if(!state.agentMatches.length){runAgent(); if(!state.agentMatches.length) return;} const topMatches = state.agentMatches.slice(0, 10); topMatches.forEach(match=>{window.open(match.job.applyUrl,'_blank'); state.saved.add(match.job.id);}); updateAgentStatus(`Opened ${topMatches.length} personalized fresher apply links and saved them.`); render();}
function escapeCSVValue(val) {
	if (val === null || val === undefined) return '';
	let str = '';
	if (Array.isArray(val)) {
		str = val.join(' · ');
	} else {
		str = String(val);
	}
	const escaped = str.replace(/"/g, '""');
	if (escaped.includes('"') || escaped.includes(',') || escaped.includes('\n') || escaped.includes('\r')) {
		return `"${escaped}"`;
	}
	return str;
}
function convertToCSV(rows) {
	if (!rows.length) return '';
	const headers = Object.keys(rows[0]);
	const headerLine = headers.join(',');
	const dataLines = rows.map(row => 
		headers.map(header => escapeCSVValue(row[header])).join(',')
	);
	return [headerLine, ...dataLines].join('\r\n');
}
function exportAgentMatches(){if(!state.agentMatches.length){runAgent(); if(!state.agentMatches.length) return;} const rows=state.agentMatches.map(m=>({id:m.job.id,title:m.job.title,company:m.job.company,location:m.job.location,mode:m.job.mode,jobType:m.job.jobType,score:m.score,applyUrl:m.job.applyUrl})); const csvContent=convertToCSV(rows); const blob=new Blob([csvContent],{type:'text/csv;charset=utf-8;'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='agent-shortlist.csv'; a.click(); URL.revokeObjectURL(a.href); updateAgentStatus(`Exported ${rows.length} agent-selected jobs to CSV.`);}
function render(){const filters=buildFilters(); renderChips(filters); let rows; if(state.agentActive){rows = state.agentMatches;} else {const scorer=state.mlMode ? mlScore : baseScore; rows=sortJobRows(state.jobs.map(job=>({job,...scorer(job,filters)})).filter(row=>passes(row.job,filters,row)), el('sortBy').value);} 	if(!rows.length){
		const hint = state.jobs.length
			? `<p class="muted">${state.jobs.length} jobs loaded, but none pass your filters (India + entry-level software). Try unchecking "Entry-level software only" or set Location to a city like Bengaluru.</p>`
			: '<p class="muted">Run <code>bash run.sh</code> and open http://localhost:8080</p>';
		el('results').innerHTML=`<div class="empty"><h3>No matching jobs</h3>${hint}</div>`;
		return;
	}
	el('results').innerHTML = rows.map(({job,score,reasons,skillMatches})=>{
		const skills = skillMatches || includesAny(jobHaystack(job), state.extractedSkills);
		const highlights = buildJobHighlights(job, reasons, skills);
		const newBadge = job.isNew ? '<span class="badge badge-new">New</span>' : '';
		return `<article class="job-card${job.isNew ? ' job-card-new' : ''}"><div class="job-head"><div><h3>${escapeHtml(job.title)}</h3><div class="muted small">${escapeHtml(job.company)} · ${escapeHtml(job.location)} · ${escapeHtml(job.mode)} · ${escapeHtml(job.jobType)}</div></div><div class="score">${score}</div></div><div class="meta">${newBadge}<span class="badge">${escapeHtml(job.source)}</span><span class="badge">Posted ${job.postedDaysAgo ?? '?'}d ago</span><span class="badge salary">${escapeHtml(job.salary || 'Salary not listed')}</span></div><ul class="job-highlights">${highlights.map(h=>`<li>${escapeHtml(h)}</li>`).join('')}</ul><p class="why small">Fit: ${escapeHtml(reasons.join(' · '))}</p><div class="chips">${(job.tags||[]).slice(0,6).map(t=>`<span class="chip">${escapeHtml(t)}</span>`).join('')}</div><div class="job-actions" style="margin-top:1rem"><a class="btn btn-primary" href="${escapeHtml(job.applyUrl)}" target="_blank" rel="noopener noreferrer">Apply on source</a><button class="btn btn-secondary" onclick="toggleSave(${JSON.stringify(job.id)})">${state.saved.has(job.id)?'Unsave':'Save'}</button></div></article>`;
	}).join('');
}
function toggleSave(id){if(state.saved.has(id)) state.saved.delete(id); else state.saved.add(id); render();}
window.toggleSave = toggleSave;
function setJobsFeedMessage(message){
	const target = el('jobsFeedStatus');
	if(target) target.textContent = message || '';
}
function formatRelativeTime(iso){
	if(!iso) return '';
	const then = Date.parse(iso);
	if(Number.isNaN(then)) return '';
	const mins = Math.floor((Date.now() - then) / 60000);
	if(mins < 1) return 'just now';
	if(mins < 60) return `${mins}m ago`;
	const hrs = Math.floor(mins / 60);
	if(hrs < 48) return `${hrs}h ago`;
	return `${Math.floor(hrs / 24)}d ago`;
}
function formatUntil(iso){
	if(!iso) return '';
	const diff = Date.parse(iso) - Date.now();
	if(Number.isNaN(diff) || diff <= 0) return 'soon';
	const mins = Math.ceil(diff / 60000);
	if(mins < 60) return `in ${mins}m`;
	const hrs = Math.floor(mins / 60);
	const rem = mins % 60;
	return rem ? `in ${hrs}h ${rem}m` : `in ${hrs}h`;
}
function buildJobsFeedMessage(meta, jobCount){
	const parts = [];
	if(meta?.fetchedAt) parts.push(`Updated ${formatRelativeTime(meta.fetchedAt)}`);
	if(meta?.newCount > 0) parts.push(`${meta.newCount} new since last sync`);
	if(meta?.nextRefreshAt) parts.push(`next auto-refresh ${formatUntil(meta.nextRefreshAt)}`);
	if(meta?.sources?.length) parts.push(`sources: ${meta.sources.join(', ')}`);
	const summary = parts.length ? parts.join(' · ') : 'Job feed ready';
	return jobCount != null ? `${summary} (${jobCount} listings)` : summary;
}
function getLocationPriority(job) {
	const loc = (job.location || '').toLowerCase();
	if (loc.includes('bangalore') || loc.includes('bengaluru')) return 0;
	if (loc.includes('india') || loc.includes('indian') || /hyderabad|pune|chennai|mumbai|delhi|gurugram|gurgaon|noida|kolkata|ahmedabad|karnataka|maharashtra|telangana|tamil nadu/i.test(loc)) return 1;
	if (job.mode === 'Remote' || loc.includes('remote') || loc.includes('flexible') || loc.includes('anywhere')) return 2;
	return 3;
}
function sortJobRows(rows, sortBy){
	const mode = sortBy || 'recent';
	return rows.sort((a, b) => {
		if(mode === 'score') {
			const pA = getLocationPriority(a.job);
			const pB = getLocationPriority(b.job);
			if(pA !== pB) return pA - pB;
			if(b.score !== a.score) return b.score - a.score;
			const pa = a.job.postedDaysAgo ?? 999;
			const pb = b.job.postedDaysAgo ?? 999;
			return pa - pb;
		}
		const pa = a.job.postedDaysAgo ?? 999;
		const pb = b.job.postedDaysAgo ?? 999;
		if(pa !== pb) return pa - pb;
		if(mode === 'company') return a.job.company.localeCompare(b.job.company) || b.score - a.score;
		return b.score - a.score;
	});
}
function scheduleJobsAutoRefresh(){
	if(jobsAutoRefreshTimer) clearInterval(jobsAutoRefreshTimer);
	jobsAutoRefreshTimer = setInterval(() => loadJobs({ refresh: canUseServerParser(), quiet: true }), JOB_REFRESH_MS);
}
function applyJobsPayload(payload){
	const { jobs, sources, errors, fetchedAt, nextRefreshAt, newCount } = payload;
	state.jobs = jobs;
	state.jobsFeedMeta = { sources, errors, fetchedAt, nextRefreshAt, newCount };
	let msg = buildJobsFeedMessage(state.jobsFeedMeta, jobs.length);
	if(errors?.length) msg += ` (${errors.length} source(s) unavailable)`;
	setJobsFeedMessage(msg);
	render();
}
async function fetchStaticJobsFeed({ bust = false } = {}){
	if(location.protocol === 'file:') return null;
	const q = bust ? `?t=${Date.now()}` : '';
	try{
		const resp = await fetch(`./data/jobs_live_cache.json${q}`, { cache: 'no-store' });
		if(!resp.ok) return null;
		const data = await resp.json();
		if(Array.isArray(data.jobs) && data.jobs.length) return data;
	}catch(_e){ /* try seed */ }
	try{
		const resp = await fetch(`./data/india_seed_jobs.json${q}`, { cache: 'no-store' });
		if(!resp.ok) return null;
		const data = await resp.json();
		if(!Array.isArray(data.jobs) || !data.jobs.length) return null;
		return {
			jobs: data.jobs,
			sources: ['India seed listings'],
			errors: [],
			fetchedAt: data.generated_at || null,
			newCount: 0,
		};
	}catch(_e){ return null; }
}
async function fetchJobsFromServer({ force = false } = {}){
	const url = force ? '/api/jobs?refresh=1' : '/api/jobs';
	const resp = await fetch(url, { cache: 'no-store' });
	const data = await resp.json().catch(() => ({}));
	if(!resp.ok) throw new Error(data.errors?.[0] || 'Server jobs API failed');
	return data;
}
async function loadJobs({ refresh = false, quiet = false } = {}){
	if(jobsLoading && !refresh && !quiet) return;
	jobsLoading = true;
	const refreshBtn = el('refreshJobsBtn');
	if(refreshBtn) refreshBtn.disabled = true;
	try{
		if(location.protocol === 'file:'){
			setJobsFeedMessage('Run bash run.sh and open http://localhost:8080');
			el('results').innerHTML='<div class="empty"><h3>Start the app once</h3><p class="muted">Run <code>bash run.sh</code> in the project folder, then open <code>http://localhost:8080</code>. Jobs update every 2 hours automatically.</p></div>';
			return;
		}
		if(!quiet) setJobsFeedMessage('Loading job feed…');
		let payload = null;
		if(canUseServerParser()){
			try{
				payload = await fetchJobsFromServer({ force: refresh });
			}catch(_e){ /* fall back to file cache */ }
		}
		if(!payload?.jobs?.length){
			payload = await fetchStaticJobsFeed({ bust: refresh || !payload });
		}
		if(payload?.jobs?.length){
			applyJobsPayload(payload);
			return;
		}
		setJobsFeedMessage('Job feed unavailable. Is bash run.sh still running?');
		el('results').innerHTML='<div class="empty"><h3>No job feed</h3><p class="muted">Run <code>bash run.sh</code> once and keep the terminal open. It fetches jobs every 2 hours automatically.</p></div>';
	}catch(e){
		if(state.jobs.length){
			setJobsFeedMessage(`Showing ${state.jobs.length} jobs (offline copy).`);
			render();
		}else{
			setJobsFeedMessage('Could not load jobs.');
			el('results').innerHTML='<div class="empty"><h3>Could not load job feed</h3><p class="muted">Ensure <code>data/jobs_live_cache.json</code> exists and you are using http:// not file://</p></div>';
		}
	}finally{
		jobsLoading = false;
		if(refreshBtn) refreshBtn.disabled = false;
	}
}
const AUDIO_VIDEO_EXT = /\.(mp3|wav|ogg|oga|opus|flac|aac|m4a|wma|aiff?|ape|mid|midi|mp4|m4v|mov|avi|mkv|webm|wmv|flv|mpeg|mpg|3gp|3g2|ogv|ts|m2ts|vob|rm|rmvb|asf|divx)$/i;
function isAudioOrVideoFile(file){
	const type = (file.type || '').toLowerCase();
	if(type.startsWith('audio/') || type.startsWith('video/')) return true;
	return AUDIO_VIDEO_EXT.test(file.name || '');
}
function isRawPdfContent(text){
	const t = (text || '').trim();
	if(!t) return false;
	if(t.startsWith('%PDF-')) return true;
	return t.includes('%PDF-') && /\b\d+\s+\d+\s+obj\b/.test(t) && t.includes('endobj');
}
function isGarbledResumeText(text){
	if(!text || text.length < 30) return false;
	if(isRawPdfContent(text)) return true;
	let bad = 0;
	const sample = Math.min(text.length, 1500);
	for(let i = 0; i < sample; i++){
		const c = text.charCodeAt(i);
		if(c < 32 && c !== 10 && c !== 13 && c !== 9) bad++;
		else if(c > 126 && c < 160) bad++;
	}
	return bad / sample > 0.06;
}
function canUseServerParser(){
	return location.protocol === 'http:' || location.protocol === 'https:';
}
async function extractResumeViaServer(file){
	const body = new FormData();
	body.append('file', file, file.name || 'resume');
	const resp = await fetch('/api/parse-resume', { method: 'POST', body });
	const data = await resp.json().catch(() => ({}));
	if(!resp.ok) throw new Error(data.error || 'Server could not parse this resume.');
	return data.text || '';
}
function latin1ToArrayBuffer(str){
	const bytes = new Uint8Array(str.length);
	for(let i = 0; i < str.length; i++) bytes[i] = str.charCodeAt(i) & 0xff;
	return bytes.buffer;
}
function readFileAsArrayBuffer(file){
	return new Promise((resolve, reject) => {
		const r = new FileReader();
		r.onload = () => resolve(r.result);
		r.onerror = () => reject(new Error('Could not read the file.'));
		r.readAsArrayBuffer(file);
	});
}
function readFileAsText(file){
	return new Promise((resolve, reject) => {
		const r = new FileReader();
		r.onload = () => resolve(r.result);
		r.onerror = () => reject(new Error('Could not read the file.'));
		r.readAsText(file);
	});
}
function normalizeResumeText(text){
	return (text || '')
		.replace(/\r\n/g, '\n')
		.replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g, '')
		.replace(/\n{3,}/g, '\n\n')
		.replace(/[ \t]{2,}/g, ' ')
		.trim();
}
function getResumeFormat(file){
	const name = (file.name || '').toLowerCase();
	const type = (file.type || '').toLowerCase();
	if(type === 'application/pdf' || name.endsWith('.pdf')) return 'pdf';
	if(type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' || name.endsWith('.docx')) return 'docx';
	if(type === 'text/plain' || name.endsWith('.txt') || name.endsWith('.md') || name.endsWith('.markdown')) return 'text';
	if(type.startsWith('text/') || name.endsWith('.html') || name.endsWith('.htm') || name.endsWith('.csv')) return 'text';
	return 'unknown';
}
function pdfItemsToText(items){
	let text = '';
	let lastY = null;
	for(const item of items){
		if(!item.str) continue;
		const y = item.transform ? item.transform[5] : null;
		if(lastY !== null && y !== null && Math.abs(y - lastY) > 2) text += '\n';
		else if(text && !text.endsWith('\n') && !text.endsWith(' ')) text += ' ';
		text += item.str;
		if(item.hasEOL) text += '\n';
		lastY = y;
	}
	return text;
}
async function extractPdfText(arrayBuffer){
	if(typeof pdfjsLib === 'undefined') throw new Error('PDF parser is not loaded. Run bash run.sh and open http://localhost:8080');
	const pdf = await pdfjsLib.getDocument({
		data: arrayBuffer,
		disableWorker: true,
		cMapUrl: PDF_CMAP_URL,
		cMapPacked: true,
		useWorkerFetch: false,
		isEvalSupported: false,
	}).promise;
	const parts = [];
	for(let pageNum = 1; pageNum <= pdf.numPages; pageNum++){
		const page = await pdf.getPage(pageNum);
		const textContent = await page.getTextContent();
		parts.push(pdfItemsToText(textContent.items));
	}
	return parts.join('\n\n');
}
async function extractDocxText(arrayBuffer){
	if(typeof mammoth === 'undefined') throw new Error('DOCX parser is not loaded. Check your internet connection and refresh.');
	const result = await mammoth.extractRawText({ arrayBuffer });
	return result.value || '';
}
async function extractResumeText(file){
	const format = getResumeFormat(file);
	if((format === 'pdf' || format === 'docx') && canUseServerParser()){
		try{
			const serverText = normalizeResumeText(await extractResumeViaServer(file));
			if(serverText && !isGarbledResumeText(serverText)) return serverText;
		}catch(err){ console.warn('Server resume parse:', err.message); }
	}
	if(format === 'pdf') return extractPdfText(await readFileAsArrayBuffer(file));
	if(format === 'docx') return extractDocxText(await readFileAsArrayBuffer(file));
	if(format === 'text') return readFileAsText(file);
	throw new Error('Unsupported resume format. Please upload PDF, DOCX, TXT, or MD. (Legacy .doc files are not supported.)');
}
async function maybeParseResumeTextarea(){
	const textarea = el('resumeText');
	const raw = textarea.value;
	if(!isRawPdfContent(raw)) return false;
	const previous = raw;
	textarea.value = 'Parsing PDF content…';
	try{
		const text = normalizeResumeText(await extractPdfText(latin1ToArrayBuffer(raw)));
		if(!text || isRawPdfContent(text) || isGarbledResumeText(text)) throw new Error('Could not extract readable text from this PDF. Upload the .pdf file (do not paste binary), and use bash run.sh → http://localhost:8080');
		textarea.value = text;
		return true;
	}catch(err){
		textarea.value = previous;
		throw err;
	}
}
async function handleResumeFile(file){
	const textarea = el('resumeText');
	const previous = textarea.value;
	textarea.value = 'Extracting text from resume…';
	try{
		const raw = await extractResumeText(file);
		const text = normalizeResumeText(raw);
		if(!text || isRawPdfContent(text) || isGarbledResumeText(text)) throw new Error('No readable text was found. Run bash run.sh, open http://localhost:8080, and upload the PDF again.');
		textarea.value = text;
		state.extractedSkills = extractSkills(text);
		render();
	}catch(err){
		textarea.value = previous;
		alert(err.message || 'Could not extract resume text.');
	}
}
function onResumeFileChange(e){
	const input = e.target;
	const file = input.files && input.files[0];
	if(!file) return;
	if(isAudioOrVideoFile(file)){
		alert('Please choose a file other than audio or video.');
		input.value = '';
		return;
	}
	handleResumeFile(file);
}
function exportAllJobs(){const filters=buildFilters(); const scorer=state.mlMode?mlScore:baseScore; const rows=sortJobRows(state.jobs.map(job=>({job,...scorer(job,filters)})).filter(row=>passes(row.job,filters,row)),el('sortBy').value).map(r=>({id:r.job.id,title:r.job.title,company:r.job.company,location:r.job.location,mode:r.job.mode,jobType:r.job.jobType,score:r.score,applyUrl:r.job.applyUrl,source:r.job.source,postedDaysAgo:r.job.postedDaysAgo})); const csvContent=convertToCSV(rows); const blob=new Blob([csvContent],{type:'text/csv;charset=utf-8;'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='identified-jobs.csv'; a.click(); URL.revokeObjectURL(a.href);}
function copySearchUrl(){navigator.clipboard.writeText(location.href).then(()=>alert('Current URL copied.'));}
function resetFilters(){el('resumeText').value=''; el('resumeFile').value=''; el('roleKeywords').value=''; el('location').value=''; el('mode').value=''; el('jobType').value=''; el('postedWithin').value='365'; el('remoteOnly').checked=false; el('fresherOnly').checked=false; el('trustedOnly').checked=false; el('mlMode').checked=true; el('sortBy').value='score'; state.extractedSkills=[]; state.showSavedOnly=false; state.mlMode=true; state.agentActive=false; state.agentMatches=[]; state.agentStatus='Agent is idle.'; el('savedToggleBtn').textContent='Show saved only'; const agentStatusEl = el('agentStatus'); if(agentStatusEl) agentStatusEl.textContent = state.agentStatus; render();}
function toggleTheme(){document.documentElement.dataset.theme = document.documentElement.dataset.theme==='dark' ? 'light' : 'dark';}
document.addEventListener('DOMContentLoaded',()=>{
	const protocolWarning = el('protocolWarning');
	if(protocolWarning && location.protocol === 'file:') protocolWarning.hidden = false;

	el('clearProfileBtn').addEventListener('click',()=>{el('resumeText').value=''; el('resumeFile').value=''; state.extractedSkills=[]; render();});
	el('resumeFile').addEventListener('change',onResumeFileChange);
	let resumeInputTimer;
	el('resumeText').addEventListener('input',()=>{
		clearTimeout(resumeInputTimer);
		resumeInputTimer = setTimeout(async ()=>{
			const textarea = el('resumeText');
			const value = textarea.value;
			if(isRawPdfContent(value)){
				try{
					await maybeParseResumeTextarea();
				}catch(err){ 
					alert(err.message || 'Could not parse pasted PDF.'); 
					return;
				}
			}
			const finalValue = textarea.value;
			if(isGarbledResumeText(finalValue)){
				return;
			}
			state.extractedSkills = extractSkills(finalValue);
			render();
		}, 500);
	});
	el('refreshJobsBtn')?.addEventListener('click',()=>loadJobs({ refresh: true }));
	el('applyFiltersBtn').addEventListener('click',()=>{state.agentActive=false; render();});
	el('resetBtn').addEventListener('click',resetFilters);
	el('exportBtn').addEventListener('click',exportAllJobs);
	el('shareBtn').addEventListener('click',copySearchUrl);
	el('themeBtn').addEventListener('click',toggleTheme);
	el('savedToggleBtn').addEventListener('click',()=>{state.showSavedOnly=!state.showSavedOnly; el('savedToggleBtn').textContent=state.showSavedOnly ? 'Show all jobs':'Show saved only'; state.agentActive=false; render();});
	el('agentRunBtn').addEventListener('click',runAgent);
	el('agentOpenBtn').addEventListener('click',openAgentMatches);
	el('agentExportBtn').addEventListener('click',exportAgentMatches);
	el('mlMode').addEventListener('input',()=>{state.mlMode=el('mlMode').checked; render();});
	['roleKeywords','location','mode','jobType','postedWithin','remoteOnly','fresherOnly','trustedOnly','sortBy'].forEach(id=>el(id).addEventListener('input',()=>{state.agentActive=false; render();}));
	const agentStatusEl = el('agentStatus');
	if(agentStatusEl) agentStatusEl.textContent = state.agentStatus;
	loadJobs();
	scheduleJobsAutoRefresh();
});
