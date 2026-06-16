# Job Search Agent Implementation Guide

## Overview

The **Job Search Agent (Agent 2)** searches for matching jobs, extracts metadata, calculates ATS scores, and ranks jobs by relevance. It works downstream of the Parser Agent and feeds into the CV Tailor Agent.

## Architecture

```
Master CV Input
    ↓
Extract Keywords & Requirements
    ↓
Process Job Listings (batch)
    ├─ Extract Job Metadata (LLM)
    ├─ Calculate ATS Score (LLM + Keyword Matching)
    └─ Generate Job Level/Compensation Data
    ↓
Filter by ATS Threshold (75+)
    ↓
Rank & Categorize
    ├─ Excellent Fit (90+)
    ├─ Strong Fit (80-89)
    ├─ Good Fit (75-79)
    └─ Below Threshold (<75)
    ↓
Ranked Job List with Recommendations
```

## Core Components

### 1. JobSearchAgent

Main orchestrator with these methods:

```python
# Process multiple jobs at once
result = agent.process_job_listings(master_cv, job_listings)

# Extract metadata from single job
metadata, confidence = agent.extract_job_metadata(job_description)

# Calculate comprehensive ATS score
ats_score, analysis = agent.calculate_ats_score(master_cv, job_description)

# Filter by minimum ATS threshold
filtered = agent.filter_jobs_by_ats(jobs_with_scores, min_score=75)

# Rank jobs by relevance
ranked = agent.rank_jobs(filtered_jobs)

# Generate search queries for job portals
queries = agent.generate_job_search_queries(master_cv, "mid-level")
```

### 2. JobMetadata

Structured job information:

```python
class JobMetadata:
    job_title: str              # e.g., "Senior Python Engineer"
    company_name: str           # e.g., "Google"
    job_level: str             # entry, mid, senior, lead
    employment_type: str       # full-time, part-time, contract
    location: List[str]        # ["San Francisco", "Remote"]
    salary_min: float
    salary_max: float
    required_skills: List[str]
    required_experience_years: int
    preferred_skills: List[str]
    responsibilities: List[str]
    benefits: List[str]
```

### 3. LLM Prompts

#### Job Metadata Extraction

Extracts structured data from job descriptions:
- Job title, company, level
- Location, employment type
- Salary range
- Required/preferred qualifications
- Responsibilities and benefits

Temperature: 0.2 (deterministic)

#### ATS Score Calculation

Comprehensive scoring across:
- **Keyword Match** (0-30 points)
- **Experience Match** (0-25 points)
- **Education Match** (0-15 points)
- **Format Score** (0-15 points)
- **Language Score** (0-15 points)

**Total: 0-100 scale**

#### Job Ranking

Ranks multiple jobs based on:
- ATS score (primary)
- Growth potential
- Company reputation/stability
- Compensation competitiveness
- Work environment factors

## Usage Examples

### Basic Job Processing

```python
from cv_customizer.agents.job_search_agent import JobSearchAgent
from cv_customizer.agents.llm_provider import LLMProviderFactory

provider = LLMProviderFactory.get_provider("claude")
agent = JobSearchAgent(provider=provider)

# Sample job listings
job_listings = [
    {
        "id": "job1",
        "title": "Python Engineer",
        "description": "We are looking for...",
        "url": "https://example.com/job1"
    },
    {
        "id": "job2",
        "title": "Full Stack Developer",
        "description": "Join our team...",
        "url": "https://example.com/job2"
    }
]

# Process with Master CV
result = agent.process_job_listings(master_cv, job_listings)

# Results include:
print(f"Processed: {result['processed_count']}")
print(f"Passed ATS: {result['passed_ats']}")
print(f"Top opportunity: {result['top_opportunities'][0]}")
```

### Extract Specific Job Metadata

```python
job_description = """
We're seeking a Senior Software Engineer with:
- 5+ years of experience
- Python, Go, or Rust expertise
- Cloud architecture experience (AWS/GCP)
- Team leadership skills
...
"""

metadata, confidence = agent.extract_job_metadata(job_description)

print(f"Title: {metadata.job_title}")
print(f"Required Experience: {metadata.required_experience_years} years")
print(f"Skills: {metadata.required_skills}")
print(f"Salary: ${metadata.salary_min}k - ${metadata.salary_max}k")
print(f"Confidence: {confidence:.0%}")
```

### Calculate ATS Score

