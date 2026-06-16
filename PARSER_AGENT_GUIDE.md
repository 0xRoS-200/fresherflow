# Parser Agent Implementation Guide

## Overview

The **Parser Agent (Agent 1)** extracts and structures resume/portfolio data into the standardized Master CV format. It supports both PDF uploads and portfolio website scraping.

## Architecture

```
Raw Input (PDF/URL)
    ↓
PDF Extractor / Portfolio Scraper
    ↓
Section Extraction & Cleaning
    ↓
LLM Processing (Data Extraction)
    ↓
LLM Processing (Structure to Master CV)
    ↓
Validation & Confidence Scoring
    ↓
Master CV Object
```

## Features

### 1. PDF Resume Parsing

```python
from cv_customizer.agents.parser_agent import ParserAgent
from cv_customizer.agents.llm_provider import LLMProviderFactory

# Initialize
provider = LLMProviderFactory.get_provider("gemini")
parser = ParserAgent(provider=provider)

# Parse PDF
extracted_data, confidence = parser.parse_pdf("/path/to/resume.pdf")

# Generate Master CV
master_cv, structuring_conf = parser.generate_master_cv(extracted_data)
```

#### PDF Extraction Methods

**Primary: pdfplumber**
- Supports tables, layout preservation
- Handles complex PDF structures
- Confidence: 95%

**Fallback: PyPDF2**
- Simpler text extraction
- Good for plain PDFs
- Confidence: 85%

### 2. Portfolio Website Scraping

```python
# Parse portfolio website
extracted_data, confidence = parser.parse_portfolio("https://johndoe.dev")

# Automatic section detection
# Contact info extraction (email, phone, social links)
# LLM-powered content parsing
```

#### Scraping Methods

**Primary: Selenium**
- Handles JavaScript rendering
- Supports dynamic content
- Confidence: 90%

**Fallback: BeautifulSoup**
- Static content only
- Lighter weight
- Confidence: 75%

### 3. Complete Parsing Workflow

```python
# Full workflow with validation
result = parser.parse_complete_workflow({
    "source_type": "pdf",
    "file_path": "/path/to/resume.pdf"
})

print(result)
# {
#   "success": True,
#   "master_cv": MasterCV(...),
#   "confidence_score": 0.92,
#   "validation": {...},
#   "missing_fields": [...],
#   "warnings": [...]
# }
```

## Data Extraction Process

### Step 1: Raw Text Extraction

- PDF text extracted with pdfplumber or PyPDF2
- Sections automatically detected
- Text cleaned and normalized

### Step 2: LLM-Powered Extraction

LLM receives prompt to extract:
- Personal information (name, email, phone, location)
- Social profiles (LinkedIn, GitHub, portfolio)
- Professional summary
- Work experience (company, title, dates, achievements)
- Education (degree, institution, graduation date)
- Skills (with proficiency levels)
- Certifications
- Projects
- Languages
- Awards and achievements

**Confidence Score:** Based on data completeness

### Step 3: Master CV Structuring

Extracted data is passed to LLM to structure into Master CV schema:

```json
{
  "personal_info": { ... },
  "professional_summary": { ... },
  "experience": [ ... ],
  "education": [ ... ],
  "skills": [ ... ],
  "languages": [ ... ],
  "certifications": [ ... ],
  "projects": [ ... ],
  "achievements": [ ... ],
  "metadata": { ... }
}
```

### Step 4: Validation & Quality Scoring

- Check required fields present
- Validate email/phone formats
- Verify date consistency
- Calculate confidence score (0-1)
- Identify missing fields

## LLM Prompts

### Initial Parsing Prompt

Extracts data from raw text with detailed instructions for:
- Personal information extraction
- Section identification
- Contact information parsing
- Date format standardization

### Master CV Structuring Prompt

Converts extracted data to Master CV schema with:
- Field mapping rules
- Enum value constraints
- Format specifications
- Error handling

### Validation Prompt

Checks data quality with scoring for:
- Accuracy
- Completeness
- Categorization
- Consistency
- Contact information

## Usage Examples

### Basic PDF Parsing

```python
from cv_customizer.agents.parser_agent import ParserAgent
from cv_customizer.agents.llm_provider import LLMProviderFactory

provider = LLMProviderFactory.get_provider("gemini")
parser = ParserAgent(provider=provider)

# Parse and get result
result = parser.parse_complete_workflow({
    "source_type": "pdf",
    "file_path": "john_resume.pdf"
})

if result["success"]:
    master_cv = result["master_cv"]
    print(f"Name: {master_cv.personal_info.first_name}")
    print(f"Email: {master_cv.personal_info.email}")
    print(f"Skills: {[s.name for s in master_cv.skills]}")
    print(f"Confidence: {result['confidence_score']}")
else:
    print(f"Error: {result['errors']}")
```

### Portfolio Website Parsing

```python
result = parser.parse_complete_workflow({
    "source_type": "portfolio",
    "portfolio_url": "https://johndoe.dev"
})

master_cv = result["master_cv"]
```

### Manual Step-by-Step

