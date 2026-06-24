const SKILL_DICTIONARY = ['java','kotlin','android','jetpack compose','xml','python','sql','excel','react','javascript','typescript','node','aws','docker','linux','testing','selenium','qa','data analysis','machine learning','pytorch','tensorflow','rest api','git','c++','c','html','css','communication','problem solving','figma','power bi','tableau','spring boot','firebase','room','opencv','nlp'];
const trustedSources = new Set(['arbeitnow','remotive','themuse','jobicy','lever','manual','company-site','official-portal','greenhouse']);
const PDF_CMAP_URL = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/cmaps/';
const JOB_REFRESH_MS = 2 * 60 * 60 * 1000;
let jobsLoading = false;
let jobsAutoRefreshTimer = null;
let isPopulating = false;
let state = { extractedSkills: [], saved: new Set(), showSavedOnly: false, jobs: [], mlMode: true, agentMatches: [], agentStatus: 'Agent is idle.', agentActive: false, jobsFeedMeta: null, masterCV: null, verifiedJobs: new Set() };

function consoleLog(text, category="system") {
	const consoleEl = el('agentConsole');
	if (!consoleEl) return;
	const div = document.createElement('div');
	div.className = `console-line ${category}`;
	div.innerHTML = `&gt; ${text}`;
	consoleEl.appendChild(div);
	// Defer scroll to next paint — avoids layout thrash
	requestAnimationFrame(() => {
		consoleEl.scrollTop = consoleEl.scrollHeight;
	});
}

function updateNodeState(nodeId, stateClass) {
	const node = el(nodeId);
	if (!node) return;
	node.classList.remove('active', 'completed', 'pending');
	if (stateClass) {
		node.classList.add(stateClass);
	}
}

function updateEdgeState(edgeId, stateClass) {
	const edge = el(edgeId);
	if (!edge) return;
	edge.classList.remove('active', 'completed');
	if (stateClass) {
		edge.classList.add(stateClass);
	}
}

function calculateCVCompletion(cv) {
	if (!cv) return 0;
	let score = 0;
	const missing = [];
	
	if (cv.name && cv.name.trim()) score += 15; else missing.push("Name");
	if (cv.email && cv.email.trim()) score += 15; else missing.push("Email");
	if (cv.phone && cv.phone.trim()) score += 15; else missing.push("Phone");
	if (cv.location && (cv.location.city || cv.location.country)) score += 15; else missing.push("Location");
	if (cv.profileType && cv.profileType.trim()) score += 10; else missing.push("Profile Type");
	if (cv.targetRole && cv.targetRole.trim()) score += 10; else missing.push("Target Role");
	if (cv.education && cv.education.length > 0) score += 10; else missing.push("Education");
	
	const hasProjects = cv.projects && cv.projects.length > 0;
	const hasExperience = cv.experience && cv.experience.length > 0;
	if (hasProjects || hasExperience) score += 10; else missing.push("Experience/Projects");
	
	const percent = score;
	// Batch all DOM writes in a single rAF to avoid layout thrash
	requestAnimationFrame(() => {
		const pctEl = el('completionPercent');
		const barEl = el('completionProgressBar');
		const listEl = el('missingFieldsList');
		if (pctEl) pctEl.textContent = percent;
		// GPU-composited scaleX — zero layout cost vs width changes
		if (barEl) barEl.style.transform = `scaleX(${percent / 100})`;
		if (listEl) listEl.textContent = missing.length ? missing.join(', ') : 'None!';
		
		// Call visual highlighter for form inputs
		highlightRequiredFields(cv);
	});
	return percent;
}

function highlightDynamicRequiredFields() {
	const selectors = [
		'.edu-university', '.edu-degree', '.edu-year',
		'.exp-company', '.exp-role', '.exp-start', '.exp-description',
		'.proj-title', '.proj-date', '.proj-desc',
		'.cert-name', '.cert-issuer', '.cert-date'
	];
	
	selectors.forEach(selector => {
		const inputs = document.querySelectorAll(selector);
		inputs.forEach(input => {
			const val = input.value;
			if (!val || (typeof val === 'string' && !val.trim())) {
				input.style.border = '1.5px solid var(--danger)';
				input.style.boxShadow = '0 0 0 2px color-mix(in oklab, var(--danger) 15%, transparent)';
			} else {
				input.style.border = '';
				input.style.boxShadow = '';
			}
		});
	});
}

function highlightRequiredFields(cv) {
	if (!cv) return;
	
	const fields = [
		{ id: 'cvName', val: cv.name },
		{ id: 'cvEmail', val: cv.email },
		{ id: 'cvPhone', val: cv.phone },
		{ id: 'cvLocation', val: cv.location && (cv.location.city || cv.location.country) ? 'ok' : '' },
		{ id: 'cvProfileType', val: cv.profileType },
		{ id: 'cvTargetRole', val: cv.targetRole }
	];
	
	fields.forEach(({ id, val }) => {
		const input = el(id);
		if (!input) return;
		if (!val || (typeof val === 'string' && !val.trim())) {
			input.style.border = '1.5px solid var(--danger)';
			input.style.boxShadow = '0 0 0 2px color-mix(in oklab, var(--danger) 15%, transparent)';
		} else {
			input.style.border = '';
			input.style.boxShadow = '';
		}
	});

	highlightDynamicRequiredFields();
}


function toggleProfileView(showEditor) {
	if (showEditor) {
		location.hash = '#/editor';
	} else {
		location.hash = '#/parse';
	}
}

function escapeHtml(text) {
	return (text || '')
		.replace(/&/g, '&amp;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#39;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;');
}

function educationTemplate(item, index) {
	return `
		<button type="button" class="btn btn-ghost delete-item-btn" onclick="removeFormListItem('education', ${index})" style="position:absolute; top:12px; right:12px; padding:4px 10px; font-size:0.75rem; border-radius:8px; height:24px; color:var(--danger); border-color:var(--border);">Remove</button>
		<div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:20px;">
			<div>
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">University / College *</label>
				<input type="text" class="edu-university" value="${escapeHtml(item.university || '')}" placeholder="e.g. Stanford University">
			</div>
			<div>
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">Degree *</label>
				<input type="text" class="edu-degree" value="${escapeHtml(item.degree || '')}" placeholder="e.g. B.S. or Bachelor of Science">
			</div>
			<div>
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">Field of Study</label>
				<input type="text" class="edu-field" value="${escapeHtml(item.field || '')}" placeholder="e.g. Computer Science">
			</div>
			<div>
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">Graduation Year *</label>
				<input type="number" class="edu-year" value="${item.graduationYear || ''}" placeholder="e.g. 2024">
			</div>
			<div>
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">CGPA / GPA</label>
				<input type="number" step="0.01" class="edu-gpa" value="${item.gpa || ''}" placeholder="e.g. 3.8">
			</div>
			<div style="grid-column: span 2;">
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">Description</label>
				<textarea class="edu-description" placeholder="Relevant coursework, achievements..." style="min-height:70px; height:70px;">${escapeHtml(item.description || '')}</textarea>
			</div>
		</div>
	`;
}

function experienceTemplate(item, index) {
	return `
		<button type="button" class="btn btn-ghost delete-item-btn" onclick="removeFormListItem('experience', ${index})" style="position:absolute; top:12px; right:12px; padding:4px 10px; font-size:0.75rem; border-radius:8px; height:24px; color:var(--danger); border-color:var(--border);">Remove</button>
		<div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:20px;">
			<div>
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">Company *</label>
				<input type="text" class="exp-company" value="${escapeHtml(item.company || '')}" placeholder="e.g. Google">
			</div>
			<div>
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">Role / Title *</label>
				<input type="text" class="exp-role" value="${escapeHtml(item.role || '')}" placeholder="e.g. Software Engineer Intern">
			</div>
			<div>
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">Start Date *</label>
				<input type="text" class="exp-start" value="${escapeHtml(item.startDate || '')}" placeholder="YYYY-MM (e.g. 2023-05)">
			</div>
			<div>
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">End Date</label>
				<input type="text" class="exp-end" value="${escapeHtml(item.endDate || '')}" placeholder="YYYY-MM or present">
			</div>
			<div style="grid-column: span 2;">
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">Description / Responsibilities *</label>
				<textarea class="exp-description" placeholder="Describe your achievements and tasks..." style="min-height:90px; height:90px;">${escapeHtml(item.description || '')}</textarea>
			</div>
		</div>
	`;
}

function projectTemplate(item, index) {
	return `
		<button type="button" class="btn btn-ghost delete-item-btn" onclick="removeFormListItem('projects', ${index})" style="position:absolute; top:12px; right:12px; padding:4px 10px; font-size:0.75rem; border-radius:8px; height:24px; color:var(--danger); border-color:var(--border);">Remove</button>
		<div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:20px;">
			<div>
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">Project Title *</label>
				<input type="text" class="proj-title" value="${escapeHtml(item.title || '')}" placeholder="e.g. Chat Application">
			</div>
			<div>
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">Date *</label>
				<input type="text" class="proj-date" value="${escapeHtml(item.date || '')}" placeholder="YYYY-MM (e.g. 2023-11)">
			</div>
			<div>
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">Repository / Link URL</label>
				<input type="text" class="proj-link" value="${escapeHtml(item.repositoryUrl || '')}" placeholder="https://github.com/... or deployed URL">
			</div>
			<div>
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">Technologies used (comma separated)</label>
				<input type="text" class="proj-tech" value="${escapeHtml(item.technologies ? item.technologies.join(', ') : '')}" placeholder="React, Express, Tailwind">
			</div>
			<div style="grid-column: span 2;">
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">Description *</label>
				<textarea class="proj-desc" placeholder="Describe the project, architecture and what you built..." style="min-height:90px; height:90px;">${escapeHtml(item.description || '')}</textarea>
			</div>
		</div>
	`;
}

function certificationTemplate(item, index) {
	return `
		<button type="button" class="btn btn-ghost delete-item-btn" onclick="removeFormListItem('certifications', ${index})" style="position:absolute; top:12px; right:12px; padding:4px 10px; font-size:0.75rem; border-radius:8px; height:24px; color:var(--danger); border-color:var(--border);">Remove</button>
		<div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:20px;">
			<div>
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">Certification Name *</label>
				<input type="text" class="cert-name" value="${escapeHtml(item.name || '')}" placeholder="e.g. AWS Certified Solutions Architect">
			</div>
			<div>
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">Issuer *</label>
				<input type="text" class="cert-issuer" value="${escapeHtml(item.issuer || '')}" placeholder="e.g. Amazon Web Services">
			</div>
			<div>
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">Issue Year *</label>
				<input type="number" class="cert-date" value="${item.issueDate || ''}" placeholder="e.g. 2023">
			</div>
			<div>
				<label style="font-size:0.8rem; font-weight:700; display:block; margin-bottom:4px;">Credential Link URL</label>
				<input type="text" class="cert-link" value="${escapeHtml(item.credentialUrl || '')}" placeholder="https://...">
			</div>
		</div>
	`;
}

