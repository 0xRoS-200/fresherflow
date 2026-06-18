"""LLM Prompts for Job Search and ATS Analysis"""

from textwrap import dedent
from typing import Dict


class JobSearchPrompts:
    """Prompts for job searching and metadata extraction"""

    @staticmethod
    def build_job_metadata_extraction_prompt(job_description: str) -> str:
        """Build prompt to extract structured metadata from job description"""
        return dedent("""
        Extract structured job metadata from the job description provided at the end.
        
        Extract and structure the following:
        
        1. BASIC INFO:
           - Job title
           - Company name
           - Job level (entry, mid, senior, lead, director, c-level)
           - Employment type (full-time, part-time, contract, remote)
           - Location(s) (remote, on-site, hybrid)
        
        2. COMPENSATION:
           - Salary range (min and max)
           - Currency
           - Salary period (annual, hourly, project)
           - Additional compensation (bonus, stock options, benefits)
        
        3. REQUIREMENTS:
           - Required skills (technical)
           - Required experience (years)
           - Required education level (high school, bachelor, master, phd)
           - Required certifications
           - Required languages
        
        4. PREFERRED QUALIFICATIONS:
           - Preferred skills
           - Preferred experience (years)
           - Preferred certifications
           - Preferred qualifications
        
        5. RESPONSIBILITIES:
           - Main responsibilities (top 5)
           - Team information (team size, reporting structure)
           - Success metrics
        
        6. BENEFITS & PERKS:
           - Health insurance
           - Retirement plan
           - Remote work options
           - Professional development
           - Other benefits
        
        7. METADATA:
           - Job posting URL (if available)
           - Posted date (if available)
           - Application deadline (if available)
           - Hiring team info (if available)
        
        Return as clean, well-formatted JSON with extracted data.
        If information is not present, use null values.
        Be thorough and extract all available information.

        JOB DESCRIPTION TO ANALYZE:
        {job_description}
        """).format(job_description=job_description)

    @staticmethod
    def build_keyword_extraction_prompt(job_requirements: str, cv_keywords: str) -> str:
        """Build prompt to extract keywords for ATS matching"""
        return dedent("""
        Extract and analyze keywords from job requirements and CV provided at the end.
        
        For each of the following categories, extract keywords:
        
        1. TECHNICAL SKILLS:
           - Programming languages
           - Frameworks and libraries
           - Tools and platforms
           - Databases
           - Cloud services
        
        2. SOFT SKILLS:
           - Communication styles
           - Leadership types
           - Problem-solving approaches
           - Collaboration styles
        
        3. EXPERIENCE TYPES:
           - Industry experience
           - Domain experience
           - Project types
           - Team sizes
        
        4. CERTIFICATIONS & CREDENTIALS:
           - Certifications
           - Degrees
           - Training
           - Awards
        
        Return JSON:
        {{
          "required_keywords": {{
            "technical_skills": [...],
            "soft_skills": [...],
            "experience": [...],
            "certifications": [...]
          }},
          "cv_keywords": {{
            "technical_skills": [...],
            "soft_skills": [...],
            "experience": [...],
            "certifications": [...]
          }},
          "matched_keywords": [...],
          "missing_keywords": [...],
          "match_percentage": number (0-100)
        }}
        
        Return ONLY valid JSON, no markdown.

        JOB REQUIREMENTS:
        {job_requirements}
        
        CV KEYWORDS:
        {cv_keywords}
        """).format(job_requirements=job_requirements, cv_keywords=cv_keywords)

    @staticmethod
    def build_ats_analysis_prompt(cv_text: str, job_description: str) -> str:
        """Build prompt for comprehensive ATS analysis"""
        return dedent("""
        Perform comprehensive ATS (Applicant Tracking System) analysis comparing CV to job.
        
        Analyze:
        
        1. KEYWORD MATCHING:
           - Match CV skills to job requirements
           - Calculate percentage matched
           - Identify critical missing skills
        
        2. FORMAT COMPLIANCE:
           - Check if CV follows standard ATS format
           - Identify formatting issues
           - Suggest improvements
        
        3. EXPERIENCE ALIGNMENT:
           - Match CV experience to job requirements
           - Calculate experience match percentage
           - Assess relevance
        
        4. EDUCATION ALIGNMENT:
           - Match education to requirements
           - Check degree match
           - Assess relevance
        
        5. LANGUAGE & TERMINOLOGY:
           - Check for ATS-friendly language
           - Identify jargon match
           - Assess industry alignment
        
        6. SCORING:
           - Keyword match score (0-30)
           - Experience score (0-25)
           - Education score (0-15)
           - Format score (0-15)
           - Language score (0-15)
        
        Return JSON:
        {{
          "keyword_match": number (0-30),
          "experience_match": number (0-25),
          "education_match": number (0-15),
          "format_score": number (0-15),
          "language_score": number (0-15),
          "total_ats_score": number (0-100),
          "pass_ats_filter": boolean (score >= 75),
          "matched_keywords": [...],
          "missing_keywords": [...],
          "format_issues": [...],
          "recommendations": [...]
        }}
        
        Return ONLY valid JSON.

        CV TEXT:
        {cv_text}
        
        JOB DESCRIPTION:
        {job_description}
        """).format(cv_text=cv_text, job_description=job_description)

    @staticmethod
    def build_job_ranking_prompt(jobs_with_scores: str) -> str:
        """Build prompt for ranking multiple jobs"""
        return dedent("""
        Rank these jobs based on fit, growth potential, and alignment with CV.
        
        For each job, consider:
        
        1. ATS SCORE (0-100):
           - Higher is better
           - Minimum 75 to pass
        
        2. GROWTH POTENTIAL:
           - Career advancement opportunities
           - Skill development potential
           - Industry growth
        
        3. COMPANY FACTORS:
           - Company reputation
           - Stability
           - Culture fit (if available)
        
        4. COMPENSATION:
           - Salary competitiveness
           - Benefits package
           - Total compensation
        
        5. WORK ENVIRONMENT:
           - Remote work availability
           - Work-life balance indicators
           - Team size and dynamics
        
        Return JSON:
        {{
          "ranked_jobs": [
            {{
              "job_id": string,
              "rank": number,
              "ats_score": number (0-100),
              "growth_potential": number (0-10),
              "company_score": number (0-10),
              "compensation_score": number (0-10),
              "work_env_score": number (0-10),
              "total_fit_score": number (0-100),
              "recommendation": "high_priority" | "apply" | "consider" | "skip",
              "why": string
            }}
          ]
        }}
        
        Return ONLY valid JSON.

        JOBS WITH ATS SCORES:
        {jobs_with_scores}
        """).format(jobs_with_scores=jobs_with_scores)

    @staticmethod
    def build_job_search_query_prompt(cv_skills: str, experience_level: str) -> str:
        """Build prompt to generate job search queries"""
        return dedent("""
        Generate optimized job search queries based on CV.
        
        Generate search queries for major job portals:
        
        1. LINKEDIN SEARCH:
           - Build effective LinkedIn search filters
           - Keyword combinations
           - Location strategies
        
        2. INDEED SEARCH:
           - Generate Indeed search queries
           - Filter combinations
           - Location strategies
        
        3. GENERAL JOB BOARDS:
           - Generic job board queries
           - Niche board queries (if applicable)
        
        4. COMPANY SEARCH:
           - Target companies by industry
           - Tech stack matching
        
        Return JSON:
        {{
          "linkedin": {{
            "queries": [...],
            "filters": {{...}}
          }},
          "indeed": {{
            "queries": [...],
            "location_options": [...]
          }},
          "job_boards": [
            {{
              "board_name": string,
              "queries": [...]
            }}
          ],
          "target_companies": [...]
        }}
        
        Return ONLY valid JSON.

        CV SKILLS: {cv_skills}
        EXPERIENCE LEVEL: {experience_level}
        """).format(cv_skills=cv_skills, experience_level=experience_level)


