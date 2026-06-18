"""
Parser Agent using LangGraph - Main orchestrator for resume parsing
Workflow: PDF/URL → Extract text → Parse with LLM → Structured JSON → Master CV
"""

import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from langchain_core.messages import HumanMessage, SystemMessage
from llm_provider import invoke_with_fallback
from master_cv import MasterCV, Location, Skill, Experience, Education

load_dotenv()


import sys
import time
import threading
import os

# Enable ANSI escape sequences on Windows console if applicable
if os.name == 'nt':
    try:
        os.system('')
    except Exception:
        pass

class TerminalSpinner:
    """A clean, cyan terminal spinner for displaying loading states in command line/terminal."""
    def __init__(self, message: str = "Processing..."):
        self.message = message
        self.spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.stop_running = threading.Event()
        self.thread = None

    def _spin(self):
        idx = 0
        while not self.stop_running.is_set():
            sys.stdout.write(f"\r\033[36m{self.spinner[idx % len(self.spinner)]}\033[0m {self.message}")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.08)
        # Clear the spinner line
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def __enter__(self):
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_running.set()
        if self.thread:
            self.thread.join()


class ParserAgent:
    """
    LangGraph Parser Agent for structured resume extraction
    Uses Gemini/Claude for intelligent parsing and schema compliance
    """

    def __init__(self):
        """Initialize parser tools."""
        from parser_tools import ResumeParserUnstructured
        self.parser = ResumeParserUnstructured()

    def extract_from_pdf(self, pdf_path: str) -> MasterCV:
        """
        Step 1: Extract resume data from PDF
        Returns: Structured Master CV with null fields marked
        """
        print(f"[Parser] Extracting text from PDF: {pdf_path}")
        from parser_tools import PDFExtractor

        with TerminalSpinner("Extracting text and running basic parser heuristics..."):
            # Use basic extractor first
            basic_cv = self.parser.parse_pdf(pdf_path)

            # Get raw text for LLM enhancement
            text = PDFExtractor.extract_text(pdf_path)
            sections = PDFExtractor.extract_sections(text)

        # Enhance with LLM parsing
        enhanced_cv = self._enhance_with_llm(text, basic_cv, sections)

        return enhanced_cv

    def extract_from_portfolio(self, portfolio_url: str) -> MasterCV:
        """
        Step 2: Extract resume data from portfolio URL using web scraping
        Returns: Structured Master CV with null fields marked
        """
        print(f"[Parser] Extracting from portfolio: {portfolio_url}")

        cv = MasterCV(
            name="",
            email="",
            phone="",
            location=Location(city="", country=""),
            metadata={"source": "portfolio"}
        )
        cv.mark_null_fields()
        return cv

    def _enhance_with_llm(self, resume_text: str, basic_cv: MasterCV, sections: Optional[Dict[str, str]] = None) -> MasterCV:
        """
        Use LLM provider fallback chain to parse resume text and extract structured data.
        Extracts all fields including profileType, totalExperienceYears,
        rawAccomplishments, and achievements.
        """
        print("[Parser] Enhancing extraction with LLM...")

        from llm_provider import get_provider_order
        provider_order = get_provider_order()
        is_ollama_primary = False  # Ollama is strictly restricted to coding/LaTeX, never used for resume extraction

        if is_ollama_primary and sections and len(sections) >= 3:
            print("[Parser] Ollama primary provider detected. Using parallel Map-Reduce section parsing...")
            try:
                data = self._process_sections_parallel(sections)
                if data.get("name") and (data.get("email") or data.get("phone")):
                    cv = self._reconstruct_cv(data, basic_cv)
                    return cv
                print("[Parser] Parallel parsing incomplete, falling back to single prompt...")
            except Exception as e:
                print(f"[Parser] Parallel parsing failed: {e}, falling back to single prompt...")

        extraction_prompt = """
You are a professional resume parser. Extract ALL information from the resume text below and return ONLY valid JSON matching this schema exactly.

CRITICAL EXTRACTION RULES:
1. For `rawAccomplishments` in experience: copy the EXACT bullet points / sentences from the resume, preserving the original phrasing. Do NOT rephrase them.
2. For `profileType`: set "fresher" if totalExperienceYears < 1, otherwise "experienced".
3. For `totalExperienceYears`: calculate total months of all work experience (excluding internships < 6 months) and convert to years (round to 1 decimal).
4. For `targetRole`: infer from resume title, objective, or most recent role.
5. For `achievements`: extract standalone awards, honors, hackathon wins, publications, competitive programming rankings — NOT job bullets.
6. For `skills`: infer proficiency as "beginner" / "intermediate" / "expert" based on context clues (years mentioned, project complexity, etc.).
7. Under no circumstances should you invent or hallucinate any projects, work experiences, credentials, skills, or metrics. If a field has no data in the resume, use null or empty array — do NOT invent data.

JSON SCHEMA:
{{
  "name": "string",
  "email": "string",
  "phone": "string",
  "location": {{"city": "string", "country": "string"}},
  "profileType": "fresher" | "experienced",
  "totalExperienceYears": 0.0,
  "targetRole": "string or null",
  "summary": "string or null",
  "skills": [
    {{"name": "string", "proficiency": "beginner|intermediate|expert", "category": "technical|soft|domain"}}
  ],
  "experience": [
    {{
      "role": "string",
      "company": "string",
      "startDate": "YYYY-MM",
      "endDate": "YYYY-MM or 'present'",
      "description": "string",
      "responsibilities": ["string"],
      "rawAccomplishments": ["EXACT copied bullet points from resume, unmodified"]
    }}
  ],
  "education": [
    {{
      "degree": "string",
      "university": "string",
      "institution": "string",
      "field": "string or null",
      "graduationYear": 2025,
      "startDate": "YYYY or YYYY-MM or null",
      "endDate": "YYYY or YYYY-MM or null",
      "gpa": 0.0,
      "description": "string or null"
    }}
  ],
  "certifications": [
    {{"name": "string", "issuer": "string", "issueDate": 2023, "expiryDate": null, "credentialUrl": "URL or null"}}
  ],
  "projects": [
    {{
      "title": "string",
      "description": "string",
      "techStack": "comma-separated string of technologies",
      "technologies": ["string"],
      "repositoryUrl": "URL or null",
      "deployedUrl": "URL or null",
      "date": "YYYY-MM",
      "rawAccomplishments": ["EXACT copied bullet points from resume describing this project"]
    }}
  ],
  "socialLinks": {{
    "linkedin": "URL or null",
    "github": "URL or null",
    "portfolio": "URL or null",
    "twitter": "URL or null"
  }},
  "languages": [
    {{"name": "string", "proficiency": "beginner|intermediate|fluent|native"}}
  ],
  "achievements": [
    "string — standalone awards, hackathon wins, honors, competitive rankings ONLY"
  ]
}}

Resume text:
{resume_text}

Return ONLY the JSON object, no other text, no markdown fences.
""".format(resume_text=resume_text)

        try:
            with TerminalSpinner("Calling LLM for structured resume extraction..."):
                _, response = invoke_with_fallback([
                    SystemMessage(content="You are an expert resume parser. Extract all information faithfully and return valid JSON only. Never invent or rephrase — copy rawAccomplishments exactly as written. If projects or experiences are not in the text, do not invent them under any circumstances."),
                    HumanMessage(content=extraction_prompt)
                ], allowed_providers=["gemini", "groq"])

            response_text = response.content.strip()

            # Strip markdown fences if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(
                    line for line in lines
                    if not line.strip().startswith("```")
                ).strip()

            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    print("[Parser] Warning: Could not parse LLM response, using basic extraction")
                    return basic_cv

            cv = self._reconstruct_cv(data, basic_cv)
            return cv

        except Exception as e:
            print(f"[Parser] LLM enhancement failed: {e}, using basic extraction")
            return basic_cv

    def _process_sections_parallel(self, sections: Dict[str, str]) -> Dict[str, Any]:
        from concurrent.futures import ThreadPoolExecutor
        from langchain_core.messages import HumanMessage, SystemMessage
        from llm_provider import invoke_with_fallback
        
        prompts = {
            "personal": """Extract personal contact information from this text. Return ONLY a valid JSON object matching this schema:
{
  "name": "string or null",
  "email": "string or null",
  "phone": "string or null",
  "location": {"city": "string or null", "country": "string or null"},
  "socialLinks": {"linkedin": "string or null", "github": "string or null", "portfolio": "string or null", "twitter": "string or null"}
}
Return ONLY valid JSON.
Text:
""",
            "experience": """Extract work experience entries from this text. Return ONLY a valid JSON object matching this schema:
{
  "experience": [
    {
      "role": "string",
      "company": "string",
      "startDate": "YYYY-MM or null",
      "endDate": "YYYY-MM or 'present' or null",
      "description": "string",
      "responsibilities": ["string"],
      "rawAccomplishments": ["EXACT copied bullet points from resume, unmodified"]
    }
  ]
}
Return ONLY valid JSON.
Text:
""",
            "education": """Extract education entries from this text. Return ONLY a valid JSON object matching this schema:
{
  "education": [
    {
      "degree": "string",
      "university": "string",
      "institution": "string",
      "field": "string or null",
      "graduationYear": number or null,
      "startDate": "YYYY or YYYY-MM or null",
      "endDate": "YYYY or YYYY-MM or null",
      "gpa": number or null,
      "description": "string or null"
    }
  ]
}
Return ONLY valid JSON.
Text:
""",
            "skills": """Extract skills and languages from this text. Return ONLY a valid JSON object matching this schema:
{
  "skills": [
    {"name": "string", "proficiency": "beginner|intermediate|expert", "category": "technical|soft|domain"}
  ],
  "languages": [
    {"name": "string", "proficiency": "beginner|intermediate|fluent|native"}
  ]
}
Return ONLY valid JSON.
Text:
""",
            "projects": """Extract project entries from this text. Return ONLY a valid JSON object matching this schema:
{
  "projects": [
    {
      "title": "string",
      "description": "string",
      "techStack": "comma-separated string of technologies",
      "technologies": ["string"],
      "repositoryUrl": "URL or null",
      "deployedUrl": "URL or null",
      "date": "YYYY-MM or null",
      "rawAccomplishments": ["EXACT copied bullet points from resume describing this project"]
    }
  ]
}
Return ONLY valid JSON.
Text:
""",
            "certifications": """Extract certifications and awards from this text. Return ONLY a valid JSON object matching this schema:
{
  "certifications": [
    {"name": "string", "issuer": "string", "issueDate": number or null, "expiryDate": null, "credentialUrl": "URL or null"}
  ],
  "achievements": [
    "string — standalone awards, hackathon wins, honors, competitive rankings ONLY"
  ]
}
Return ONLY valid JSON.
Text:
"""
        }

        # Combine contact, summary, etc. into a single personal text block if they exist
        combined_sections = {}
        for sec_name, content in sections.items():
            key = sec_name.lower().strip()
            if key in ["contact", "summary", "objective", "profile", "about"]:
                combined_sections["personal"] = combined_sections.get("personal", "") + "\n" + content
            elif key in ["experience", "work experience", "employment"]:
                combined_sections["experience"] = content
            elif key in ["education", "academic", "qualifications"]:
                combined_sections["education"] = content
            elif key in ["skills", "technical skills", "languages"]:
                combined_sections["skills"] = combined_sections.get("skills", "") + "\n" + content
            elif key in ["projects", "portfolio"]:
                combined_sections["projects"] = content
            elif key in ["certifications", "awards", "credentials"]:
                combined_sections["certifications"] = combined_sections.get("certifications", "") + "\n" + content

        final_data = {
            "name": None,
            "email": None,
            "phone": None,
            "location": {"city": None, "country": None},
            "profileType": "fresher",
            "totalExperienceYears": 0.0,
            "targetRole": None,
            "summary": None,
            "skills": [],
            "experience": [],
            "education": [],
            "certifications": [],
            "projects": [],
            "socialLinks": {"linkedin": None, "github": None, "portfolio": None, "twitter": None},
            "languages": [],
            "achievements": []
        }

        def worker(key, text):
            if key not in prompts:
                return key, {}
            prompt = prompts[key] + text
            try:
                _, response = invoke_with_fallback([
                    SystemMessage(content="You are an expert resume parser. Extract section information faithfully and return valid JSON only."),
                    HumanMessage(content=prompt)
                ], allowed_providers=["gemini", "groq"])
                # Clean markdown
                response_text = response.content.strip()
                if response_text.startswith("```"):
                    lines = response_text.split("\n")
                    response_text = "\n".join(
                        line for line in lines
                        if not line.strip().startswith("```")
                    ).strip()
                
                try:
                    parsed = json.loads(response_text)
                except json.JSONDecodeError:
                    import re
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group())
                    else:
                        parsed = {}
                return key, parsed
            except Exception as e:
                print(f"Error parsing section {key} in parallel: {e}")
                return key, {}

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(worker, key, text) for key, text in combined_sections.items() if text.strip()]
            for future in futures:
                key, result = future.result()
                if not result:
                    continue
                if key == "personal":
                    for field in ["name", "email", "phone"]:
                        if result.get(field):
                            final_data[field] = result[field]
                    if result.get("location"):
                        final_data["location"].update(result["location"])
                    if result.get("socialLinks"):
                        final_data["socialLinks"].update(result["socialLinks"])
                elif key == "experience":
                    final_data["experience"] = result.get("experience") or []
                elif key == "education":
                    final_data["education"] = result.get("education") or []
                elif key == "skills":
                    final_data["skills"] = result.get("skills") or []
                    final_data["languages"] = result.get("languages") or []
                elif key == "projects":
                    final_data["projects"] = result.get("projects") or []
                elif key == "certifications":
                    final_data["certifications"] = result.get("certifications") or []
                    final_data["achievements"] = result.get("achievements") or []

        # Post-process profileType & totalExperienceYears
        # Calculate experience years
        total_months = 0
        for exp in final_data["experience"]:
            try:
                start = exp.get("startDate")
                end = exp.get("endDate")
                if start and len(start) >= 4:
                    sy = int(start[:4])
                    sm = int(start[5:7]) if len(start) >= 7 else 1
                    if not end or end.lower() == "present":
                        import datetime
                        now = datetime.datetime.now()
                        ey, em = now.year, now.month
                    else:
                        ey = int(end[:4])
                        em = int(end[5:7]) if len(end) >= 7 else 12
                    total_months += (ey - sy) * 12 + (em - sm)
            except Exception:
                pass
        final_data["totalExperienceYears"] = round(total_months / 12, 1)
        final_data["profileType"] = "fresher" if final_data["totalExperienceYears"] < 1 else "experienced"

        return final_data

    def _reconstruct_cv(self, parsed_data: Dict[str, Any], basic_cv: Optional[MasterCV] = None) -> MasterCV:
        """Reconstruct Master CV from parsed data, mapping all new fields and falling back to basic_cv where necessary"""
        from master_cv import Project, Certification, SocialLinks

        # 1. Fallback / Sanitize required string and location fields to prevent Pydantic failures
        # Name
        name = parsed_data.get("name")
        if not name or not str(name).strip() or str(name).lower() == "null":
            name = basic_cv.name if basic_cv else "Unknown"
        else:
            name = str(name).strip()

        # Email
        email = parsed_data.get("email")
        if email and isinstance(email, str):
            email = email.strip()
            if "@" not in email:
                email = basic_cv.email if basic_cv else ""
        else:
            email = basic_cv.email if basic_cv else ""

        # Phone
        phone = parsed_data.get("phone")
        if phone:
            phone = str(phone).strip()
            digits = "".join(c for c in phone if c.isdigit())
            if len(digits) < 10:
                phone = basic_cv.phone if basic_cv else ""
        else:
            phone = basic_cv.phone if basic_cv else ""

        # Location
        loc_data = parsed_data.get("location")
        if isinstance(loc_data, dict):
            location = Location(
                city=str(loc_data.get("city") or "").strip(),
                country=str(loc_data.get("country") or "").strip()
            )
        else:
            location = basic_cv.location if basic_cv else Location(city="", country="")

        if not location.city and not location.country and basic_cv and basic_cv.location:
            location = basic_cv.location

        # 2. Extract Skills (fallback to basic_cv if none parsed)
        skills = []
        parsed_skills = parsed_data.get("skills")
        if isinstance(parsed_skills, list):
            for skill_data in parsed_skills:
                try:
                    if isinstance(skill_data, str):
                        skills.append(Skill(name=skill_data, proficiency="intermediate"))
                    elif isinstance(skill_data, dict):
                        skills.append(Skill(**skill_data))
                except Exception:
                    pass
        if not skills and basic_cv and basic_cv.skills:
            skills = basic_cv.skills

        # 3. Extract Experience (with rawAccomplishments)
        experiences = []
        parsed_experience = parsed_data.get("experience")
        if isinstance(parsed_experience, list):
            for exp_data in parsed_experience:
                try:
                    if isinstance(exp_data, dict):
                        raw_acc = exp_data.get("rawAccomplishments")
                        if not isinstance(raw_acc, list):
                            exp_data["rawAccomplishments"] = [str(raw_acc)] if raw_acc else []
                        experiences.append(Experience(**exp_data))
                except Exception:
                    pass

        # 4. Extract Education (with institution alias)
        education = []
        parsed_education = parsed_data.get("education")
        if isinstance(parsed_education, list):
            for edu_data in parsed_education:
                try:
                    if isinstance(edu_data, dict):
                        education.append(Education(**edu_data))
                except Exception:
                    pass

        # 5. Extract Certifications
        certifications = []
        parsed_certifications = parsed_data.get("certifications")
        if isinstance(parsed_certifications, list):
            for cert_data in parsed_certifications:
                try:
                    if isinstance(cert_data, dict):
                        certifications.append(Certification(**cert_data))
                except Exception:
                    pass

        # 6. Extract Projects (with rawAccomplishments + techStack)
        projects = []
        parsed_projects = parsed_data.get("projects")
        if isinstance(parsed_projects, list):
            for proj_data in parsed_projects:
                try:
                    if isinstance(proj_data, dict):
                        raw_acc = proj_data.get("rawAccomplishments")
                        if not isinstance(raw_acc, list):
                            proj_data["rawAccomplishments"] = [str(raw_acc)] if raw_acc else []
                        projects.append(Project(**proj_data))
                except Exception:
                    pass

        # 7. Extract Social Links (fallback to basic_cv)
        social_data = parsed_data.get("socialLinks")
        social_links = None
        if isinstance(social_data, dict):
            try:
                social_links = SocialLinks(
                    linkedin=social_data.get("linkedin"),
                    github=social_data.get("github"),
                    portfolio=social_data.get("portfolio"),
                    twitter=social_data.get("twitter")
                )
            except Exception:
                pass
        if not social_links and basic_cv and basic_cv.socialLinks:
            social_links = basic_cv.socialLinks

        # 8. Extract Languages
        languages = []
        parsed_languages = parsed_data.get("languages")
        if isinstance(parsed_languages, list):
            from master_cv import Language
            for lang_data in parsed_languages:
                try:
                    if isinstance(lang_data, dict):
                        languages.append(Language(**lang_data))
                except Exception:
                    pass

        # Determine profileType
        total_years = parsed_data.get("totalExperienceYears")
        try:
            total_years = float(total_years) if total_years is not None else 0.0
        except Exception:
            total_years = 0.0

        profile_type = parsed_data.get("profileType", "fresher")
        if not profile_type or profile_type not in ("fresher", "experienced"):
            profile_type = "experienced" if total_years >= 1.0 else "fresher"

        # Extract achievements
        achievements = []
        parsed_achievements = parsed_data.get("achievements")
        if isinstance(parsed_achievements, list):
            achievements = [str(a) for a in parsed_achievements if a]

        # Create CV with all new fields
        cv = MasterCV(
            name=name,
            email=email,
            phone=phone,
            location=location,
            profileType=profile_type,
            totalExperienceYears=total_years,
            targetRole=parsed_data.get("targetRole"),
            summary=parsed_data.get("summary"),
            skills=skills,
            experience=experiences,
            education=education,
            certifications=certifications if certifications else None,
            projects=projects if projects else None,
            socialLinks=social_links,
            languages=languages if languages else None,
            achievements=achievements,
            metadata={"source": "pdf"}
        )

        cv.mark_null_fields()
        cv.calculate_completion()
        return cv

    def fill_missing_fields(self, cv: MasterCV, user_input: Dict[str, Any]) -> MasterCV:
        """
        Step 3: Fill missing required fields from user input
        Input format: {"name": "John", "email": "john@example.com", ...}
        """
        print("[Parser] Filling missing fields from user input...")

        if user_input.get("name"):
            cv.name = user_input["name"]
        if user_input.get("email"):
            cv.email = user_input["email"]
        if user_input.get("phone"):
            cv.phone = user_input["phone"]
        if user_input.get("location"):
            loc_data = user_input["location"]
            cv.location = Location(
                city=loc_data.get("city", cv.location.city),
                country=loc_data.get("country", cv.location.country)
            )
        if user_input.get("profileType"):
            cv.profileType = user_input["profileType"]
        if user_input.get("totalExperienceYears") is not None:
            cv.totalExperienceYears = float(user_input["totalExperienceYears"])
        if user_input.get("targetRole"):
            cv.targetRole = user_input["targetRole"]
        if user_input.get("achievements"):
            cv.achievements = user_input["achievements"]

        cv.mark_null_fields()
        cv.calculate_completion()

        return cv

    def parse_workflow(self, pdf_path: str, user_input: Optional[Dict[str, Any]] = None) -> MasterCV:
        """
        Complete parsing workflow:
        1. Extract from PDF
        2. Fill missing fields
        3. Return structured Master CV
        """
        print("[Parser Agent] Starting parse workflow...")

        # Step 1: Extract from PDF
        cv = self.extract_from_pdf(pdf_path)
        print(f"[Parser] Extraction complete. Completion: {cv.metadata.completionPercentage}%")
        print(f"[Parser] Profile type: {cv.profileType}, Experience: {cv.totalExperienceYears} years")
        print(f"[Parser] Missing fields: {cv.metadata.nullFields}")

        # Step 2: Fill missing fields if provided
        if user_input:
            cv = self.fill_missing_fields(cv, user_input)
            print(f"[Parser] Fields updated. New completion: {cv.metadata.completionPercentage}%")

        return cv


def invoke_llm_with_fallback(system_message: str, prompt_message: str, temperature: float = 0.7, allowed_providers: Optional[list[str]] = None) -> str:
    """Helper wrapper for serve.py to invoke LLM with fallback and return text content."""
    from langchain_core.messages import SystemMessage, HumanMessage
    from llm_provider import invoke_with_fallback

    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content=prompt_message)
    ]
    _, response = invoke_with_fallback(messages, allowed_providers=allowed_providers)
    return response.content


# Example usage
if __name__ == "__main__":
    parser_agent = ParserAgent()