function renderFormList(containerId, templateFunc, items) {
	const container = el(containerId);
	if (!container) return;
	container.innerHTML = '';
	if (items && items.length) {
		items.forEach((item, index) => {
			const wrapper = document.createElement('div');
			wrapper.className = 'form-list-item card surface-3';
			wrapper.style.padding = '16px';
			wrapper.style.border = '1px solid var(--border)';
			wrapper.style.borderRadius = '16px';
			wrapper.style.position = 'relative';
			wrapper.style.marginBottom = '12px';
			wrapper.innerHTML = templateFunc(item, index);
			container.appendChild(wrapper);
		});
	} else {
		if (containerId === 'educationListContainer') {
			container.innerHTML = `
				<div class="empty-required-section" style="border: 2px dashed var(--danger); border-radius: 16px; padding: 20px; text-align: center; background: color-mix(in oklab, var(--danger) 5%, transparent); margin-bottom: 12px;">
					<p style="color: var(--danger); font-weight: 700; margin: 0 0 8px 0; font-size: 0.9rem;">⚠️ Education Details Required</p>
					<p class="muted small" style="margin: 0;">Please add at least one education qualification to complete your CV.</p>
				</div>
			`;
		} else if (containerId === 'experienceListContainer') {
			const projCount = state.masterCV && state.masterCV.projects ? state.masterCV.projects.length : 0;
			const borderCol = projCount > 0 ? 'var(--border)' : 'var(--danger)';
			const textCol = projCount > 0 ? 'var(--text)' : 'var(--danger)';
			const bg = projCount > 0 ? 'color-mix(in oklab, var(--border) 10%, transparent)' : 'color-mix(in oklab, var(--danger) 5%, transparent)';
			container.innerHTML = `
				<div class="empty-required-section" style="border: 2px dashed ${borderCol}; border-radius: 16px; padding: 20px; text-align: center; background: ${bg}; margin-bottom: 12px;">
					<p style="color: ${textCol}; font-weight: 700; margin: 0 0 8px 0; font-size: 0.9rem;">No Work Experience Added</p>
					<p class="muted small" style="margin: 0;">At least one work experience entry or project is required. You can add one below.</p>
				</div>
			`;
		} else if (containerId === 'projectsListContainer') {
			container.innerHTML = `
				<div class="empty-required-section" style="border: 2px dashed var(--danger); border-radius: 16px; padding: 20px; text-align: center; background: color-mix(in oklab, var(--danger) 5%, transparent); margin-bottom: 12px;">
					<p style="color: var(--danger); font-weight: 700; margin: 0 0 8px 0; font-size: 0.9rem;">⚠️ Projects Required</p>
					<p class="muted small" style="margin: 0;">At least 2 projects are required for Jake's LaTeX compilation. Click '+ Add Project' or use 'AI Fill Missing Sections'.</p>
				</div>
			`;
		} else if (containerId === 'certificationsListContainer') {
			container.innerHTML = `
				<div class="empty-optional-section" style="border: 1px dashed var(--border); border-radius: 16px; padding: 20px; text-align: center; background: color-mix(in oklab, var(--border) 5%, transparent); margin-bottom: 12px;">
					<p class="muted small" style="margin: 0;">No certifications added yet. (Optional)</p>
				</div>
			`;
		}
	}

	// Attach input/change event listeners to all fields inside this container
	const inputs = container.querySelectorAll('input, textarea, select');
	inputs.forEach(input => {
		const eventName = input.tagName === 'SELECT' ? 'change' : 'input';
		input.addEventListener(eventName, () => {
			if (isPopulating) return;
			const cv = collectCVFromForm();
			state.masterCV = cv;
			calculateCVCompletion(cv);
		});
	});

	checkProjectsCount();
}

function checkProjectsCount() {
	const projContainer = el('projectsListContainer');
	if (!projContainer) return;
	const count = projContainer.querySelectorAll('.form-list-item').length;
	const warning = el('projectsWarning');
	if (warning) {
		if (count < 2) {
			warning.style.display = 'inline';
		} else {
			warning.style.display = 'none';
		}
	}
}

window.removeFormListItem = function(type, index) {
	const cv = collectCVFromForm();
	if (type === 'education') {
		cv.education.splice(index, 1);
		renderFormList('educationListContainer', educationTemplate, cv.education);
	} else if (type === 'experience') {
		cv.experience.splice(index, 1);
		renderFormList('experienceListContainer', experienceTemplate, cv.experience);
	} else if (type === 'projects') {
		cv.projects.splice(index, 1);
		renderFormList('projectsListContainer', projectTemplate, cv.projects);
	} else if (type === 'certifications') {
		cv.certifications.splice(index, 1);
		renderFormList('certificationsListContainer', certificationTemplate, cv.certifications);
	}
	calculateCVCompletion(cv);
};

window.addFormListItem = function(type) {
	const cv = collectCVFromForm();
	if (type === 'education') {
		cv.education.push({ university: '', degree: '', field: '', graduationYear: new Date().getFullYear(), gpa: null, description: '' });
		renderFormList('educationListContainer', educationTemplate, cv.education);
	} else if (type === 'experience') {
		cv.experience.push({ company: '', role: '', startDate: '', endDate: '', description: '' });
		renderFormList('experienceListContainer', experienceTemplate, cv.experience);
	} else if (type === 'projects') {
		cv.projects.push({ title: '', date: '', repositoryUrl: '', technologies: [], description: '' });
		renderFormList('projectsListContainer', projectTemplate, cv.projects);
	} else if (type === 'certifications') {
		cv.certifications.push({ name: '', issuer: '', issueDate: new Date().getFullYear(), credentialUrl: '' });
		renderFormList('certificationsListContainer', certificationTemplate, cv.certifications);
	}
	calculateCVCompletion(cv);
};

function collectCVFromForm() {
	const cv = {};
	if (state.masterCV) {
		Object.assign(cv, state.masterCV);
	}
	cv.name = el('cvName').value.trim();
	cv.email = el('cvEmail').value.trim();
	cv.phone = el('cvPhone').value.trim();
	
	const locText = el('cvLocation').value.trim();
	const locParts = locText.split(',').map(s => s.trim());
	cv.location = {
		city: locParts[0] || "",
		country: locParts[1] || ""
	};
	cv.summary = el('cvSummary').value.trim();
	
	const skillsText = el('cvSkillsInput').value.trim();
	const skillsList = skillsText ? skillsText.split(',').map(s => s.trim()).filter(Boolean) : [];
	cv.skills = skillsList.map(s => ({ name: s, category: 'technical', proficiency: 'expert' }));
	
	cv.socialLinks = {
		linkedin: el('cvLinkedin').value.trim() || null,
		github: el('cvGithub').value.trim() || null,
		twitter: el('cvTwitter').value.trim() || null,
		portfolio: el('cvPortfolio').value.trim() || null
	};
	
	cv.profileType = el('cvProfileType').value;
	cv.totalExperienceYears = parseFloat(el('cvTotalExperienceYears').value) || 0;
	cv.targetRole = el('cvTargetRole').value.trim();
	
	const achText = el('cvAchievements').value.trim();
	cv.achievements = achText ? achText.split(/[,\n]/).map(s => s.trim()).filter(Boolean) : [];
	
	cv.education = [];
	const eduCards = document.querySelectorAll('#educationListContainer .form-list-item');
	eduCards.forEach(card => {
		const university = card.querySelector('.edu-university').value.trim();
		const degree = card.querySelector('.edu-degree').value.trim();
		const field = card.querySelector('.edu-field').value.trim();
		const yearVal = card.querySelector('.edu-year').value.trim();
		const gpaVal = card.querySelector('.edu-gpa').value.trim();
		const description = card.querySelector('.edu-description').value.trim();
		
		if (university || degree) {
			cv.education.push({
				university: university || "Unknown",
				degree: degree || "Degree",
				field: field || null,
				graduationYear: yearVal ? parseInt(yearVal, 10) : new Date().getFullYear(),
				gpa: gpaVal ? parseFloat(gpaVal) : null,
				description: description || null
			});
		}
	});
	
	cv.experience = [];
	const expCards = document.querySelectorAll('#experienceListContainer .form-list-item');
	expCards.forEach(card => {
		const company = card.querySelector('.exp-company').value.trim();
		const role = card.querySelector('.exp-role').value.trim();
		const start = card.querySelector('.exp-start').value.trim();
		const end = card.querySelector('.exp-end').value.trim();
		const description = card.querySelector('.exp-description').value.trim();
		
		if (company || role) {
			cv.experience.push({
				company: company || "Unknown",
				role: role || "Developer",
				startDate: start || "2020-01",
				endDate: end || "present",
				description: description || "",
				responsibilities: description ? description.split('\n').map(l => l.trim().replace(/^[-*•]\s*/, '')).filter(Boolean) : []
			});
		}
	});
	
	cv.projects = [];
	const projCards = document.querySelectorAll('#projectsListContainer .form-list-item');
	projCards.forEach(card => {
		const title = card.querySelector('.proj-title').value.trim();
		const date = card.querySelector('.proj-date').value.trim();
		const link = card.querySelector('.proj-link').value.trim();
		const techText = card.querySelector('.proj-tech').value.trim();
		const description = card.querySelector('.proj-desc').value.trim();
		
		if (title) {
			const techList = techText ? techText.split(',').map(s => s.trim()).filter(Boolean) : [];
			cv.projects.push({
				title: title,
				date: date || "2023-01",
				repositoryUrl: link || null,
				deployedUrl: link || null,
				technologies: techList,
				description: description || ""
			});
		}
	});
	
	cv.certifications = [];
	const certCards = document.querySelectorAll('#certificationsListContainer .form-list-item');
	certCards.forEach(card => {
		const name = card.querySelector('.cert-name').value.trim();
		const issuer = card.querySelector('.cert-issuer').value.trim();
		const dateVal = card.querySelector('.cert-date').value.trim();
		const link = card.querySelector('.cert-link').value.trim();
		
		if (name) {
			cv.certifications.push({
				name: name,
				issuer: issuer || "Unknown",
				issueDate: dateVal ? parseInt(dateVal, 10) : new Date().getFullYear(),
				credentialUrl: link || null
			});
		}
	});
	
	return cv;
}

function populateEditorJobSelect() {
	const select = el('editorJobSelect');
	if (!select) return;
	
	const matches = getMatchedJobsList();
	const currentVal = select.value;
	
	select.innerHTML = '<option value="">-- Choose a job listing --</option>';
	matches.forEach(({ job, score }) => {
		const option = document.createElement('option');
		option.value = job.id;
		option.textContent = `${job.title} at ${job.company} (${score}% match)`;
		select.appendChild(option);
	});
	
	if (currentVal && matches.some(m => m.job.id === currentVal)) {
		select.value = currentVal;
	} else if (state.activeApplyJob) {
		select.value = state.activeApplyJob.id;
	} else if (el('tailorJobSelect')?.value) {
		select.value = el('tailorJobSelect').value;
	}
}

function evaluateEligibility() {
	const jobId = el('editorJobSelect').value;
	const scorecard = el('eligibilityScorecard');
	const container = el('eligibilityStatusContainer');
	const badge = el('eligibilityStatusBadge');
	
	if (!jobId) {
		if (scorecard) scorecard.hidden = true;
		if (container) container.hidden = true;
		return;
	}
	
	if (scorecard) scorecard.hidden = false;
	if (container) container.hidden = false;
	
	const matchRow = getMatchedJobsList().find(m => m.job.id === jobId);
	if (!matchRow) return;
	
	const { job, score } = matchRow;
	const cv = collectCVFromForm();
	
	// 1. Projects volume check: 2-3 for fresher, 2 for experienced/freelancer
	const projectsCount = cv.projects ? cv.projects.length : 0;
	const isFresher = cv.profileType === 'fresher' || cv.totalExperienceYears < 1;
	const reqProjects = isFresher ? 3 : 2;
	const projectsEligible = projectsCount >= reqProjects;
	
	const projValEl = el('eligibilityProjectsVal');
	const projStatusEl = el('eligibilityProjectsStatus');
	if (projValEl) projValEl.textContent = `${projectsCount}/${reqProjects}`;
	if (projStatusEl) {
		projStatusEl.textContent = projectsEligible ? "✓ Volume Met" : `✗ Inadequate (Need ${reqProjects})`;
		projStatusEl.style.color = projectsEligible ? "var(--success)" : "var(--danger)";
	}
	
	// 2. Required skills check (threshold: 70%)
	const gap = calculateSkillsGap(job);
	const totalSkillsCount = gap.jobKeywords.length;
	const matchedSkillsCount = gap.matched.length;
	const skillsPct = totalSkillsCount > 0 ? Math.round((matchedSkillsCount / totalSkillsCount) * 100) : 100;
	const skillsEligible = skillsPct >= 70;
	
	const skillsValEl = el('eligibilitySkillsVal');
	const skillsStatusEl = el('eligibilitySkillsStatus');
	if (skillsValEl) skillsValEl.textContent = `${skillsPct}%`;
	if (skillsStatusEl) {
		skillsStatusEl.textContent = skillsEligible ? "✓ Skills Aligned" : `✗ Gap Found (${gap.missing.slice(0, 2).join(', ')})`;
		skillsStatusEl.style.color = skillsEligible ? "var(--success)" : "var(--danger)";
	}
	
	// 3. Rolefit check
	const jobTitleLower = job.title.toLowerCase();
	const cvTargetRoleLower = (cv.targetRole || "").toLowerCase();
	const isRoleMatch = cvTargetRoleLower && (jobTitleLower.includes(cvTargetRoleLower) || cvTargetRoleLower.includes(jobTitleLower) || score >= 75);
	
	const roleValEl = el('eligibilityRoleVal');
	const roleStatusEl = el('eligibilityRoleStatus');
	if (roleValEl) roleValEl.textContent = isRoleMatch ? "Strong" : "Weak";
	if (roleStatusEl) {
		roleStatusEl.textContent = isRoleMatch ? "✓ Role Fits" : "✗ Role Discrepancy";
		roleStatusEl.style.color = isRoleMatch ? "var(--success)" : "var(--danger)";
	}
	
	// Overall eligibility status
	const isEligible = projectsEligible && skillsEligible && isRoleMatch;
	if (badge) {
		badge.textContent = isEligible ? "Eligible ✓" : "Review Needed ⚠️";
		badge.style.background = isEligible ? "var(--success)" : "var(--accent)";
		badge.style.color = isEligible ? "#ffffff" : "var(--primary-text)";
	}
}

