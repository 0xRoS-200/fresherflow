/* Live job feeds (browser-safe APIs with CORS) */
const JobsAPI = (() => {
	const stripHtml = text => (text || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();

	

	function estimatePostedDays(createdAt){
		if(!createdAt) return 0;
		const parsed = Date.parse(createdAt);
		if(Number.isNaN(parsed)) return 0;
		return Math.max(0, Math.floor((Date.now() - parsed) / 86400000));
	}

	function dedupe(jobs){
		const map = new Map();
		for(const job of jobs){
			const key = job.id || job.applyUrl;
			if(key && !map.has(key)) map.set(key, job);
		}
		return [...map.values()];
	}

	function isIndiaLocation(locationText){
		const loc = (locationText || '').toLowerCase();
		return /india|indian|bengaluru|bangalore|hyderabad|pune|chennai|mumbai|delhi|gurugram|gurgaon|noida|kolkata|ahmedabad|karnataka|maharashtra|telangana|tamil nadu/.test(loc);
	}

	

	function fromTheMuse(item){
		const locations = item.locations || [];
		const locationText = locations.map(l => l.name).filter(Boolean).join(', ') || 'Remote';
		const mode = locations.some(l => /remote|flexible/i.test(l.name || '')) ? 'Remote' : 'Onsite';
		const levels = item.levels || [];
		const levelNames = levels.map(l => (l.name || '').toLowerCase());
		const isEntry = levelNames.some(ln => ln.includes('entry') || ln.includes('intern') || ln.includes('junior'));
		const isSenior = levelNames.some(ln => ln.includes('senior') || ln.includes('lead') || ln.includes('principal') || ln.includes('manager'));
		const expMax = isEntry ? 1 : (isSenior ? 5 : 3);
		return {
			id: item.refs?.landing_page || item.id || item.name,
			title: item.name || 'Unknown role',
			company: item.company?.name || 'Unknown',
			location: locationText,
			mode,
			jobType: (item.type || item.job_type || 'Full-time').replace(/_/g, ' '),
			postedDaysAgo: estimatePostedDays(item.publication_date),
			source: 'themuse',
			salary: 'Salary not listed',
			applyUrl: item.refs?.landing_page,
			experienceMax: expMax,
			tags: [
				...(item.categories || []).map(c => (c.name || '').toLowerCase()).filter(Boolean),
				...levelNames.filter(Boolean),
			],
			description: stripHtml(item.contents || item.description || ''),
		};
	}

	async function fetchJson(url, timeoutMs = 12000){
		const ctrl = new AbortController();
		const timer = setTimeout(() => ctrl.abort(), timeoutMs);
		try{
			const resp = await fetch(url, { signal: ctrl.signal });
			if(!resp.ok) throw new Error(`${url} returned ${resp.status}`);
			return resp.json();
		}finally{
			clearTimeout(timer);
		}
	}

	// fetchLeverCompany and fetchLeverIndia functions removed

	async function fetchTheMuseLocation(location, pages = 3){
		const jobs = [];
		for(let page = 1; page <= pages; page++){
			try{
				const q = encodeURIComponent(location);
				const data = await fetchJson(
					`https://www.themuse.com/api/public/jobs?page=${page}&location=${q}`,
					8000,
				);
				if(!data.results || !data.results.length) break;
				for(const item of data.results){
					const job = fromTheMuse(item);
					if(job.applyUrl && isIndiaLocation(job.location)) jobs.push(job);
				}
			}catch(_e){
				break;
			}
		}
		return jobs;
	}

	async function fetchTheMuseIndiaTech(){
		const locations = ['Bengaluru', 'Hyderabad', 'Pune', 'Chennai', 'Mumbai', 'Delhi', 'India', 'Remote'];
		const results = await Promise.allSettled(
			locations.map(loc => fetchTheMuseLocation(loc, 3))
		);
		const jobs = [];
		for(const r of results){
			if(r.status === 'fulfilled') jobs.push(...r.value);
		}
		return jobs;
	}

	async function fetchArbeitnowJobs(){
		try{
			const data = await fetchJson('https://www.arbeitnow.com/api/job-board-api', 8000);
			const jobs = [];
			for(const item of data.data || []){
				const loc = item.location || 'Remote';
				if(!isIndiaLocation(loc) && !item.remote) continue;
				const title = item.title || 'Unknown role';
				const desc = stripHtml(item.description || '');
				const locLower = loc.toLowerCase();
				const entryHint = /intern|junior|entry|fresher|graduate|trainee|new grad/i.test(`${title} ${desc.slice(0, 2000)}`);
				jobs.push({
					id: `arbeitnow-${item.slug || item.url}`,
					title,
					company: item.company_name || 'Unknown',
					location: loc,
					mode: (item.remote || /remote|wfh/i.test(locLower)) ? 'Remote' : 'Onsite',
					jobType: 'Full-time',
					postedDaysAgo: 1,
					source: 'arbeitnow',
					salary: 'Salary not listed',
					applyUrl: item.url,
					experienceMax: entryHint ? 1 : 3,
					tags: item.remote ? ['remote'] : [],
					description: desc.slice(0, 6000),
				});
			}
			return jobs;
		}catch(_e){ return []; }
	}

	async function fetchJobicyJobs(){
		try{
			const data = await fetchJson('https://jobicy.com/api/v2/remote-jobs', 8000);
			const jobs = [];
			for(const item of data.jobs || []){
				const title = item.jobTitle || 'Unknown role';
				const desc = stripHtml(item.jobDescription || '');
				const loc = item.jobGeo || 'Remote';
				const locLower = loc.toLowerCase();
				if(!locLower.includes('india') && !locLower.includes('anywhere') && !locLower.includes('world') && !locLower.includes('global')) continue;
				const entryHint = /intern|junior|entry|fresher|graduate|trainee|new grad/i.test(`${title} ${desc.slice(0, 2000)}`);
				jobs.push({
					id: `jobicy-${item.id}`,
					title,
					company: item.companyName || 'Unknown',
					location: loc,
					mode: 'Remote',
					jobType: (item.jobType || 'Full-time').replace(/_/g, ' '),
					postedDaysAgo: estimatePostedDays(item.pubDate),
					source: 'jobicy',
					salary: item.annualSalaryMin || 'Salary not listed',
					applyUrl: item.url,
					experienceMax: entryHint ? 1 : 3,
					tags: (item.jobIndustry || '').split(',').map(t => t.trim().toLowerCase()).filter(Boolean),
					description: desc.slice(0, 6000),
				});
			}
			return jobs;
		}catch(_e){ return []; }
	}

	async function fetchLiveJobs(){
		const tasks = [
			{ name: 'The Muse (India tech)', run: fetchTheMuseIndiaTech },
			{ name: 'Arbeitnow', run: fetchArbeitnowJobs },
			{ name: 'Jobicy', run: fetchJobicyJobs },
		];
		const results = await Promise.allSettled(tasks.map(t => t.run()));
		const jobs = [];
		const sources = [];
		const errors = [];
		results.forEach((result, i) => {
			if(result.status === 'fulfilled'){
				jobs.push(...result.value);
				if(result.value.length) sources.push(`${tasks[i].name} (${result.value.length})`);
			}else{
				errors.push(`${tasks[i].name}: ${result.reason?.message || 'failed'}`);
			}
		});
		return {
			jobs: dedupe(jobs),
			sources,
			errors,
			fetchedAt: new Date().toISOString(),
		};
	}

	return { fetchLiveJobs, dedupe, stripHtml, isIndiaLocation };
})();