```python
# Single job ATS analysis
ats_score, analysis = agent.calculate_ats_score(master_cv, job_description)

print(f"ATS Score: {ats_score}/100")
print(f"Keyword Match: {analysis['keyword_match']}/30")
print(f"Experience Match: {analysis['experience_match']}/25")
print(f"Pass ATS Filter: {analysis['pass_ats_filter']}")

if analysis['pass_ats_filter']:
    print("✅ Recommended to apply!")
else:
    print("⚠️  Below threshold, but consider:")
    for rec in analysis['recommendations']:
        print(f"  - {rec}")
```

### Generate Job Search Queries

```python
# Get optimized search queries
queries = agent.generate_job_search_queries(master_cv, "mid-level")

# LinkedIn searches
for query in queries['linkedin']['queries']:
    print(f"LinkedIn: {query}")

# Indeed searches
for query in queries['indeed']['queries']:
    print(f"Indeed: {query}")

# Target companies
for company in queries['target_companies']:
    print(f"Target: {company}")
```

### Filter & Rank Multiple Jobs

```python
# Process batch of jobs
jobs_with_scores = agent.process_job_listings(master_cv, job_listings)

# Filter by minimum ATS score (default 75)
filtered = agent.filter_jobs_by_ats(
    jobs_with_scores["jobs_with_scores"],
    min_score=75.0
)

# Rank by relevance
ranked = agent.rank_jobs(filtered)

# Display results
for job in ranked[:5]:
    print(f"{job['rank']}. {job['title']} @ {job['company']}")
    print(f"   ATS Score: {job['ats_score']:.1f}/100")
    print(f"   Fit: {job['fit_category']}")
    print(f"   Location: {', '.join(job['location'])}")
    print(f"   Salary: ${job['salary_range'][0]}k - ${job['salary_range'][1]}k")
    print()
```

## ATS Score Breakdown

### Scoring Components

| Component | Max Points | What It Measures |
|-----------|-----------|------------------|
| Keyword Match | 30 | Overlap of CV skills with job requirements |
| Experience Match | 25 | Years/type of experience alignment |
| Education Match | 15 | Degree level and field alignment |
| Format Score | 15 | CV readability for ATS systems |
| Language Score | 15 | Industry terminology & jargon match |

### Score Interpretation

| Score Range | Recommendation | Action |
|------------|-----------------|--------|
| 90-100 | Excellent Fit | Apply immediately |
| 80-89 | Strong Fit | Apply with confidence |
| 75-79 | Good Fit | Apply (may need to tailor) |
| 70-74 | Consider | Only if interested |
| <70 | Not Recommended | Skip or heavily tailor |

### Example Score Distribution

**Job: Senior Python Engineer at Google**

```
Job Description: "5+ years Python, distributed systems,
 cloud architecture (AWS/GCP), team lead experience"

CV: "4 years Python/Go, 2 years AWS/Lambda,
 managed 2-person team"

Breakdown:
  Keyword Match: 24/30 (80% - Python ✓, AWS ✓, distributed systems ✗)
  Experience: 20/25 (80% - years slightly lower, team lead ✓)
  Education: 12/15 (80% - BS CS, no advanced degree)
  Format: 14/15 (93% - good ATS format)
  Language: 13/15 (87% - good industry terminology)
  
Total ATS Score: 83/100 ⭐ STRONG FIT
Recommendation: Apply with confidence
```

## Fallback ATS Scoring

When LLM is unavailable, system uses keyword matching fallback:

```python
# Fallback calculation
common_keywords = CV_keywords ∩ Job_keywords
score = (|common_keywords| / |job_keywords|) * 100 * boost_factor

# Boost factor accounts for partial matches
score = min(100, score * 1.5)
```

## Company Culture Assessment

Beyond ATS score, assess culture fit:

```python
company_info = """
Google Culture:
- Highly competitive, fast-paced
- Data-driven decision making
- Strong emphasis on innovation
- Work-life balance: moderate
- Team size: 8-12 per squad
"""

assessment = agent.assess_company_culture_fit(company_info, master_cv)

print(f"Culture Fit Score: {assessment['culture_fit_score']}/100")
print(f"Work Environment Match: {assessment['work_env_match']}/10")
print(f"Growth Opportunity: {assessment['growth_fit']}/10")
```

## Job Filtering Strategy

### Multi-Level Filtering

```
Input: 100 job listings
    ↓
Filter 1: ATS Score >= 75
    → 45 jobs pass
    ↓
Filter 2: Salary Range Acceptable
    → 32 jobs pass
    ↓
Filter 3: Location/Remote Preference
    → 18 jobs pass
    ↓
Filter 4: Company Culture Fit
    → 10 jobs pass (top candidates)
```

### Manual Override Options