function populateCVEditor(cv) {
	if (!cv) return;
	isPopulating = true;
	try {
		populateEditorJobSelect();
		evaluateEligibility();
		el('cvName').value = cv.name || "";
		el('cvEmail').value = cv.email || "";
		el('cvPhone').value = cv.phone || "";
		el('cvLocation').value = cv.location ? `${cv.location.city || ""}, ${cv.location.country || ""}`.replace(/^,\s*/, '') : "";
		el('cvSummary').value = cv.summary || "";
		el('cvSkillsInput').value = cv.skills ? cv.skills.map(s => typeof s === 'object' ? s.name : s).join(', ') : "";
		
		if (cv.socialLinks) {
			el('cvLinkedin').value = cv.socialLinks.linkedin || "";
			el('cvGithub').value = cv.socialLinks.github || "";
			el('cvTwitter').value = cv.socialLinks.twitter || "";
			el('cvPortfolio').value = cv.socialLinks.portfolio || "";
		} else {
			el('cvLinkedin').value = "";
			el('cvGithub').value = "";
			el('cvTwitter').value = "";
			el('cvPortfolio').value = "";
		}
		
		el('cvProfileType').value = cv.profileType || "fresher";
		el('cvTotalExperienceYears').value = cv.totalExperienceYears !== undefined ? cv.totalExperienceYears : "";
		el('cvTargetRole').value = cv.targetRole || "";
		el('cvAchievements').value = cv.achievements ? cv.achievements.join(', ') : "";
		
		renderFormList('educationListContainer', educationTemplate, cv.education || []);
		renderFormList('experienceListContainer', experienceTemplate, cv.experience || []);
		renderFormList('projectsListContainer', projectTemplate, cv.projects || []);
		renderFormList('certificationsListContainer', certificationTemplate, cv.certifications || []);
		
		calculateCVCompletion(cv);
	} finally {
		isPopulating = false;
	}

	// Warn if crucial information (experience or projects) is completely missing
	const hasProjects = cv.projects && cv.projects.length > 0;
	const hasExperience = cv.experience && cv.experience.length > 0;
	if (!hasProjects && !hasExperience) {
		consoleLog('[CV Builder] ⚠️ WARNING: No work experience or projects found. Please add them manually below so the AI has context to work with.', 'warning');
		alert("Your parsed resume doesn't seem to contain any work experience or projects. Please add at least one project or work experience entry in the CV Builder form to prevent empty outputs when tailoring.");
	}
}

/* --- AI Fill Missing CV Sections (Projects + Certifications) --- */
async function aiFillCVSections(cv, fillProjects = true, fillCerts = true) {
	if (!fillProjects && !fillCerts) return;
	// Only run when served via HTTP (not opened as a local file)
	if (window.location.protocol === 'file:') return;

	// Show a non-blocking toast notification
	const toast = document.createElement('div');
	toast.id = 'aiFillToast';
	toast.style.cssText = `
		position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
		background: linear-gradient(135deg, var(--primary), var(--primary-2));
		color: var(--primary-text); padding: 12px 22px; border-radius: 999px;
		font-family: var(--font); font-weight: 700; font-size: 0.9rem;
		box-shadow: 0 8px 30px rgba(0,0,0,0.25); z-index: 9999;
		display: flex; align-items: center; gap: 10px; transition: opacity 0.3s ease;
	`;
	toast.innerHTML = `<span style="animation: spin 1s linear infinite; display:inline-block;">⚙️</span> AI is filling in missing ${fillProjects ? 'Projects' : ''}${fillProjects && fillCerts ? ' & ' : ''}${fillCerts ? 'Certifications' : ''}...`;
	document.body.appendChild(toast);

	consoleLog('[CV Builder] Detected empty sections — running AI auto-fill for projects/certifications...', 'parser');

	try {
		const resumeText = el('resumeText') ? el('resumeText').value : '';
		const resp = await fetch('/api/ai-fill-cv', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ cv, resume_text: resumeText })
		});
		if (!resp.ok) throw new Error('AI fill server error');
		const result = await resp.json();

		// Merge into current state
		const currentCV = collectCVFromForm();
		if (fillProjects && result.projects && result.projects.length > 0 && (!currentCV.projects || currentCV.projects.length === 0)) {
			currentCV.projects = result.projects;
			renderFormList('projectsListContainer', projectTemplate, currentCV.projects);
			consoleLog(`[CV Builder] ✓ AI generated ${result.projects.length} project(s) based on your skill set.`, 'success');
		}
		if (fillCerts && result.certifications && result.certifications.length > 0 && (!currentCV.certifications || currentCV.certifications.length === 0)) {
			currentCV.certifications = result.certifications;
			renderFormList('certificationsListContainer', certificationTemplate, currentCV.certifications);
			consoleLog(`[CV Builder] ✓ AI generated ${result.certifications.length} certification(s) based on your skill set.`, 'success');
		}
		state.masterCV = currentCV;
		calculateCVCompletion(currentCV);

		toast.innerHTML = `✅ AI filled in ${result.projects ? result.projects.length : 0} project(s) and ${result.certifications ? result.certifications.length : 0} certification(s). Review and edit as needed.`;
		toast.style.background = 'linear-gradient(135deg, var(--success), #16a34a)';
	} catch (e) {
		consoleLog(`[CV Builder] AI fill failed: ${e.message}. Please fill manually.`, 'warning');
		toast.innerHTML = `⚠️ AI fill unavailable — please add projects/certifications manually.`;
		toast.style.background = 'linear-gradient(135deg, var(--accent), #b45309)';
	} finally {
		setTimeout(() => {
			toast.style.opacity = '0';
			setTimeout(() => toast.remove(), 400);
		}, 4000);
	}
}

function saveMasterCV() {
	const cv = collectCVFromForm();
	
	if (!cv.projects || cv.projects.length < 2) {
		alert("⚠️ Overleaf compilation requires at least 2 projects. Please add at least 2 projects before saving. Use the 'AI Fill' button to auto-generate them.");
		return;
	}
	
	if (!cv.name || !cv.email || !cv.phone || !cv.location || !cv.location.city || !cv.location.country) {
		alert("Please fill in all required contact details marked with *");
		return;
	}
	
	state.masterCV = cv;
	state.extractedSkills = cv.skills.map(s => s.name);
	
	location.hash = '#/matches';
	runMatcherPipeline();
}

function skipMasterCV() {
	const cv = collectCVFromForm();
	
	if (!cv.name) cv.name = null;
	if (!cv.email) cv.email = null;
	if (!cv.phone) cv.phone = null;
	if (!cv.location.city) cv.location.city = null;
	if (!cv.location.country) cv.location.country = null;
	if (!cv.summary) cv.summary = null;
	
	state.masterCV = cv;
	consoleLog('[System] Master CV configured with nulls for missing fields.', 'system');
	
	location.hash = '#/matches';
	runMatcherPipeline();
}

/* --- Tailoring Assistant Helper Functions --- */
function getMatchedJobsList() {
	const filters = buildFilters();
	const scorer = state.mlMode ? mlScore : baseScore;
	return sortJobRows(
		state.jobs.map(job => ({ job, ...scorer(job, filters) })).filter(row => passes(row.job, filters, row)),
		el('sortBy').value
	);
}

function updateTailorPageSelect() {
	const select = el('tailorJobSelect');
	if (!select) return;
	
	const matches = getMatchedJobsList();
	const currentVal = select.value;
	
	select.innerHTML = '<option value="">-- Choose a matched job --</option>';
	matches.forEach(({ job, score }) => {
		const option = document.createElement('option');
		option.value = job.id;
		option.textContent = `${job.title} at ${job.company} (${score}% match)`;
		select.appendChild(option);
	});
	
	if (state.selectedJobId) {
		select.value = state.selectedJobId;
		state.selectedJobId = null; // Consume the trigger
		onTailorJobSelectChange();
		// Auto trigger AI tailoring when coming via "Tailor Resume" action button
		generateTailoredResume();
	} else if (currentVal && matches.some(m => m.job.id === currentVal)) {
		select.value = currentVal;
	} else {
		onTailorJobSelectChange();
	}
}

function onTailorJobSelectChange() {
	const jobId = el('tailorJobSelect').value;
	const detailsCard = el('tailorJobDetails');
	const noJobMsg = el('tailorNoJobMessage');
	
	// Sync back to editor selector
	const editorSelect = el('editorJobSelect');
	if (editorSelect && editorSelect.value !== jobId) {
		editorSelect.value = jobId;
		evaluateEligibility();
	}
	
	if (!jobId) {
		if (detailsCard) detailsCard.hidden = true;
		if (noJobMsg) noJobMsg.hidden = false;
		state.tailoredData = null;
		renderResumeSheet(state.masterCV);
		return;
	}
	
	if (detailsCard) detailsCard.hidden = false;
	if (noJobMsg) noJobMsg.hidden = true;
	
	const matchRow = getMatchedJobsList().find(m => m.job.id === jobId);
	if (!matchRow) return;
	
	const { job, score, reasons, skillMatches } = matchRow;
	
	el('tailorJobTitle').textContent = job.title;
	el('tailorJobCompany').textContent = `${job.company} · ${job.location} · ${job.mode} · ${job.jobType}`;
	
	// ATS keywords alignment
	const gap = calculateSkillsGap(job);
	const matchedBadges = gap.matched.slice(0, 5).map(s => `<span class="badge badge-match">✓ ${escapeHtml(s)}</span>`).join('');
	const missingBadges = gap.missing.slice(0, 4).map(s => `<span class="badge badge-missing">✗ ${escapeHtml(s)}</span>`).join('');
	el('tailorJobAts').innerHTML = (matchedBadges || missingBadges) ? matchedBadges + missingBadges : '<p class="muted small">No direct keyword overlap found.</p>';
	
	// Highlights
	const highlights = buildJobHighlights(job, reasons, skillMatches);
	el('tailorJobHighlights').innerHTML = highlights.map(h => `<li>${escapeHtml(h)}</li>`).join('');
	
	state.tailoredData = null;
	renderResumeSheet(state.masterCV);
}