class JobFilteringPrompts:
    """Prompts for filtering and prioritization"""

    @staticmethod
    def build_company_culture_assessment_prompt(company_info: str, cv_profile: str) -> str:
        """Build prompt to assess company culture fit"""
        return dedent("""
        Assess cultural fit between candidate and company.
        
        Analyze:
        1. Work environment match
        2. Values alignment
        3. Growth opportunities
        4. Team dynamics fit
        5. Work-life balance indicators
        
        Return JSON:
        {{
          "culture_fit_score": number (0-100),
          "work_env_match": number (0-10),
          "values_alignment": number (0-10),
          "growth_fit": number (0-10),
          "team_dynamics": number (0-10),
          "insights": array of strings
        }}

        COMPANY INFO:
        {company_info}
        
        CV PROFILE:
        {cv_profile}
        """).format(company_info=company_info, cv_profile=cv_profile)

    @staticmethod
    def build_salary_negotiation_prompt(job_salary: str, market_data: str, cv_level: str) -> str:
        """Build prompt for salary negotiation analysis"""
        return dedent("""
        Analyze salary offer and market positioning.
        
        Provide:
        1. Market rate comparison
        2. Negotiation strategy
        3. Acceptance factors
        
        Return JSON:
        {{
          "market_rate_low": number,
          "market_rate_high": number,
          "offered_salary": number,
          "negotiation_potential": number (0-100),
          "recommendation": string
        }}

        JOB SALARY: {job_salary}
        MARKET DATA: {market_data}
        CANDIDATE LEVEL: {cv_level}
        """).format(job_salary=job_salary, market_data=market_data, cv_level=cv_level)