```python
# Adjust ATS threshold
filtered = agent.filter_jobs_by_ats(jobs, min_score=70.0)  # Be more lenient

# Filter by specific criteria
location_jobs = [j for j in jobs if "Remote" in j["location"]]
startup_jobs = [j for j in jobs if j["company_size"] == "startup"]
high_pay = [j for j in jobs if j["salary_range"][1] > 200000]
```

## Integration Points

### With Parser Agent

```python
# Parser provides Master CV
master_cv = parser.parse_complete_workflow(input_data)["master_cv"]

# Job Search Agent uses it
jobs_result = job_agent.process_job_listings(master_cv, job_listings)
```

### With CV Tailor Agent

```python
# For each top opportunity, tailor CV
for job in ranked_jobs[:5]:
    tailored_cv = tailor_agent.tailor_cv_for_job(
        master_cv=master_cv,
        job_description=job["raw_description"],
        target_ats_score=95
    )
```

## Performance Metrics

### Processing Speed

| Operation | Time | Notes |
|-----------|------|-------|
| Extract metadata (1 job) | 2-3s | LLM call |
| Calculate ATS score (1 job) | 2-3s | LLM call |
| Rank 100 jobs | 200-300s | Parallel batch |
| Generate search queries | 3-5s | Single LLM call |

### Accuracy

| Metric | Expected | Target |
|--------|----------|--------|
| Metadata extraction | 85-90% | Critical fields correct |
| ATS score accuracy | 80-85% | Correlates with human review |
| Job ranking order | 75-80% | Top 5 are genuinely best fits |

## Configuration

### Environment Variables

```bash
# Job Search LLM provider
JOB_SEARCH_LLM_PROVIDER=claude

# ATS threshold
ATS_PASS_THRESHOLD=75

# Temperature for LLM (0.2 = deterministic)
JOB_AGENT_TEMPERATURE=0.2

# Max tokens for metadata extraction
JOB_METADATA_MAX_TOKENS=3000
```

### Agent Parameters

```python
agent_config = {
    "temperature": 0.2,           # Deterministic extraction
    "max_tokens": 3000,           # Metadata extraction
    "ats_threshold": 75,          # Minimum passing score
    "ranking_factors": {
        "ats_weight": 0.40,       # Primary factor
        "growth_weight": 0.20,    # Career growth
        "company_weight": 0.20,   # Company quality
        "compensation_weight": 0.15, # Salary
        "environment_weight": 0.05  # Work-life balance
    }
}
```

## Common Issues & Solutions

### Issue: Low ATS Scores Across All Jobs

**Cause:** Keyword mismatch between CV and job descriptions

**Solution:**
1. Ensure CV uses industry terminology
2. Add specific technical skills to CV
3. Use Parser Agent to enhance Master CV
4. Lower ATS threshold temporarily

### Issue: Inconsistent Metadata Extraction

**Cause:** Varied job description formats

**Solution:**
1. Use more specific extraction prompts
2. Enable LLM to request clarification
3. Implement post-extraction validation
4. Fall back to regex extraction for key fields

### Issue: False Positives (High ATS Score, Not Actually Good Fit)

**Cause:** Keyword-heavy job descriptions

**Solution:**
1. Weight experience level more heavily
2. Add education level verification
3. Use culture assessment as secondary filter
4. Manual review of top scores

## Testing

```python
# Test with sample job
sample_job = """
Senior Full-Stack Engineer
We're looking for someone with:
- 5+ years web development
- React, Node.js, Python
- AWS or GCP experience
- Leadership background
- $150k-200k salary
"""

# Extract metadata
metadata, conf = agent.extract_job_metadata(sample_job)
assert metadata.job_title == "Senior Full-Stack Engineer"
assert metadata.required_experience_years >= 5

# Calculate ATS (with sample CV)
score, analysis = agent.calculate_ats_score(master_cv, sample_job)
assert score > 0
assert "keyword_match" in analysis

# Rank multiple jobs
jobs = [...]
ranked = agent.rank_jobs(jobs)
assert ranked[0]["rank"] == 1
assert ranked[0]["ats_score"] >= ranked[1]["ats_score"]

print("✅ Job Search Agent tests passed")
```

## Files Reference

- **Job Search Agent**: `cv_customizer/agents/job_search_agent.py`
- **Job Search Prompts**: `cv_customizer/utils/job_prompts.py`
- **Master CV**: `cv_customizer/models/master_cv.py`
- **CV Utilities**: `cv_customizer/utils/cv_utils.py`

## Next Steps

Feature 6: **CV Tailor Agent** - Customize CV for specific jobs with LaTeX generation and Overleaf integration