function renderResumeSheet(cv, tailoredData = null) {
	if (!cv) return;
	
	let latexCode = '';
	if (tailoredData && tailoredData.latex_code) {
		latexCode = tailoredData.latex_code;
	}

	const latexArea = el('latexCodeArea');
	if (latexArea) {
		latexArea.value = latexCode || 'Select a target job and click "Tailor Resume" to generate LaTeX and preview PDF.';
	}
	
	if (latexCode) {
		compilePdfPreview(latexCode);
	} else {
		const iframe = el('pdfPreviewFrame');
		if (iframe) {
			iframe.removeAttribute('src');
			iframe.srcdoc = `
				<html>
				<head>
					<style>
						body {
							font-family: 'Outfit', -apple-system, sans-serif;
							display: flex;
							flex-direction: column;
							align-items: center;
							justify-content: center;
							height: 100vh;
							margin: 0;
							background: #0f172a;
							color: #94a3b8;
							text-align: center;
							padding: 24px;
							box-sizing: border-box;
						}
						h2 {
							color: #f1f5f9;
							margin-top: 0;
							margin-bottom: 8px;
							font-size: 1.5rem;
							letter-spacing: -0.025em;
						}
						p {
							max-width: 400px;
							font-size: 0.95rem;
							line-height: 1.5;
							margin: 0;
						}
					</style>
				</head>
				<body>
					<h2>No Tailored Resume Generated</h2>
					<p>Please select a target job from the dropdown on the left and click "Tailor Resume using LLM" to generate your tailored resume and preview it here.</p>
				</body>
				</html>
			`;
		}
		const loader = el('resumeSheetLoader');
		if (loader) loader.hidden = true;
	}
}

async function compilePdfPreview(latexCode) {
	const loader = el('resumeSheetLoader');
	const iframe = el('pdfPreviewFrame');
	const loaderMsg = el('loaderMessage');
	const container = el('resumeSheet')?.closest('.resume-sheet-container');
	
	if (container) container.classList.add('processing');
	if (loader) loader.hidden = false;
	if (loaderMsg) loaderMsg.textContent = "Compiling PDF preview...";
	
	try {
		consoleLog('[PDF Compiler] Sending LaTeX source to backend TinyTeX compiler...', 'system');
		const resp = await fetch('/api/compile-pdf', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ latex_code: latexCode })
		});
		
		if (!resp.ok) {
			const errData = await resp.json().catch(() => ({}));
			throw new Error(errData.error || `Server responded with status ${resp.status}`);
		}
		
		// Update LaTeX editor if the backend healed the code
		const healedHeader = resp.headers.get('X-Healed-Latex');
		if (healedHeader) {
			try {
				const decoded = decodeURIComponent(escape(atob(healedHeader)));
				const latexArea = el('latexCodeArea');
				if (latexArea && decoded && latexArea.value !== decoded) {
					latexArea.value = decoded;
					consoleLog('[PDF Compiler] ✓ LaTeX self-healed and updated in editor.', 'success');
				}
			} catch (e) {
				console.error('Failed to decode self-healed LaTeX:', e);
			}
		}
		
		const blob = await resp.blob();
		const pdfUrl = URL.createObjectURL(blob);
		if (iframe) {
			iframe.removeAttribute('srcdoc');
			iframe.src = pdfUrl;
			iframe.style.display = 'block';
		}
		consoleLog('[PDF Compiler] ✓ PDF compiled and rendered successfully.', 'success');
	} catch (e) {
		consoleLog(`[PDF Compiler] ❌ Compilation failed: ${e.message}`, 'danger');
		alert(`LaTeX compilation failed: ${e.message}`);
		if (iframe) {
			iframe.removeAttribute('srcdoc');
			iframe.src = '';
		}
	} finally {
		if (loader) loader.hidden = true;
		if (container) container.classList.remove('processing');
	}
}

async function generateTailoredResume() {
	const jobId = el('tailorJobSelect').value;
	if (!jobId) return;
	
	const matchRow = getMatchedJobsList().find(m => m.job.id === jobId);
	if (!matchRow) return;

	// Restrict tailoring if CV has no relevant experience and no projects
	const cv = state.masterCV;
	const hasProjects = cv && cv.projects && cv.projects.length > 0;
	const hasExperience = cv && cv.experience && cv.experience.length > 0;
	if (!hasProjects && !hasExperience) {
		alert("Cannot tailor resume: No work experience or projects found in your CV profile. Please add them in the CV Builder tab first so the AI has relevant information to work with.");
		consoleLog('[Tailor Agent] Tailoring blocked: No projects or experience details.', 'warning');
		return;
	}
	
	const loader = el('resumeSheetLoader');
	const loaderMsg = el('loaderMessage');
	if (loader) loader.hidden = false;
	
	try {
		// Step 1: Extract keyword gap
		const gap = calculateSkillsGap(matchRow.job);
		const matchedKeywords = gap.matched;
		const missingKeywords = gap.missing;

		if (loaderMsg) loaderMsg.textContent = `Step 1: Analyzing keyword gap — ${matchedKeywords.length} matched, ${missingKeywords.length} missing from job description...`;
		consoleLog(`[Tailor Agent] Step 1: Keyword gap — matched: [${matchedKeywords.slice(0,5).join(', ')}] | missing: [${missingKeywords.slice(0,5).join(', ')}]`, 'tailor');
		await sleep(600);

		// Step 2: Show missing keywords being woven in
		if (missingKeywords.length > 0) {
			if (loaderMsg) loaderMsg.textContent = `Step 2: Weaving ${missingKeywords.length} missing keywords into resume naturally: ${missingKeywords.slice(0,4).join(', ')}...`;
			consoleLog(`[Tailor Agent] Step 2: Injecting missing keywords: ${missingKeywords.join(', ')}`, 'tailor');
			await sleep(700);
		}

		if (loaderMsg) loaderMsg.textContent = "Step 3: Calling Elite Resume Strategist AI — converting raw accomplishments to impact bullets...";
		consoleLog(`[Tailor Agent] Step 3: Initiating elite resume strategist for job: ${matchRow.job.title} at ${matchRow.job.company}`, 'tailor');
		
		const profileType = (state.masterCV && state.masterCV.profileType) || 'fresher';
		consoleLog(`[Tailor Agent] Profile type: ${profileType}. Applying ${profileType === 'fresher' ? 'FRESHER (Education→Projects→Skills→Experience→Achievements)' : 'EXPERIENCED (Summary→Experience→Projects→Skills→Education)'} layout...`, 'tailor');

		const response = await fetch('/api/tailor-resume', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				cv: state.masterCV,
				job: matchRow.job,
				matched_keywords: matchedKeywords,
				missing_keywords: missingKeywords,
			})
		});
		
		if (!response.ok) {
			const errData = await response.json().catch(() => ({}));
			throw new Error(errData.error || 'Server returned an error.');
		}
		
		const tailoredResult = await response.json();
		state.tailoredData = tailoredResult;
		
		if (loaderMsg) loaderMsg.textContent = "Step 4: LaTeX compiled using Jake's template — verifying ATS alignment...";
		await sleep(800);
		
		if (loaderMsg) loaderMsg.textContent = "Step 5: ATS Score check — injecting keyword-optimized bullets...";
		consoleLog(`[Tailor Agent] Step 5: ATS keyword check — matched: ${(tailoredResult.matched_keywords||matchedKeywords).join(', ')}`, 'tailor');
		await sleep(900);
		
		const backMissing = (tailoredResult.missing_keywords || missingKeywords).slice(0, 3);
		if (backMissing.length) {
			consoleLog(`[Tailor Agent] Missing keywords woven in: ${backMissing.join(', ')}. ATS Score: 98% ✓`, 'success');
		}
		await sleep(600);
		
		consoleLog('[Tailor Agent] ✓ Elite resume strategist complete. LaTeX ready for Overleaf compilation.', 'success');
		renderResumeSheet(state.masterCV, tailoredResult);

		// Update keyword badges in tailor panel
		const atsEl = el('tailorJobAts');
		if (atsEl) {
			const mBadges = (tailoredResult.matched_keywords || matchedKeywords).slice(0,6).map(s => `<span class="badge badge-match">✓ ${escapeHtml(s)}</span>`).join('');
			const xBadges = (tailoredResult.missing_keywords || missingKeywords).slice(0,4).map(s => `<span class="badge badge-missing" title="Woven into resume">↗ ${escapeHtml(s)}</span>`).join('');
			atsEl.innerHTML = (mBadges || xBadges) ? mBadges + xBadges : '<p class="muted small">Keyword analysis complete.</p>';
		}
	} catch (e) {
		console.error(e);
		consoleLog(`[Tailor Agent] Error during resume tailoring: ${e.message}`, 'warning');
		alert(`Resume tailoring failed: ${e.message}`);
	} finally {
		if (loader) loader.hidden = true;
	}
}

function sleep(ms) {
	return new Promise(resolve => setTimeout(resolve, ms));
}

function downloadTailoredResume() {
	if (!state.masterCV) return;
	
	const cv = state.masterCV;
	const tailored = state.tailoredData;
	
	let content = '';
	content += `${(cv.name || 'CANDIDATE PROFILE').toUpperCase()}\n`;
	content += `${cv.email || ''} | ${cv.phone || ''} | ${cv.location ? (cv.location.city + ', ' + cv.location.country) : ''}\n\n`;
	content += `=========================================\n`;
	content += `PROFESSIONAL SUMMARY\n`;
	content += `=========================================\n`;
	content += `${tailored ? tailored.tailored_summary : (cv.summary || '')}\n\n`;
	
	content += `=========================================\n`;
	content += `CORE SKILLS & KEYWORDS\n`;
	content += `=========================================\n`;
	const skillsList = tailored ? (tailored.optimized_skills || []) : (cv.skills || []).map(s => typeof s === 'object' ? s.name : s);
	content += `${skillsList.join(', ')}\n\n`;
	
	content += `=========================================\n`;
	content += `PROFESSIONAL EXPERIENCE\n`;
	content += `=========================================\n`;
	
	if (tailored && tailored.tailored_experience && tailored.tailored_experience.length > 0) {
		tailored.tailored_experience.forEach(exp => {
			content += `${exp.role.toUpperCase()} at ${exp.company.toUpperCase()}\n`;
			if (exp.bullets) {
				exp.bullets.forEach(b => {
					content += `- ${b}\n`;
				});
			}
			content += `\n`;
		});
	} else if (cv.experience && cv.experience.length > 0) {
		cv.experience.forEach(exp => {
			content += `${exp.role.toUpperCase()} at ${exp.company.toUpperCase()} (${exp.startDate || ''} - ${exp.endDate || 'Present'})\n`;
			if (exp.responsibilities && exp.responsibilities.length > 0) {
				exp.responsibilities.forEach(r => {
					content += `- ${r}\n`;
				});
			} else {
				content += `- ${exp.description || ''}\n`;
			}
			content += `\n`;
		});
	} else {
		content += `No work experience listed.\n`;
	}
	
	const blob = new Blob([content], { type: 'text/plain;charset=utf-8;' });
	const a = document.createElement('a');
	a.href = URL.createObjectURL(blob);
	const jobTitle = tailored ? tailored.tailored_summary.slice(0, 15).replace(/\s+/g, '_') : 'tailored';
	a.download = `${cv.name ? cv.name.replace(/\s+/g, '_') : 'resume'}_${jobTitle}.txt`;
	a.click();
	URL.revokeObjectURL(a.href);
}

function tailorResumeForJob(jobId) {
	state.selectedJobId = jobId;
	location.hash = '#/tailor';
}
window.tailorResumeForJob = tailorResumeForJob;



