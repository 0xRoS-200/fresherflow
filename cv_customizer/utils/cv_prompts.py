"""LLM Prompts for CV Data Extraction and Structuring"""

from textwrap import dedent
from typing import Dict, List


class CVExtractionPrompts:
    """Collection of prompts for parsing CV data with LLMs"""

    @staticmethod
    def build_initial_parsing_prompt(raw_text: str) -> str:
        """Build prompt for initial CV data extraction"""
        return dedent(f"""
        Extract structured information from this resume/CV text.
        
        RESUME TEXT:
        {raw_text[:3000]}
        
        Please extract and structure the following information:
        
        1. PERSONAL INFORMATION:
           - Full name
           - Email address (if present)
           - Phone number (if present)
           - Location (City, State, Country)
           - LinkedIn profile URL (if present)
           - GitHub profile URL (if present)
           - Portfolio website URL (if present)
           - Twitter handle (if present)
        
        2. PROFESSIONAL HEADLINE:
           - Professional headline/title (one line summary)
           - Professional summary (2-3 sentences max)
        
        3. WORK EXPERIENCE:
           For each job, extract:
           - Company name
           - Job title
           - Employment type (full-time, part-time, contract, internship)
           - Start date (format: YYYY-MM)
           - End date (format: YYYY-MM, or "present")
           - Location
           - Job description/responsibilities (2-3 sentences)
           - Key achievements (bullet points)
           - Technologies/skills used
        
        4. EDUCATION:
           For each entry, extract:
           - Institution name
           - Degree type (Bachelor, Master, PhD, etc.)
           - Field of study
           - Graduation date (YYYY-MM)
           - GPA (if mentioned)
           - Notable activities or awards
        
        5. SKILLS:
           - List all skills mentioned
           - For each skill, estimate proficiency level (beginner, intermediate, advanced, expert)
           - Group by category (Programming Languages, Tools, Soft Skills, etc.)
        
        6. CERTIFICATIONS:
           For each certification:
           - Certification name
           - Issuing organization
           - Date obtained (YYYY-MM)
           - Expiration date (if applicable)
           - Credential URL (if present)
        
        7. PROJECTS:
           For each project:
           - Project name
           - Brief description
           - Technologies used
           - Project URL or GitHub link (if present)
           - Key achievements/results
        
        8. OTHER INFORMATION:
           - Languages spoken (with proficiency levels)
           - Awards and achievements
           - Publications
           - Volunteering experience
           - Any other relevant information
        
        Return as a clean, well-formatted JSON object with extracted data.
        If information is not present, use null values.
        Be thorough and extract all available information.
        """)

    @staticmethod
    def build_master_cv_structuring_prompt(extracted_data: str) -> str:
        """Build prompt for structuring into Master CV format"""
        return dedent(f"""
        Convert this extracted CV data into the Master CV JSON schema format.
        
        EXTRACTED DATA:
        {extracted_data[:2000]}
        
        MASTER CV SCHEMA REQUIREMENTS:
        
        {{
          "personal_info": {{
            "first_name": string,
            "last_name": string,
            "email": string (email format),
            "phone": string (with country code),
            "location": string,
            "linkedin_url": string or null,
            "github_url": string or null,
            "portfolio_url": string or null,
            "personal_website": string or null,
            "twitter_handle": string or null
          }},
          "professional_summary": {{
            "headline": string,
            "summary": string (20+ chars),
            "total_experience_years": number,
            "specialization": string or null,
            "key_achievements": array of strings or null
          }},
          "experience": [
            {{
              "company_name": string,
              "job_title": string,
              "employment_type": "full_time" | "part_time" | "contract" | "freelance" | "internship" | "temporary",
              "location": string or null,
              "start_date": "YYYY-MM" format,
              "end_date": "YYYY-MM" format or null,
              "is_current": boolean,
              "description": string,
              "achievements": array of strings,
              "skills_used": array of strings
            }}
          ],
          "education": [
            {{
              "institution": string,
              "degree": "bachelor" | "master" | "phd" | "diploma" | "certification" | "high_school",
              "field_of_study": string,
              "location": string or null,
              "start_date": "YYYY-MM" format,
              "graduation_date": "YYYY-MM" format,
              "gpa": number (0-4.0) or null,
              "activities": array of strings,
              "courses": array of strings
            }}
          ],
          "skills": [
            {{
              "name": string,
              "level": "beginner" | "intermediate" | "advanced" | "expert",
              "category": string,
              "years_of_experience": number or null
            }}
          ],
          "languages": [
            {{
              "name": string,
              "proficiency": "beginner" | "intermediate" | "advanced" | "expert",
              "native": boolean
            }}
          ],
          "certifications": [
            {{
              "name": string,
              "issuer": string,
              "issue_date": "YYYY-MM" format,
              "expiration_date": "YYYY-MM" format or null,
              "is_active": boolean,
              "credential_url": string or null
            }}
          ],
          "projects": [
            {{
              "name": string,
              "description": string,
              "start_date": "YYYY-MM" format or null,
              "end_date": "YYYY-MM" format or null,
              "is_current": boolean,
              "technologies_used": array of strings,
              "github_url": string or null,
              "key_achievements": array of strings
            }}
          ],
          "achievements": [
            {{
              "title": string,
              "description": string,
              "date": "YYYY-MM" format,
              "issuer": string or null
            }}
          ],
          "additional_sections": object with custom sections or null
        }}
        
        IMPORTANT RULES:
        1. Ensure all required fields are present (use null for missing)
        2. Keep dates in YYYY-MM format
        3. Employment type must be one of the specified values
        4. Proficiency levels must be one of the specified values
        5. is_current=true means end_date should be null
        6. Return VALID JSON that can be parsed
        7. Do not include markdown formatting, just raw JSON
        
        Return ONLY the JSON object, no explanation or markdown.
        """)

    @staticmethod
    def build_confidence_scoring_prompt(extracted_data: str, master_cv: str) -> str:
        """Build prompt for confidence scoring"""
        return dedent(f"""
        Evaluate the quality and completeness of this CV extraction.
        
        ORIGINAL DATA:
        {extracted_data[:1000]}
        
        STRUCTURED CV:
        {master_cv[:1000]}
        
        Rate the extraction on these criteria (1-10 scale):
        1. Accuracy of extracted data
        2. Completeness of required fields
        3. Proper field categorization
        4. Data consistency
        5. Contact information accuracy
        
        Return JSON:
        {{
          "accuracy_score": number (1-10),
          "completeness_score": number (1-10),
          "categorization_score": number (1-10),
          "consistency_score": number (1-10),
          "contact_accuracy_score": number (1-10),
          "overall_confidence": number (0-1),
          "missing_fields": array of strings,
          "issues": array of strings,
          "recommendations": array of strings
        }}
        
        Return ONLY valid JSON, no markdown.
        """)

    @staticmethod
    def build_missing_fields_prompt(master_cv: str) -> str:
        """Build prompt for identifying missing fields"""
        return dedent(f"""
        Analyze this Master CV and identify missing or incomplete fields.
        
        CV:
        {master_cv[:1000]}
        
        For each missing or incomplete field, suggest:
        1. What information is missing
        2. Why it's important
        3. How it should be formatted
        
        Return JSON:
        {{
          "missing_critical": array of strings,
          "missing_important": array of strings,
          "missing_optional": array of strings,
          "incomplete_fields": {{
            "field_name": "reason and how to complete"
          }},
          "suggestions": array of strings
        }}
        
        Return ONLY valid JSON, no markdown.
        """)


class DataValidationPrompts:
    """Prompts for validating extracted data"""

    @staticmethod
    def build_validation_prompt(cv_data: Dict) -> str:
        """Build prompt for data validation"""
        return dedent(f"""
        Validate this CV data for accuracy and consistency.
        
        CV DATA:
        {str(cv_data)[:1500]}
        
        Check for:
        1. Date consistency (end_date > start_date)
        2. Email format validity
        3. Phone format validity
        4. URL format validity
        5. Logical experience progression
        6. Reasonable skill counts
        7. Proper date formatting
        
        Return JSON:
        {{
          "is_valid": boolean,
          "errors": array of strings,
          "warnings": array of strings,
          "suggestions": array of strings,
          "validation_score": number (0-1)
        }}
        
        Return ONLY valid JSON.
        """)