```python
# Step 1: Extract data
extracted, extraction_conf = parser.parse_pdf("resume.pdf")
print(f"Extraction confidence: {extraction_conf}")

# Step 2: Generate Master CV
master_cv, struct_conf = parser.generate_master_cv(extracted)
print(f"Structuring confidence: {struct_conf}")

# Step 3: Fill missing fields
master_cv = parser.fill_missing_fields(master_cv)

# Step 4: Validate quality
validation = parser.validate_cv_quality(master_cv)
print(f"Validation: {validation}")
```

## Confidence Scoring

Confidence score (0-1) based on:

| Factor | Weight | Details |
|--------|--------|---------|
| Extraction confidence | 40% | PDF/scraping success |
| Data completeness | 30% | Required fields present |
| Data quality | 20% | Validation checks passed |
| Consistency | 10% | Data consistency |

**Example:**
- PDF extraction: 0.95 (pdfplumber)
- Data structuring: 0.90 (most fields filled)
- Average confidence: **(0.95 + 0.90) / 2 = 0.925**

## Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| FileNotFoundError | PDF doesn't exist | Check file path |
| UnsupportedFormat | Wrong file type | Use PDF format |
| ScrapeError | Website unreachable | Check URL and network |
| JSONParseError | LLM response malformed | Retry or use fallback |
| ValidationError | Missing required fields | Manual data entry needed |

### Error Recovery

```python
try:
    result = parser.parse_complete_workflow(input_data)
except FileNotFoundError:
    print("Resume file not found")
except ValueError as e:
    print(f"Invalid input: {e}")
except Exception as e:
    print(f"Parsing failed: {e}")
```

## Supported File Types

### PDF Formats
- Standard PDFs (text-based)
- Scanned PDFs (if OCR available)
- Multi-page documents
- Complex layouts

### Website Types
- Static portfolio sites
- Dynamic sites (Selenium)
- JavaScript-rendered content
- LinkedIn profiles (basic info)

## Configuration

### Environment Variables

```bash
# Primary LLM provider for parsing
PARSER_LLM_PROVIDER=gemini

# Extraction parameters
PDF_EXTRACTION_TIMEOUT=30
SCRAPING_TIMEOUT=10

# Selenium options
SELENIUM_HEADLESS=true
SELENIUM_BROWSER=chrome

# Ollama (for local processing)
OLLAMA_BASE_URL=http://localhost:11434
```

### Agent Parameters

```python
# Temperature (creativity)
# Lower = more deterministic
parser_config = {
    "temperature": 0.3,      # Conservative for extraction
    "max_tokens": 4000,      # Enough for full extraction
    "timeout": 30,           # Processing timeout
}
```

## Performance

### Processing Times

| Source | Method | Time | Confidence |
|--------|--------|------|-----------|
| PDF (1 page) | pdfplumber | ~2s | 0.95 |
| PDF (10 pages) | pdfplumber | ~5s | 0.95 |
| Portfolio | Selenium | ~10s | 0.90 |
| Portfolio | BeautifulSoup | ~3s | 0.75 |

### Optimization Tips

1. **Reduce PDF complexity**: Extract only needed pages
2. **Use fast providers**: Groq for extraction (free tier)
3. **Enable caching**: Cache LLM responses
4. **Batch processing**: Process multiple files efficiently

## Integration with Other Agents

### With Job Search Agent

```python
# Parser output → Job Search Agent
result = parser.parse_complete_workflow(input_data)
master_cv = result["master_cv"]

# Use in job search
from cv_customizer.agents.job_search_agent import JobSearchAgent

job_provider = LLMProviderFactory.get_provider("claude")
job_agent = JobSearchAgent(provider=job_provider)

jobs = job_agent.search_jobs(
    keywords=[s.name for s in master_cv.skills]
)
```

### With CV Tailor Agent

```python
# Parser output → CV Tailor Agent
from cv_customizer.agents.cv_tailor_agent import CVTailorAgent

tailor_provider = LLMProviderFactory.get_provider("chatgpt")
tailor_agent = CVTailorAgent(provider=tailor_provider)

tailored = tailor_agent.tailor_cv_content(
    master_cv=master_cv,
    job_data=job_listing
)
```

## Testing

```python
# Test with sample PDF
from cv_customizer.agents.parser_agent import ParserAgent

provider = LLMProviderFactory.get_provider("gemini")
parser = ParserAgent(provider=provider)

# Parse example resume
result = parser.parse_complete_workflow({
    "source_type": "pdf",
    "file_path": "examples/sample_resume.pdf"
})

assert result["success"]
assert result["master_cv"] is not None
assert result["confidence_score"] > 0.5
print("✅ Parser Agent test passed")
```

## File Reference

- **Parser Agent**: `cv_customizer/agents/parser_agent.py`
- **PDF Extractor**: `cv_customizer/utils/pdf_extractor.py`
- **Portfolio Scraper**: `cv_customizer/utils/portfolio_scraper.py`
- **Extraction Prompts**: `cv_customizer/utils/cv_prompts.py`
- **Master CV Schema**: `cv_customizer/models/master_cv.py`
- **CV Utilities**: `cv_customizer/utils/cv_utils.py`

## Next Steps

Feature 5: **Job Search & Filtering Agent** - Search jobs and filter by ATS score