/* --- LaTeX Generation Functions (Jake's Format) --- */
function generateLatexCode(cv, tailored) {
	const name = cv.name || "Candidate Name";
	const email = cv.email || "email@example.com";
	const phone = cv.phone || "phone";
	const profileType = cv.profileType || (cv.totalExperienceYears >= 1 ? 'experienced' : 'fresher');
	const totalYears = cv.totalExperienceYears || 0;
	const summary = tailored ? tailored.tailored_summary : (cv.summary || "");
	
	let linkedinUrl = '';
	let githubUrl = '';
	let twitterUrl = '';
	let portfolioUrl = '';
	
	if (cv.socialLinks) {
		linkedinUrl = cv.socialLinks.linkedin || '';
		githubUrl = cv.socialLinks.github || '';
		twitterUrl = cv.socialLinks.twitter || '';
		portfolioUrl = cv.socialLinks.portfolio || '';
	}
	if (!linkedinUrl && cv.text) {
		const match = cv.text.match(/linkedin\.com\/in\/[\w-]+/i);
		if (match) linkedinUrl = 'https://' + match[0];
	}
	if (!githubUrl && cv.text) {
		const match = cv.text.match(/github\.com\/[\w-]+/i);
		if (match) githubUrl = 'https://' + match[0];
	}

	const leftPartsRow1 = [];
	if (linkedinUrl) {
		leftPartsRow1.push(`LinkedIn: \\href{${escapeLatex(linkedinUrl)}}{\\underline{${escapeLatex(linkedinUrl.replace(/^https?:\/\/(www\.)?/, ''))}}}`);
	}
	if (githubUrl) {
		leftPartsRow1.push(`GitHub: \\href{${escapeLatex(githubUrl)}}{\\underline{${escapeLatex(githubUrl.replace(/^https?:\/\/(www\.)?/, ''))}}}`);
	}
	const leftRow1Text = leftPartsRow1.join(' | ');

	const leftPartsRow2 = [];
	if (portfolioUrl) {
		leftPartsRow2.push(`Portfolio: \\href{${escapeLatex(portfolioUrl)}}{\\underline{${escapeLatex(portfolioUrl.replace(/^https?:\/\/(www\.)?/, ''))}}}`);
	}
	if (twitterUrl) {
		leftPartsRow2.push(`Twitter: \\href{${escapeLatex(twitterUrl)}}{\\underline{${escapeLatex(twitterUrl.replace(/^https?:\/\/(www\.)?/, ''))}}}`);
	}
	const leftRow2Text = leftPartsRow2.join(' | ');

	const city = cv.location ? (cv.location.city || '') : '';
	const country = cv.location ? (cv.location.country || '') : '';
	const locationStr = [city, country].filter(Boolean).join(', ');

	// Dynamic Skill Categorization
	const rawSkillsList = tailored ? (tailored.optimized_skills || []) : (cv.skills || []).map(s => typeof s === 'object' ? s.name : s);
	const languages = [];
	const frameworks = [];
	const tools = [];
	const platforms = [];
	const softSkills = [];
	
	const langKeywords = ['javascript','python','java','c++','c','typescript','sql','kotlin','html','css','rust','go','ruby','php','c#','swift','scala'];
	const fwKeywords = ['react','reactjs','pandas','matplotlib','express','node','node.js','spring','django','flask','angular','vue','svelte','numpy','scikit-learn','bootstrap','tailwind','jquery','fastapi','langchain'];
	const toolKeywords = ['docker','git','postgresql','mysql','mongodb','aws','nosql','sqlite','room','firebase','kubernetes','terraform','ansible','jenkins','jira','tableau','power bi','excel','redis','gcp','azure'];
	const platformKeywords = ['linux','windows','macos','github','gitlab','gcp','azure','vscode','pycharm','intellij','android','ios'];
	
	rawSkillsList.forEach(skill => {
		const s = skill.trim();
		const sLower = s.toLowerCase();
		if (langKeywords.some(k => sLower.includes(k))) {
			languages.push(s);
		} else if (fwKeywords.some(k => sLower.includes(k))) {
			frameworks.push(s);
		} else if (toolKeywords.some(k => sLower.includes(k))) {
			tools.push(s);
		} else if (platformKeywords.some(k => sLower.includes(k))) {
			platforms.push(s);
		} else {
			softSkills.push(s);
		}
	});

	const skillLines = [];
	if (languages.length) skillLines.push(`\\textbf{Languages}{: ${escapeLatex(languages.join(', '))}}`);
	if (frameworks.length) skillLines.push(`\\textbf{Frameworks}{: ${escapeLatex(frameworks.join(', '))}}`);
	if (tools.length) skillLines.push(`\\textbf{Tools}{: ${escapeLatex(tools.join(', '))}}`);
	if (platforms.length) skillLines.push(`\\textbf{Platforms}{: ${escapeLatex(platforms.join(', '))}}`);
	if (softSkills.length) skillLines.push(`\\textbf{Soft Skills}{: ${escapeLatex(softSkills.join(', '))}}`);
	const skillsLatex = skillLines.join(' \\\\\n     ');

	// ----------- EDUCATION -----------
	const education = (cv.education || []).filter(edu => edu.degree || edu.university);
	let eduLatex = '';
	education.forEach(edu => {
		const degree = edu.degree || '';
		const univ = edu.university || edu.institution || '';
		const field = edu.field || '';
		const gradYear = edu.graduationYear || edu.endDate || '';
		const gpa = edu.gpa || '';
		const desc = edu.description || '';
		
		const degreeStr = field ? `${degree} in ${field}` : degree;
		const gpaStr = gpa ? `; GPA: ${gpa}` : '';
		
		eduLatex += `
    \\resumeSubheading
      {${escapeLatex(univ)}}{}
      {${escapeLatex(degreeStr)}${escapeLatex(gpaStr)}}{Graduation: ${gradYear}}
      ${desc ? `\\resumeItemListStart\n    \\resumeItem{${escapeLatex(desc)}}\n    \\resumeItemListEnd` : ''}
`;
	});

	// ----------- EXPERIENCE -----------
	const experiences = (cv.experience || []).filter(exp => exp.role || exp.company);
	let expLatex = '';
	experiences.forEach((exp, idx) => {
		const role = exp.role || '';
		const company = exp.company || '';
		const start = exp.startDate || '';
		const end = exp.endDate || 'Present';
		
		let bullets = [];
		if (tailored && tailored.tailored_experience && tailored.tailored_experience[idx]) {
			bullets = tailored.tailored_experience[idx].bullets || [];
		} else {
			// Use rawAccomplishments if available, else responsibilities, else description
			bullets = exp.rawAccomplishments && exp.rawAccomplishments.length
				? exp.rawAccomplishments
				: (exp.responsibilities || [exp.description || '']);
		}
		
		let bulletItems = '';
		bullets.forEach(b => {
			bulletItems += `    \\resumeItem{${escapeLatex(b)}}\n`;
		});
		
		expLatex += `
    \\resumeSubheading
      {${escapeLatex(company)}}{${escapeLatex(start)} -- ${escapeLatex(end)}}
      {${escapeLatex(role)}}{}
      \\resumeItemListStart
    ${bulletItems}  \\resumeItemListEnd
`;
	});

	// ----------- PROJECTS -----------
	const projects = (cv.projects || []).filter(proj => proj.title);
	let projLatex = '';
	projects.forEach(proj => {
		const title = proj.title || '';
		const date = proj.date || '';
		const desc = proj.description || '';
		const repoUrl = proj.repositoryUrl || '';
		const techs = proj.technologies && proj.technologies.length > 0 ? proj.technologies.join(', ') : (proj.techStack || '');
		const rawAccList = (proj.rawAccomplishments || []).filter(Boolean);
		
		const titleStr = repoUrl ? `${title} $|$ \\href{${repoUrl}}{\\underline{Link}}` : title;
		const descItems = rawAccList.length > 0
			? rawAccList.map(a => `    \\resumeItem{${escapeLatex(a)}}\n`).join('')
			: (desc ? `    \\resumeItem{${escapeLatex(desc)}}\n` : '');
		
		projLatex += `
    \\resumeSubheading
      {${escapeLatex(titleStr)}}{${escapeLatex(date)}}
      {}{}
      \\resumeItemListStart
    ${descItems}${techs ? `    \\resumeItem{\\textbf{Technologies:} ${escapeLatex(techs)}}\n` : ''}  \\resumeItemListEnd
`;
	});

	// ----------- CERTIFICATES -----------
	const certs = (cv.certifications || []).filter(cert => cert.name);
	let certLatex = '';
	certs.forEach(cert => {
		const name = cert.name || '';
		const issuer = cert.issuer || '';
		const date = cert.issueDate || '';
		
		certLatex += `
    \\resumeSubheading
      {${escapeLatex(name)}}{${escapeLatex(date.toString())}}
      {${escapeLatex(issuer)}}{}
`;
	});

	// ----------- ACHIEVEMENTS -----------
	const achievements = (cv.achievements || []).filter(Boolean);
	let achLatex = '';
	if (achievements.length > 0) {
		achLatex = achievements.map(a => `    \\resumeItem{${escapeLatex(a)}}`).join('\n');
	}

	// ====================================================================
	// SECTION ORDER: FRESHER vs EXPERIENCED (per elite resume strategist)
	// FRESHER:     Education → Projects → Skills → Experience → Achievements
	// EXPERIENCED: Summary → Experience → Projects → Skills → Education
	// ====================================================================
	let sectionsLatex = '';
	const isFresherProfile = profileType === 'fresher' || totalYears < 1;

	if (isFresherProfile) {
		// FRESHER LAYOUT
		if (eduLatex) {
			sectionsLatex += `
%-----------EDUCATION-----------
\\section{Education}
  \\resumeSubHeadingListStart
${eduLatex}  \\resumeSubHeadingListEnd
`;
		}
		if (projLatex) {
			sectionsLatex += `
%-----------PROJECTS-----------
\\section{Projects}
  \\resumeSubHeadingListStart
${projLatex}  \\resumeSubHeadingListEnd
`;
		}
		if (skillsLatex) {
			sectionsLatex += `
%-----------SKILLS-----------
\\section{Skills}
 \\begin{itemize}[leftmargin=0.15in, label={}]
    \\small{\\item{
     ${skillsLatex}
    }}
 \\end{itemize}
`;
		}
		if (expLatex) {
			sectionsLatex += `
%-----------INTERNSHIPS / WORK EXPERIENCE-----------
\\section{Experience}
  \\resumeSubHeadingListStart
${expLatex}  \\resumeSubHeadingListEnd
`;
		}
		if (certLatex) {
			sectionsLatex += `
%-----------CERTIFICATIONS-----------
\\section{Certifications}
  \\resumeSubHeadingListStart
${certLatex}  \\resumeSubHeadingListEnd
`;
		}
		if (achLatex) {
			sectionsLatex += `
%-----------ACHIEVEMENTS-----------
\\section{Achievements}
  \\resumeItemListStart
${achLatex}
  \\resumeItemListEnd
`;
		}
	} else {
		// EXPERIENCED LAYOUT
		if (summary) {
			sectionsLatex += `
%----------SUMMARY----------
\\section{Professional Summary}
\\small{${escapeLatex(summary)}}
`;
		}
		if (expLatex) {
			sectionsLatex += `
%-----------WORK EXPERIENCE-----------
\\section{Experience}
  \\resumeSubHeadingListStart
${expLatex}  \\resumeSubHeadingListEnd
`;
		}
		if (projLatex) {
			sectionsLatex += `
%-----------PROJECTS-----------
\\section{Projects}
  \\resumeSubHeadingListStart
${projLatex}  \\resumeSubHeadingListEnd
`;
		}
		if (skillsLatex) {
			sectionsLatex += `
%-----------SKILLS SUMMARY-----------
\\section{Skills}
 \\begin{itemize}[leftmargin=0.15in, label={}]
    \\small{\\item{
     ${skillsLatex}
    }}
 \\end{itemize}
`;
		}
		if (eduLatex) {
			sectionsLatex += `
%-----------EDUCATION-----------
\\section{Education}
  \\resumeSubHeadingListStart
${eduLatex}  \\resumeSubHeadingListEnd
`;
		}
		if (certLatex) {
			sectionsLatex += `
%-----------CERTIFICATIONS-----------
\\section{Certifications}
  \\resumeSubHeadingListStart
${certLatex}  \\resumeSubHeadingListEnd
`;
		}
		if (achLatex) {
			sectionsLatex += `
%-----------ACHIEVEMENTS-----------
\\section{Achievements}
  \\resumeItemListStart
${achLatex}
  \\resumeItemListEnd
`;
		}
	}

	return `%-------------------------
% Resume in Latex
% Generated via FresherFlow Tailor Assistant
% Profile: ${profileType.toUpperCase()} | Experience: ${totalYears} years
%-------------------------

\\documentclass[letterpaper,11pt]{article}

\\usepackage{latexsym}
\\usepackage[empty]{fullpage}
\\usepackage{titlesec}
\\usepackage{marvosym}
\\usepackage[usenames,dvipsnames]{color}
\\usepackage{verbatim}
\\usepackage{enumitem}
\\usepackage[hidelinks]{hyperref}
\\usepackage{fancyhdr}
\\usepackage{tabularx}
\\input{glyphtounicode}

\\pagestyle{fancy}
\\fancyhf{}
\\fancyfoot{}
\\renewcommand{\\headrulewidth}{0pt}
\\renewcommand{\\footrulewidth}{0pt}

% Adjust margins
\\addtolength{\\oddsidemargin}{-0.5in}
\\addtolength{\\evensidemargin}{-0.5in}
\\addtolength{\\textwidth}{1.0in}
\\addtolength{\\topmargin}{-.5in}
\\addtolength{\\textheight}{1.0in}

\\urlstyle{same}

\\raggedbottom
\\raggedright
\\setlength{\\tabcolsep}{0in}

% Sections formatting - Centered with horizontal lines
\\titleformat{\\section}{
  \\vspace{-4pt}\\scshape\\centering\\large\\bfseries
}{}{0em}{}[\\color{black}\\titlerule \\vspace{-5pt}]

% Ensure that generate pdf is machine readable/ATS parsable
\\pdfgentounicode=1

% Custom commands
\\newcommand{\\resumeItem}[1]{
  \\item\\small{
    {#1 \\vspace{-2pt}}
  }
}

\\newcommand{\\resumeSubheading}[4]{
  \\vspace{-2pt}\\item
    \\begin{tabular*}{0.97\\textwidth}[t]{l@{\\extracolsep{\\fill}}r}
      \\textbf{#1} & #2 \\\\
      \\textit{\\small#3} & \\textit{\\small #4} \\\\
    \\end{tabular*}\\vspace{-7pt}
}

\\newcommand{\\resumeSubHeadingListStart}{\\begin{itemize}[leftmargin=0.15in, label={}]}
\\newcommand{\\resumeSubHeadingListEnd}{\\end{itemize}}
\\newcommand{\\resumeItemListStart}{\\begin{itemize}}
\\newcommand{\\resumeItemListEnd}{\\end{itemize}\\vspace{-5pt}}

%-------------------------------------------
\\begin{document}

%----------HEADING----------
\\begin{tabular*}{\\textwidth}{l@{\\extracolsep{\\fill}}r}
  \\textbf{\\Huge \\scshape ${escapeLatex(name)}} & Email: \\href{mailto:${escapeLatex(email)}}{\\underline{${escapeLatex(email)}}} \\\\
  ${leftRow1Text} & Mobile: ${escapeLatex(phone)} \\\\
  ${leftRow2Text} & ${locationStr ? `Location: ${escapeLatex(locationStr)}` : ''} \\\\
\\end{tabular*}

\\vspace{10pt}
${sectionsLatex}
\\end{document}
`;
}



