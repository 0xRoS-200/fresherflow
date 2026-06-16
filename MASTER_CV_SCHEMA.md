# Master CV Schema Documentation

## Overview

The **Master CV Schema** is the standardized data structure used across all three agents in the CV Customizer system:

- **Parser Agent**: Extracts data from PDFs/portfolios → Creates Master CV
- **Job Search Agent**: Uses Master CV to match jobs and calculate ATS scores
- **CV Tailor Agent**: Tailors content from Master CV for specific jobs

## Schema Structure

### Top-Level Fields

```json
{
  "cv_id": "string (UUID)",
  "user_id": "string (optional)",
  "personal_info": { ... },
  "professional_summary": { ... },
  "experience": [ ... ],
  "education": [ ... ],
  "skills": [ ... ],
  "languages": [ ... ],
  "certifications": [ ... ],
  "projects": [ ... ],
  "achievements": [ ... ],
  "additional_sections": { ... },
  "metadata": { ... }
}
```

---

## Detailed Field Specifications

### 1. Personal Information (`personal_info`)

**Required fields:**
- `first_name` - First name (string, 1+ chars)
- `last_name` - Last name (string, 1+ chars)
- `email` - Valid email address
- `phone` - Phone with country code (10+ chars)
- `location` - City, State, Country (1+ chars)

**Optional fields:**
- `linkedin_url` - LinkedIn profile URL
- `github_url` - GitHub profile URL
- `portfolio_url` - Portfolio website
- `personal_website` - Personal website
- `twitter_handle` - Twitter handle