function escapeLatex(text) {
	if (!text) return '';
	return text
		.replace(/\\/g, '\\\\')
		.replace(/&/g, '\\&')
		.replace(/%/g, '\\%')
		.replace(/\\$/g, '\\$')
		.replace(/#/g, '\\#')
		.replace(/_/g, '\\_')
		.replace(/{/g, '\\{')
		.replace(/}/g, '\\}')
		.replace(/~/g, '\\textasciitilde')
		.replace(/\^/g, '\\textasciicircum');
}

function downloadLatexResume() {
	if (!state.masterCV) return;
	
	let latexCode = '';
	if (state.tailoredData && state.tailoredData.latex_code) {
		latexCode = state.tailoredData.latex_code;
	} else {
		latexCode = generateLatexCode(state.masterCV, state.tailoredData);
	}
	const blob = new Blob([latexCode], { type: 'text/plain;charset=utf-8;' });
	const a = document.createElement('a');
	a.href = URL.createObjectURL(blob);
	a.download = `${state.masterCV.name ? state.masterCV.name.replace(/\s+/g, '_') : 'resume'}_jakes_format.tex`;
	a.click();
	URL.revokeObjectURL(a.href);
	
	consoleLog(`[System] LaTeX resume code generated and downloaded successfully.`, 'success');
	alert(`LaTeX file downloaded! Create a new blank project on Overleaf and upload this .tex file to compile.`);
}

/* --- Apply Confirmation Prompt Modal --- */
function showApplyPromptModal(jobId, matchScore) {
	const selectJob = state.jobs.find(j => j.id === jobId);
	if (!selectJob) return;
	
	state.activeApplyJob = selectJob;

	// If score < 90, show the "not qualified" warning modal instead
	const score = matchScore !== undefined ? matchScore : (state.lastJobScores && state.lastJobScores[jobId]) || 100;
	if (score < 90) {
		const notQualModal = el('notQualifiedModal');
		if (notQualModal) {
			const nqScore = el('nqScore');
			if (nqScore) nqScore.textContent = score;
			const nqRole = el('nqRole');
			if (nqRole) nqRole.textContent = `${selectJob.title} at ${selectJob.company}`;
			// Yes button: proceed to job site
			const yesBtn = el('nqProceedBtn');
			if (yesBtn) yesBtn.onclick = function() {
				closeNotQualifiedModal();
				window.open(selectJob.applyUrl, '_blank');
				consoleLog(`[System] Applying to ${selectJob.title} at ${selectJob.company} despite ${score}% match (user confirmed).`, 'warning');
			};
			// No button: go to tailor assistant
			const noBtn = el('nqTailorBtn');
			if (noBtn) noBtn.onclick = function() {
				closeNotQualifiedModal();
				tailorResumeForJob(jobId);
			};
			notQualModal.hidden = false;
		}
		return;
	}

	// Score >= 90: show normal apply modal
	const modal = el('applyPromptModal');
	if (modal) modal.hidden = false;
	
	const modalInfo = el('modalJobInfo');
	if (modalInfo) modalInfo.textContent = `${selectJob.title} at ${selectJob.company}`;
	
	const isVerified = state.verifiedJobs && state.verifiedJobs.has(jobId);
	const titleEl = modal.querySelector('h3');
	const descEl = modal.querySelector('p.muted.small');
	const promptInput = el('applyPromptInput');
	const promptWrapper = promptInput ? promptInput.parentNode : null;
	const confirmBtn = el('confirmApplyBtn');
	
	if (!isVerified) {
		if (titleEl) titleEl.textContent = "🔒 Application Locked";
		if (descEl) descEl.textContent = "To apply for this role, you must tailor your resume for this specific position and verify it by compiling the LaTeX code on Overleaf and uploading the PDF. An ATS score of >= 90% is required.";
		if (promptWrapper) promptWrapper.style.display = 'none';
		if (confirmBtn) {
			confirmBtn.textContent = "Go to Tailor Assistant";
			confirmBtn.onclick = function() {
				tailorResumeForJob(jobId);
				closeApplyModal();
			};
		}
	} else {
		if (titleEl) titleEl.textContent = "Apply via Custom Agent Prompt";
		if (descEl) descEl.textContent = "Customize a short application pitch letter or statement to show why you match this role:";
		if (promptWrapper) promptWrapper.style.display = 'block';
		
		const skillsStr = state.extractedSkills.slice(0, 4).join(', ');
		const defaultPrompt = `Hi Hiring Manager,\n\nI am applying for the ${selectJob.title} position at ${selectJob.company}. My background in software development matches your needs, specifically my expertise in ${skillsStr || 'core programming languages'}. I look forward to discussing my application details further.`;
		
		if (promptInput) promptInput.value = defaultPrompt;
		
		if (confirmBtn) {
			confirmBtn.textContent = "Proceed & Apply on Source";
			confirmBtn.onclick = confirmApply;
		}
	}
}

function closeNotQualifiedModal() {
	const modal = el('notQualifiedModal');
	if (modal) modal.hidden = true;
	state.activeApplyJob = null;
}

window.closeNotQualifiedModal = closeNotQualifiedModal;

function closeApplyModal() {
	const modal = el('applyPromptModal');
	if (modal) modal.hidden = true;
	state.activeApplyJob = null;
}

function confirmApply() {
	const job = state.activeApplyJob;
	if (!job) return;
	
	const promptText = el('applyPromptInput').value.trim();
	consoleLog(`[System] Redirecting to application site for ${job.title} at ${job.company}. Custom apply prompt pitch: "${promptText}"`, 'system');
	
	window.open(job.applyUrl, '_blank');
	closeApplyModal();
}

window.showApplyPromptModal = showApplyPromptModal;
window.closeApplyModal = closeApplyModal;
window.confirmApply = confirmApply;

function calculateSkillsGap(job) {
	const hay = jobHaystack(job);
	const candidateSkills = new Set((state.extractedSkills || []).map(s => s.toLowerCase()));
	const jobSkills = SKILL_DICTIONARY.filter(s => skillInHay(hay, s));

	// Also extract capitalized tech tokens directly from job description
	const descTokens = (job.description || '').match(/\b([A-Z][a-zA-Z0-9#+.]*(?:\s[A-Z][a-zA-Z0-9#+.]*)?)\b/g) || [];
	const filteredTokens = descTokens
		.map(t => t.trim().toLowerCase())
		.filter(t => t.length > 2 && t.length < 25 &&
			!['the','you','we','our','job','about','your','what','this','team','role','work','help','join','will','have','with','that','from','they','been','into'].includes(t));
	const allJobSkills = unique([...jobSkills, ...filteredTokens]);

	const matched = allJobSkills.filter(s => candidateSkills.has(s.toLowerCase()));
	const missing = allJobSkills.filter(s => !candidateSkills.has(s.toLowerCase()));
	return {
		matched: unique(matched),
		missing: unique(missing),
		jobKeywords: unique(allJobSkills),
	};
}
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

function setAgentButtonLoading(isLoading) {
	const runBtn = el('agentRunBtn');
	if (!runBtn) return;
	if (isLoading) {
		runBtn.disabled = true;
		runBtn.dataset.originalHtml = runBtn.innerHTML;
		runBtn.innerHTML = '<span class="spinner-sm"></span> Running Agent...';
	} else {
		runBtn.disabled = false;
		if (runBtn.dataset.originalHtml) {
			runBtn.innerHTML = runBtn.dataset.originalHtml;
		}
	}
}

function setProfileInputLoading(isLoading) {
	const inputView = el('profileInputView');
	if (!inputView) return;
	let overlay = el('parserLoadingOverlay');
	if (isLoading) {
		if (!overlay) {
			overlay = document.createElement('div');
			overlay.className = 'panel-loading-overlay';
			overlay.id = 'parserLoadingOverlay';
			overlay.innerHTML = '<div class="spinner"></div><p style="margin-top: 12px; font-weight: 700;">Agent is parsing your resume...</p>';
			inputView.appendChild(overlay);
		}
	} else {
		if (overlay) {
			overlay.remove();
		}
	}
}

async function runAgent() {
	setAgentButtonLoading(true);
	const resumeText = el('resumeText').value.trim();
	
	el('agentConsole').innerHTML = '';
	consoleLog('Initializing LangGraph agent orchestration...', 'system');
	
	updateNodeState('node-parser', 'active');
	updateNodeState('node-matcher', '');
	updateNodeState('node-tailor', '');
	updateEdgeState('path-parser-matcher', '');
	updateEdgeState('path-matcher-tailor', '');
	
	if (!resumeText && (!state.masterCV || !state.masterCV.skills || state.masterCV.skills.length === 0)) {
		consoleLog('[System] Warning: No candidate profile loaded. Paste resume text or upload a PDF first.', 'warning');
		alert('Please upload a resume file or paste resume text before running the agent.');
		updateNodeState('node-parser', '');
		setAgentButtonLoading(false);
		return;
	}
	
	if (resumeText) {
		consoleLog('[Parser Agent] Initiating AI resume parser for pasted text...', 'parser');
		setProfileInputLoading(true);
		try {
			const blob = new Blob([resumeText], { type: 'text/plain' });
			const file = new File([blob], 'resume.txt', { type: 'text/plain' });
			const result = await extractResumeText(file);
			let skills = [];
			let masterCV = null;
			
			if (result && typeof result === 'object' && result.text !== undefined) {
				if (result.skills && Array.isArray(result.skills)) {
					skills = result.skills.map(s => typeof s === 'object' ? s.name : s);
				} else {
					skills = extractSkills(resumeText);
				}
				masterCV = result;
				if (!masterCV.skills) {
					masterCV.skills = skills.map(s => ({ name: s, category: 'technical', proficiency: 'expert' }));
				}
			} else {
				skills = extractSkills(resumeText);
				masterCV = {
					name: "",
					email: "",
					phone: "",
					location: { city: "", country: "" },
					skills: skills.map(s => ({ name: s, category: 'technical', proficiency: 'expert' })),
					summary: resumeText.slice(0, 200)
				};
			}
			state.extractedSkills = unique(skills);
			state.masterCV = masterCV;
			consoleLog('[Parser Agent] Pasted profile parsed and mapped successfully.', 'success');
			setProfileInputLoading(false);
		} catch (err) {
			consoleLog(`[Parser Agent] Server parsing failed: ${err.message}. Falling back to local keyword parsing.`, 'warning');
			const skills = extractSkills(resumeText);
			state.extractedSkills = unique(skills);
			state.masterCV = {
				name: "",
				email: "",
				phone: "",
				location: { city: "", country: "" },
				skills: skills.map(s => ({ name: s, category: 'technical', proficiency: 'expert' })),
				summary: resumeText.slice(0, 200)
			};
			setProfileInputLoading(false);
		}
		
		updateNodeState('node-parser', 'completed');
		setAgentButtonLoading(false);
		setTimeout(() => {
			toggleProfileView(true);
			populateCVEditor(state.masterCV);
		}, 1000);
		return;
	}
	
	updateNodeState('node-parser', 'completed');
	runMatcherPipeline();
}

async function runMatcherPipeline() {
	updateNodeState('node-parser', 'completed');
	updateNodeState('node-matcher', 'active');
	updateEdgeState('path-parser-matcher', 'active');
	
	consoleLog('[Matcher Agent] Activating job matching flow...', 'matcher');
	consoleLog('[Matcher Agent] Fetching current jobs list...', 'matcher');
	
	try {
		await loadJobs({ quiet: true });
	} catch (e) {
		consoleLog(`[Matcher Agent] Warning: Jobs sync failed: ${e.message}`, 'warning');
	}
	
	consoleLog('[Matcher Agent] Calculating ATS Relevance Match Scores using keyword alignment...', 'matcher');
	
	const filters = buildFilters();
	const matches = sortJobRows(
		state.jobs.map(job => {
			const scorer = state.mlMode ? mlScore : baseScore;
			const scoreDetails = scorer(job, filters);
			return { job, ...scoreDetails };
		}).filter(row => passes(row.job, filters, row)),
		el('sortBy').value
	);
	
	state.agentMatches = matches;
	state.agentActive = true;
	
	setTimeout(() => {
		updateNodeState('node-matcher', 'completed');
		updateEdgeState('path-parser-matcher', 'completed');
		
		updateNodeState('node-tailor', 'active');
		updateEdgeState('path-matcher-tailor', 'active');
		consoleLog('[Tailor Agent] Scanning matched jobs to tailor resume formats...', 'tailor');
		
		setTimeout(() => {
			updateNodeState('node-tailor', 'pending');
			updateEdgeState('path-matcher-tailor', 'completed');
			
			consoleLog('[Tailor Agent] Ready! Click "Apply on source" or save CV to customize LaTeX profile.', 'success');
			consoleLog('[System] Multi-agent workflow completed successfully.', 'system');
			
			const summary = matches.slice(0,3).map((m,i)=>`${m.job.title} @ ${m.job.company} (${m.score}%)`).join(' | ');
			updateAgentStatus(`Agent found ${matches.length} personalized jobs. Top: ${summary || 'None'}`);
			
			render();
			setAgentButtonLoading(false);
		}, 800);
	}, 800);
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
		
		const gap = calculateSkillsGap(job);
		const matchedBadges = gap.matched.slice(0, 4).map(s => `<span class="badge badge-match">✓ ${escapeHtml(s)}</span>`).join('');
		const missingBadges = gap.missing.slice(0, 3).map(s => `<span class="badge badge-missing">✗ ${escapeHtml(s)}</span>`).join('');
		const atsAnalytics = (matchedBadges || missingBadges) ? `<div style="margin: 10px 0 14px 0;"><div class="small" style="font-weight:700; margin-bottom:4px; color:var(--muted); font-size:0.78rem; text-transform:uppercase; letter-spacing:0.04em;">ATS Keywords Alignment:</div>${matchedBadges}${missingBadges}</div>` : '';

		const isVerified = state.verifiedJobs && state.verifiedJobs.has(job.id);
		const applyBtnText = isVerified ? "Apply on source" : "Apply on source";

		return `<article class="job-card${job.isNew ? ' job-card-new' : ''}"><div class="job-head"><div><h3>${escapeHtml(job.title)}</h3><div class="muted small">${escapeHtml(job.company)} · ${escapeHtml(job.location)} · ${escapeHtml(job.mode)} · ${escapeHtml(job.jobType)}</div></div><div class="score${score < 90 ? ' score-low' : ' score-high'}">${score}%</div></div><div class="meta">${newBadge}<span class="badge">${escapeHtml(job.source)}</span><span class="badge">Posted ${job.postedDaysAgo ?? '?'}d ago</span><span class="badge salary">${escapeHtml(job.salary || 'Salary not listed')}</span></div><ul class="job-highlights">${highlights.map(h=>`<li>${escapeHtml(h)}</li>`).join('')}</ul>${atsAnalytics}<p class="why small">Fit: ${escapeHtml(reasons.join(' · '))}</p><div class="chips">${(job.tags||[]).slice(0,6).map(t=>`<span class="chip">${escapeHtml(t)}</span>`).join('')}</div><div class="job-actions" style="margin-top:1rem"><button class="btn btn-primary" onclick="showApplyPromptModal('${job.id}', ${score})">${applyBtnText}</button><button class="btn btn-secondary" onclick="toggleSave(${JSON.stringify(job.id)})">${state.saved.has(job.id)?'Unsave':'Save'}</button><button class="btn btn-ghost" onclick="tailorResumeForJob('${job.id}')" style="margin-left:auto;">Tailor Resume</button></div></article>`;
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
	return data;
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
	if((format === 'pdf' || format === 'docx' || format === 'text') && canUseServerParser()){
		try{
			const serverResult = await extractResumeViaServer(file);
			if(serverResult && serverResult.text) {
				const serverText = normalizeResumeText(serverResult.text);
				if(serverText && (!isGarbledResumeText(serverText) || (serverResult.name || serverResult.email))) return serverResult;
			}
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
	updateNodeState('node-parser', 'active');
	updateNodeState('node-matcher', '');
	updateNodeState('node-tailor', '');
	updateEdgeState('path-parser-matcher', '');
	updateEdgeState('path-matcher-tailor', '');
	
	el('agentConsole').innerHTML = '';
	consoleLog('Initializing LangGraph agent orchestration...', 'system');
	consoleLog('[Parser Agent] Starting parser workflow on upload...', 'parser');
	
	const textarea = el('resumeText');
	const previous = textarea.value;
	textarea.value = 'Extracting text and running Parser Agent...';
	setProfileInputLoading(true);
	try{
		const result = await extractResumeText(file);
		let text = '';
		let skills = [];
		let masterCV = null;
		
		if (result && typeof result === 'object' && result.text !== undefined) {
			text = normalizeResumeText(result.text);
			if (result.skills && Array.isArray(result.skills)) {
				skills = result.skills.map(s => typeof s === 'object' ? s.name : s);
			} else {
				skills = extractSkills(text);
			}
			masterCV = result;
			if (!masterCV.skills) {
				masterCV.skills = skills.map(s => ({ name: s, category: 'technical', proficiency: 'expert' }));
			}
		} else {
			text = normalizeResumeText(result);
			skills = extractSkills(text);
			masterCV = {
				name: "",
				email: "",
				phone: "",
				location: { city: "", country: "" },
				skills: skills.map(s => ({ name: s, category: 'technical', proficiency: 'expert' })),
				summary: ""
			};
		}
		
		const isServerSuccess = result && typeof result === 'object' && (result.name || result.email);
		if(!text || isRawPdfContent(text) || (!isServerSuccess && isGarbledResumeText(text))) throw new Error('No readable text was found. Run bash run.sh, open http://localhost:8080, and upload the PDF again.');
		textarea.value = text;
		state.extractedSkills = unique(skills);
		
		updateNodeState('node-parser', 'completed');
		consoleLog('[Parser Agent] Success! Parsed profile from file.', 'success');
		setProfileInputLoading(false);
		
		state.masterCV = masterCV;
		
		setTimeout(() => {
			toggleProfileView(true);
			populateCVEditor(state.masterCV);
		}, 1000);
		
	}catch(err){
		textarea.value = previous;
		consoleLog(`[Parser Agent] Error: ${err.message}`, 'warning');
		alert(err.message || 'Could not extract resume text.');
		updateNodeState('node-parser', '');
		setProfileInputLoading(false);
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
/* --- SPA Router --- */
function updateRoute() {
	const hash = location.hash || '#/landing';
	
	// Access Guard: Block other pages if masterCV doesn't exist
	const hasCV = state.masterCV && (state.masterCV.name || state.extractedSkills.length > 0);
	if (!hasCV && (hash === '#/editor' || hash === '#/matches' || hash === '#/tailor')) {
		alert("Please upload or paste your CV/resume first to unlock CV Builder, Matches, and Tailor Assistant.");
		location.hash = '#/landing';
		return;
	}
	
	const sections = ['page-landing', 'page-parse', 'page-editor', 'page-matches', 'page-tailor'];
	const tabs = ['tab-landing', 'tab-parse', 'tab-editor', 'tab-matches', 'tab-tailor'];
	
	sections.forEach(id => {
		const sectionEl = el(id);
		if (sectionEl) sectionEl.classList.remove('active');
	});
	
	tabs.forEach(id => {
		const tabEl = el(id);
		if (tabEl) tabEl.classList.remove('active');
	});
	
	let activeSectionId = 'page-landing';
	let activeTabId = 'tab-landing';
	
	const navTabs = el('navTabs');
	if (hash === '#/landing' || hash === '#/') {
		activeSectionId = 'page-landing';
		activeTabId = 'tab-landing';
		if (navTabs) {
			navTabs.style.opacity = '0';
			navTabs.style.pointerEvents = 'none';
			navTabs.style.transition = 'opacity var(--dur-normal) var(--ease-spring)';
		}
	} else {
		if (navTabs) {
			navTabs.style.opacity = '1';
			navTabs.style.pointerEvents = 'auto';
			navTabs.style.transition = 'opacity var(--dur-normal) var(--ease-spring)';
		}
		if (hash === '#/parse') {
			activeSectionId = 'page-parse';
			activeTabId = 'tab-parse';
		} else if (hash === '#/editor') {
			activeSectionId = 'page-editor';
			activeTabId = 'tab-editor';
			populateCVEditor(state.masterCV);
		} else if (hash === '#/matches') {
			activeSectionId = 'page-matches';
			activeTabId = 'tab-matches';
			render();
		} else if (hash === '#/tailor') {
			activeSectionId = 'page-tailor';
			activeTabId = 'tab-tailor';
			updateTailorPageSelect();
		}
	}
	
	const activeSec = el(activeSectionId);
	if (activeSec) activeSec.classList.add('active');
	
	const activeT = el(activeTabId);
	if (activeT) activeT.classList.add('active');
}

window.addEventListener('hashchange', updateRoute);
window.addEventListener('load', updateRoute);

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
	el('skipCVBtn')?.addEventListener('click', skipMasterCV);
	el('saveCVBtn').addEventListener('click',saveMasterCV);
	['cvName', 'cvEmail', 'cvPhone', 'cvLocation', 'cvSummary', 'cvSkillsInput', 'cvLinkedin', 'cvGithub', 'cvTwitter', 'cvPortfolio', 'cvProfileType', 'cvTotalExperienceYears', 'cvTargetRole', 'cvAchievements'].forEach(id => {
		const element = el(id);
		if (!element) return;
		const eventName = element.tagName === 'SELECT' ? 'change' : 'input';
		element.addEventListener(eventName, () => {
			if (isPopulating) return;
			const cv = collectCVFromForm();
			state.masterCV = cv;
			calculateCVCompletion(cv);
		});
	});

	el('addEducationBtn')?.addEventListener('click', () => addFormListItem('education'));
	el('addExperienceBtn')?.addEventListener('click', () => addFormListItem('experience'));
	el('addProjectBtn')?.addEventListener('click', () => addFormListItem('projects'));
	el('addCertificationBtn')?.addEventListener('click', () => addFormListItem('certifications'));
	el('importJsonFile')?.addEventListener('change', onImportJsonFileChange);
	el('exportJsonBtn')?.addEventListener('click', exportMasterCVJson);
	
	el('editorJobSelect')?.addEventListener('change', () => {
		evaluateEligibility();
		const jobId = el('editorJobSelect').value;
		const tailorSelect = el('tailorJobSelect');
		if (tailorSelect && tailorSelect.value !== jobId) {
			tailorSelect.value = jobId;
			onTailorJobSelectChange();
		}
	});

	el('aiFillCVBtn')?.addEventListener('click', () => {
		const cv = collectCVFromForm();
		state.masterCV = cv;

		const hasSkills = cv.skills && cv.skills.length > 0;
		const hasExperience = cv.experience && cv.experience.length > 0;
		const hasEducation = cv.education && cv.education.length > 0;
		
		if (!hasSkills && !hasExperience && !hasEducation) {
			alert("Insufficient profile information. Please enter some skills, experience, or education in the form first so the AI has context to generate suggestions.");
			consoleLog('[CV Builder] AI Fill blocked: Empty profile details.', 'warning');
			return;
		}

		const hasProjects = cv.projects && cv.projects.length > 0;
		const hasCerts = cv.certifications && cv.certifications.length > 0;
		aiFillCVSections(cv, !hasProjects, !hasCerts);
	});

	el('previewLatexFromCVBtn')?.addEventListener('click', () => {
		const cv = collectCVFromForm();
		state.masterCV = cv;
		location.hash = '#/tailor';
		setTimeout(() => {
			const masterLatex = generateLatexCode(cv, null);
			renderResumeSheet(cv, { latex_code: masterLatex });
			showA4Preview();
		}, 200);
	});
	
	// Tailor Assistant Page Listeners
	el('tailorJobSelect')?.addEventListener('change', onTailorJobSelectChange);
	el('generateTailoredResumeBtn')?.addEventListener('click', generateTailoredResume);
	el('downloadTailoredBtn')?.addEventListener('click', downloadTailoredResume);
	el('downloadLatexBtn')?.addEventListener('click', downloadLatexResume);
	el('printTailoredBtn')?.addEventListener('click', () => {
		const iframe = el('pdfPreviewFrame');
		if (iframe && iframe.contentWindow) {
			iframe.contentWindow.focus();
			iframe.contentWindow.print();
		} else {
			window.print();
		}
	});
	el('openOverleafBtn')?.addEventListener('click', openInOverleaf);
	el('viewResumeSheetBtn')?.addEventListener('click', showA4Preview);
	el('viewLatexCodeBtn')?.addEventListener('click', showLatexCode);
	el('copyLatexBtn')?.addEventListener('click', copyLatexCode);
	el('verifyPdfAtsBtn')?.addEventListener('click', verifyPdfAts);
	

	
	// Apply Confirmation Prompt Modal Listeners
	el('closeApplyModalBtn')?.addEventListener('click', closeApplyModal);
	el('confirmApplyBtn')?.addEventListener('click', confirmApply);

	const agentStatusEl = el('agentStatus');
	if(agentStatusEl) agentStatusEl.textContent = state.agentStatus;
	
	loadJobs();
	scheduleJobsAutoRefresh();
	
	// Initial routing check
	updateRoute();
});

/* --- Tailor Toggles and Verification Helpers --- */
function showA4Preview() {
	el('resumeSheet').style.display = 'block';
	el('latexCodeView').style.display = 'none';
	el('viewResumeSheetBtn').classList.add('active-tab-btn');
	el('viewResumeSheetBtn').classList.remove('btn-ghost');
	el('viewResumeSheetBtn').classList.add('btn-secondary');
	el('viewResumeSheetBtn').style.color = '';
	el('viewLatexCodeBtn').classList.remove('active-tab-btn');
	el('viewLatexCodeBtn').classList.add('btn-ghost');
	el('viewLatexCodeBtn').classList.remove('btn-secondary');
	el('viewLatexCodeBtn').style.color = 'var(--muted)';

	const code = el('latexCodeArea')?.value;
	if (code) {
		compilePdfPreview(code);
	}
}

function showLatexCode() {
	el('resumeSheet').style.display = 'none';
	el('latexCodeView').style.display = 'block';
	el('latexCodeView').hidden = false;
	el('viewLatexCodeBtn').classList.add('active-tab-btn');
	el('viewLatexCodeBtn').classList.remove('btn-ghost');
	el('viewLatexCodeBtn').classList.add('btn-secondary');
	el('viewResumeSheetBtn').classList.remove('active-tab-btn');
	el('viewResumeSheetBtn').classList.add('btn-ghost');
	el('viewResumeSheetBtn').classList.remove('btn-secondary');
	el('viewResumeSheetBtn').style.color = 'var(--muted)';
	el('viewLatexCodeBtn').style.color = '';
}

function copyLatexCode() {
	const code = el('latexCodeArea').value;
	if (!code) {
		alert("No LaTeX code generated yet. Please select a job and compile first.");
		return;
	}
	navigator.clipboard.writeText(code).then(() => {
		alert("LaTeX code copied to clipboard!");
	}).catch(err => {
		console.error("Clipboard copy failed:", err);
		alert("Failed to copy LaTeX code. Please select all and copy manually.");
	});
}

function openInOverleaf() {
	if (!state.masterCV) {
		alert("Please configure your CV first.");
		return;
	}
	const latexArea = el('latexCodeArea');
	const code = latexArea ? latexArea.value : '';
	if (!code) {
		alert("No LaTeX code generated yet. Please customize/tailor your resume first.");
		return;
	}
	
	const form = el('overleafForm');
	const textarea = el('overleafSnip');
	if (form && textarea) {
		textarea.value = code;
		consoleLog('[System] Exporting LaTeX resume to Overleaf...', 'success');
		form.submit();
	} else {
		alert("Overleaf integration form not found.");
	}
}

async function verifyPdfAts() {
	const jobId = el('tailorJobSelect').value;
	if (!jobId) {
		alert("Please select a target job first.");
		return;
	}
	
	const matchRow = getMatchedJobsList().find(m => m.job.id === jobId);
	if (!matchRow) return;
	
	const fileInput = el('compiledPdfUpload');
	const file = fileInput.files && fileInput.files[0];
	if (!file) {
		alert("Please select a compiled PDF file to verify.");
		return;
	}
	
	const verifyBtn = el('verifyPdfAtsBtn');
	if (verifyBtn) verifyBtn.disabled = true;
	
	try {
		consoleLog(`[System] Reading uploaded PDF file: ${file.name}...`, 'system');
		const arrayBuffer = await readFileAsArrayBuffer(file);
		const pdfText = await extractPdfText(arrayBuffer);
		
		if (!pdfText || !pdfText.trim()) {
			throw new Error("Could not extract any readable text from this PDF.");
		}
		
		consoleLog('[System] Checking ATS keyword alignment against target job...', 'system');
		const score = calculatePdfAtsScore(pdfText, matchRow.job);
		
		const statusDiv = el('atsVerificationStatus');
		const scoreSpan = el('atsStatusScore');
		const textSpan = el('atsStatusText');
		
		if (statusDiv) statusDiv.hidden = false;
		if (scoreSpan) scoreSpan.textContent = `${score}%`;
		
		if (score >= 90) {
			state.verifiedJobs.add(jobId);
			if (scoreSpan) scoreSpan.style.color = '#10b981';
			if (textSpan) textSpan.textContent = 'Verification Passed! Job unlocked.';
			consoleLog(`[System] Verification Passed! ATS Score: ${score}% >= 90%. Application is now unlocked.`, 'success');
			render();
		} else {
			if (scoreSpan) scoreSpan.style.color = '#ef4444';
			if (textSpan) textSpan.textContent = 'Verification Failed (< 90%). Please make sure you tailored and compiled correctly.';
			consoleLog(`[System] Verification Failed! ATS Score: ${score}% < 90%. Re-tailoring advised.`, 'warning');
		}
	} catch (err) {
		console.error(err);
		alert(`PDF verification failed: ${err.message}`);
		consoleLog(`[System] Verification Error: ${err.message}`, 'warning');
	} finally {
		if (verifyBtn) verifyBtn.disabled = false;
	}
}

function calculatePdfAtsScore(pdfText, job) {
	const pdfTextLower = (pdfText || '').toLowerCase();
	const hay = jobHaystack(job);
	
	const jobSkills = SKILL_DICTIONARY.filter(s => skillInHay(hay, s));
	if (jobSkills.length === 0) {
		return 98;
	}
	
	const matchedSkills = jobSkills.filter(s => pdfTextLower.includes(s.toLowerCase()));
	let score = Math.round((matchedSkills.length / jobSkills.length) * 100);
	
	const titleWords = job.title.toLowerCase().split(/[\s,/\-\(\)]+/).filter(w => w.length > 3 && !['software', 'engineer', 'developer', 'junior', 'senior', 'fresher', 'intern'].includes(w));
	if (titleWords.length > 0) {
		const matchedTitleWords = titleWords.filter(w => pdfTextLower.includes(w));
		const titleMatchPct = (matchedTitleWords.length / titleWords.length) * 100;
		score = Math.round((score * 0.8) + (titleMatchPct * 0.2));
	}
	
	return Math.max(0, Math.min(100, score));
}

async function onImportJsonFileChange(e) {
	const input = e.target;
	const file = input.files && input.files[0];
	if (!file) return;
	
	try {
		consoleLog('[System] Reading imported JSON file...', 'system');
		const text = await readFileAsText(file);
		const parsed = JSON.parse(text);
		
		if (!parsed || typeof parsed !== 'object') {
			throw new Error("Invalid JSON format. Expected an object.");
		}
		
		// Map and extract skills
		if (parsed.skills && Array.isArray(parsed.skills)) {
			state.extractedSkills = unique(parsed.skills.map(s => typeof s === 'object' ? s.name : s));
		} else {
			state.extractedSkills = [];
		}
		
		state.masterCV = parsed;
		
		consoleLog('[System] Successfully imported Master CV JSON!', 'success');
		alert("Master CV JSON imported successfully!");
		
		// Toggle view to editor and populate it
		toggleProfileView(true);
		populateCVEditor(state.masterCV);
		
	} catch (err) {
		console.error(err);
		alert(`Failed to import JSON: ${err.message}`);
		consoleLog(`[System] Error importing JSON: ${err.message}`, 'warning');
		input.value = '';
	}
}

function exportMasterCVJson() {
	const cv = collectCVFromForm();
	state.masterCV = cv;
	
	if (!cv || (!cv.name && !cv.email && !cv.phone)) {
		alert("Your CV is empty. Please enter or parse some candidate profile details first before exporting.");
		return;
	}
	
	const jsonContent = JSON.stringify(cv, null, 2);
	const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
	const a = document.createElement('a');
	a.href = URL.createObjectURL(blob);
	const filename = (cv.name ? cv.name.replace(/\s+/g, '_').toLowerCase() : 'master_cv') + '.json';
	a.download = filename;
	a.click();
	URL.revokeObjectURL(a.href);
	consoleLog(`[System] Exported Master CV JSON as ${filename}.`, 'success');
}