**Example:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "phone": "+1-555-123-4567",
  "location": "San Francisco, CA, USA",
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "github_url": "https://github.com/johndoe"
}
```

---

### 2. Professional Summary (`professional_summary`)

**Fields:**
- `headline` - Professional headline (10-200 chars)
- `summary` - Career summary (20-1000 chars) ⭐ **Required for validation**
- `total_experience_years` - Years of experience (≥ 0)
- `specialization` - Area of expertise (optional)
- `key_achievements` - List of key achievements (optional)

**Example:**
```json
{
  "headline": "Senior Full-Stack Developer | Python & React Expert",
  "summary": "5+ years building scalable web applications...",
  "total_experience_years": 5,
  "specialization": "Full-Stack Web Development",
  "key_achievements": ["Led 10+ projects", "Team lead for 5 engineers"]
}
```

---

### 3. Experience (`experience`) - Array

⭐ **Required for validation:** At least 0 entries (but more is better for ATS)

**Fields per entry:**
- `company_name` - Company name (required)
- `job_title` - Job title (required)
- `employment_type` - full_time | part_time | contract | freelance | internship | temporary
- `location` - Job location (optional)
- `start_date` - Start date (YYYY-MM or YYYY-MM-DD)
- `end_date` - End date (optional, null if current)
- `is_current` - Currently working (boolean)
- `description` - Job responsibilities (required, 10+ chars)
- `achievements` - List of achievements (optional)
- `skills_used` - List of skills used (optional)

**Example:**
```json
{
  "company_name": "Tech Corp",
  "job_title": "Senior Backend Engineer",
  "employment_type": "full_time",
  "start_date": "2023-03",
  "is_current": true,
  "description": "Led development of microservices architecture...",
  "achievements": ["Improved performance by 40%"],
  "skills_used": ["Python", "FastAPI", "Docker"]
}
```

---

### 4. Education (`education`) - Array

⭐ **Required for validation:** At least 1 entry

**Fields per entry:**
- `institution` - University/School name (required)
- `degree` - Education level (bachelor | master | phd | diploma | certification | high_school)
- `field_of_study` - Major/Field (required)
- `location` - School location (optional)
- `start_date` - Start date (YYYY-MM or YYYY-MM-DD)
- `graduation_date` - Graduation date (required)
- `gpa` - GPA (optional, 0-4.0)
- `grade` - Final grade (optional)
- `description` - Additional details (optional)
- `activities` - Clubs, societies, awards (optional array)
- `courses` - Relevant courses taken (optional array)

**Example:**
```json
{
  "institution": "University of California, Berkeley",
  "degree": "bachelor",
  "field_of_study": "Computer Science",
  "graduation_date": "2021-05",
  "gpa": 3.8,
  "activities": ["Debate Club President", "Dean's List"],
  "courses": ["Data Structures", "Machine Learning"]
}
```

---

### 5. Skills (`skills`) - Array

⭐ **Required for validation:** At least 3 skills

**Fields per skill:**
- `name` - Skill name (required, e.g., "Python", "Project Management")
- `level` - Proficiency (beginner | intermediate | advanced | expert)
- `category` - Skill category (required, e.g., "Programming Languages", "Tools")
- `endorsements` - Number of endorsements (optional, ≥ 0)
- `years_of_experience` - Years with skill (optional, ≥ 0)

**Example:**
```json
[
  {
    "name": "Python",
    "level": "expert",
    "category": "Programming Languages",
    "years_of_experience": 5
  },
  {
    "name": "FastAPI",
    "level": "expert",
    "category": "Web Frameworks",
    "years_of_experience": 3
  },
  {
    "name": "Docker",
    "level": "advanced",
    "category": "DevOps",
    "years_of_experience": 3
  }
]
```

---

### 6. Languages (`languages`) - Array

**Fields per language:**
- `name` - Language name (required)
- `proficiency` - Level (beginner | intermediate | advanced | expert)
- `native` - Is native language (boolean)

**Example:**
```json
[
  {
    "name": "English",
    "proficiency": "expert",
    "native": true
  },
  {
    "name": "Spanish",
    "proficiency": "intermediate",
    "native": false
  }
]
```

---

### 7. Certifications (`certifications`) - Array

**Fields per certification:**
- `name` - Certification name (required)
- `issuer` - Issuing organization (required)
- `issue_date` - Date issued (YYYY-MM or YYYY-MM-DD)
- `expiration_date` - Expiration date (optional)
- `is_active` - Currently valid (boolean, default: true)
- `credential_id` - Credential ID (optional)
- `credential_url` - URL to credential (optional)
- `description` - Details (optional)

**Example:**
```json
{
  "name": "AWS Certified Solutions Architect",
  "issuer": "Amazon Web Services",
  "issue_date": "2023-06",
  "expiration_date": "2025-06",
  "credential_url": "https://aws.amazon.com/verification/123456"
}
```

---

### 8. Projects (`projects`) - Array

**Fields per project:**
- `name` - Project name (required)
- `description` - Project description (required, 10+ chars)
- `start_date` - Start date (optional)
- `end_date` - End date (optional)
- `is_current` - Currently working (boolean)
- `technologies_used` - Tech stack array (optional)
- `role` - Your role in project (optional)
- `team_size` - Team size (optional, ≥ 1)
- `project_url` - Project URL (optional)
- `github_url` - GitHub repository (optional)
- `demo_url` - Live demo URL (optional)
- `key_achievements` - Results achieved (optional array)
- `outcomes` - Project outcomes (optional)

**Example:**
```json
{
  "name": "AI Resume Parser",
  "description": "Built AI-powered tool to parse resumes...",
  "start_date": "2024-01",
  "is_current": true,
  "technologies_used": ["Python", "FastAPI", "LangChain"],
  "github_url": "https://github.com/user/project",
  "key_achievements": ["Parsed 10k+ resumes", "95% accuracy rate"]
}
```

---

### 9. Achievements (`achievements`) - Array

**Fields per achievement:**
- `title` - Achievement title (required)
- `description` - Achievement description (required, 10+ chars)
- `date` - Date achieved (YYYY-MM or YYYY-MM-DD)
- `issuer` - Organization (optional)
- `url` - Achievement URL (optional)

**Example:**
```json
{
  "title": "Employee of the Year 2023",
  "description": "Recognized for exceptional contribution...",
  "date": "2023-12",
  "issuer": "Tech Corp Inc."
}
```

---

### 10. Additional Sections (`additional_sections`)

Free-form object for custom sections not covered above:

**Example:**
```json
{
  "publications": "Published 3 articles on Medium...",
  "volunteering": "Mentor at Code2040...",
  "interests": "Open-source, distributed systems...",
  "languages_spoken": "English (native), Spanish (fluent)"
}
```

---

### 11. Metadata (`metadata`)

**Fields:**
- `created_at` - CV creation timestamp (ISO 8601)
- `updated_at` - Last update timestamp (ISO 8601)
- `source` - Data source: "pdf" | "portfolio" | "manual"
- `extraction_confidence` - Parser confidence (0-1)
- `parser_version` - Version of parser used (optional)
- `last_ats_score` - Last calculated ATS score (optional, 0-1)
- `last_ats_check_date` - Last ATS check timestamp (optional)

**Example:**
```json
{
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-06-16T14:45:30Z",
  "source": "portfolio",
  "extraction_confidence": 0.95,
  "parser_version": "1.0.0",
  "last_ats_score": 0.88
}
```

---

## Validation Rules

### Required Fields (For Valid CV)
1. ✅ `personal_info` (all required subfields)
2. ✅ `professional_summary.summary` (recommended: 50+ chars)
3. ✅ `skills` (minimum 3 skills)
4. ✅ `education` (at least 1 entry)

### ATS Confidence Scoring

The system calculates a **confidence score (0-1)** based on:

| Factor | Weight | Criteria |
|--------|--------|----------|
| Personal Info | 30% | Has LinkedIn + GitHub profiles |
| Professional Summary | 20% | Summary length > 100 chars |
| Experience | 20% | 1+ entry with achievements |
| Skills | 15% | 10+ skills with levels |
| Projects & Certs | 15% | 5+ combined entries |

**Example:** CV with all sections = **0.95** confidence

---

## API Endpoints Using Master CV

### Create/Update Master CV
```bash
POST /api/parser/master-cv
PUT /api/parser/master-cv/{user_id}
```

### Get Master CV
```bash
GET /api/parser/master-cv/{user_id}
```

### Validate Master CV
```bash
POST /api/parser/validate
Response:
{
  "is_valid": true,
  "missing_fields": [],
  "warnings": [],
  "confidence_score": 0.92
}
```

### Export Master CV
```bash
GET /api/parser/master-cv/{user_id}/export?format=json|pdf|txt
```

---

## Example Master CV (Full)

See `example_master_cv.json` for a complete real-world example.

---

## Implementation Notes

### For Parser Agent:
- Extract data from PDF/portfolio
- Map to Master CV schema
- Fill missing fields with `null`
- Return confidence score

### For Job Search Agent:
- Load Master CV
- Extract keywords and skills
- Calculate match score with job requirements
- Filter jobs by ATS score

### For CV Tailor Agent:
- Load Master CV
- Customize content for specific job
- Preserve all data in version history
- Generate LaTeX/PDF

---

## Version Control

Each CV can have multiple versions tracked for:
- Rollback capability
- Change history
- A/B testing different tailoring versions

---

## File Reference

- **Schema Definition**: `cv_customizer/models/master_cv.py`
- **Utilities**: `cv_customizer/utils/cv_utils.py`
- **Database Models**: `cv_customizer/models/database.py`
- **Example**: `cv_customizer/templates/example_master_cv.json`
