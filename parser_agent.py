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
from parser_tools import ResumeParserUnstructured, PDFExtractor, ContactInfoExtractor, SkillExtractor

load_dotenv()


class ParserAgent:
    """
    LangGraph Parser Agent for structured resume extraction
    Uses Claude for intelligent parsing and schema compliance
    """
    
    def __init__(self):
        """Initialize parser tools."""
        self.parser = ResumeParserUnstructured()
    
    def extract_from_pdf(self, pdf_path: str) -> MasterCV:
        """
        Step 1: Extract resume data from PDF
        Returns: Structured Master CV with null fields marked
        """
        print(f"[Parser] Extracting text from PDF: {pdf_path}")
        
        # Use basic extractor first
        basic_cv = self.parser.parse_pdf(pdf_path)
        
        # Get raw text for LLM enhancement
        text = PDFExtractor.extract_text(pdf_path)
        
        # Enhance with LLM parsing
        enhanced_cv = self._enhance_with_llm(text, basic_cv)
        
        return enhanced_cv
    
    def extract_from_portfolio(self, portfolio_url: str) -> MasterCV:
        """
        Step 2: Extract resume data from portfolio URL using web scraping
        Returns: Structured Master CV with null fields marked
        
        Note: Requires Selenium/BeautifulSoup setup
        """
        print(f"[Parser] Extracting from portfolio: {portfolio_url}")
        
        # This would use Selenium to scrape the portfolio
        # For MVP, return empty CV with null fields
        cv = MasterCV(
            name="",
            email="",
            phone="",
            location=Location(city="", country=""),
            metadata={"source": "portfolio"}
        )
        cv.mark_null_fields()
        return cv
    
    def _enhance_with_llm(self, resume_text: str, basic_cv: MasterCV) -> MasterCV:
        """
        Use Claude to parse resume text and extract structured data
        Ensures compliance with Master CV schema
        """
        print("[Parser] Enhancing extraction with LLM...")
        
        extraction_prompt = f"""
You are a resume parser. Extract all resume information and return ONLY valid JSON matching this schema:

{{
  "name": "string",
  "email": "string",
  "phone": "string",
  "location": {{"city": "string", "country": "string"}},
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
      "responsibilities": ["string"]
    }}
  ],
  "education": [
    {{
      "degree": "string",
      "university": "string",
      "field": "string or null",
      "graduationYear": "YYYY",
      "gpa": "float or null",
      "description": "string or null"
    }}
  ],
  "certifications": [
    {{"name": "string", "issuer": "string", "issueDate": "YYYY", "expiryDate": "YYYY or null"}}
  ],
  "projects": [
    {{"title": "string", "description": "string", "technologies": ["string"], "repositoryUrl": "URL or null", "date": "YYYY-MM"}}
  ],
  "socialLinks": {{
    "linkedin": "URL or null",
    "github": "URL or null",
    "portfolio": "URL or null",
    "twitter": "URL or null"
  }},
  "languages": [
    {{"name": "string", "proficiency": "beginner|intermediate|fluent|native"}}
  ]
}}

Resume text:
{resume_text}

Return ONLY the JSON object, no other text.
"""
        
        try:
            _, response = invoke_with_fallback([
                SystemMessage(content="You are an expert resume parser. Extract all information and return valid JSON."),
                HumanMessage(content=extraction_prompt)
            ])
            
            # Parse response
            response_text = response.content.strip()
            
            # Try to extract JSON from response
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to find JSON in response
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    print("[Parser] Warning: Could not parse LLM response, using basic extraction")
                    return basic_cv
            
            # Reconstruct Master CV from parsed data
            cv = self._reconstruct_cv(data)
            return cv
            
        except Exception as e:
            print(f"[Parser] LLM enhancement failed: {e}, using basic extraction")
            return basic_cv
    
    def _reconstruct_cv(self, parsed_data: Dict[str, Any]) -> MasterCV:
        """Reconstruct Master CV from parsed data"""
        from master_cv import Project, Certification, SocialLinks
        
        # Extract skills
        skills = []
        for skill_data in parsed_data.get("skills", []):
            try:
                skills.append(Skill(**skill_data))
            except:
                pass
        
        # Extract experience
        experiences = []
        for exp_data in parsed_data.get("experience", []):
            try:
                experiences.append(Experience(**exp_data))
            except:
                pass
        
        # Extract education
        education = []
        for edu_data in parsed_data.get("education", []):
            try:
                education.append(Education(**edu_data))
            except:
                pass

        # Extract certifications
        certifications = []
        for cert_data in parsed_data.get("certifications", []):
            try:
                certifications.append(Certification(**cert_data))
            except:
                pass

        # Extract projects
        projects = []
        for proj_data in parsed_data.get("projects", []):
            try:
                projects.append(Project(**proj_data))
            except:
                pass

        # Extract social links
        social_data = parsed_data.get("socialLinks", {})
        social_links = None
        if social_data:
            try:
                social_links = SocialLinks(
                    linkedin=social_data.get("linkedin"),
                    github=social_data.get("github"),
                    portfolio=social_data.get("portfolio"),
                    twitter=social_data.get("twitter")
                )
            except:
                pass
        
        # Create CV
        cv = MasterCV(
            name=parsed_data.get("name", ""),
            email=parsed_data.get("email", ""),
            phone=parsed_data.get("phone", ""),
            location=Location(**parsed_data.get("location", {"city": "", "country": ""})),
            summary=parsed_data.get("summary"),
            skills=skills,
            experience=experiences,
            education=education,
            certifications=certifications if certifications else None,
            projects=projects if projects else None,
            socialLinks=social_links,
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
        
        # Recalculate completion and null fields
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
        print(f"[Parser] Missing fields: {cv.metadata.nullFields}")
        
        # Step 2: Fill missing fields if provided
        if user_input:
            cv = self.fill_missing_fields(cv, user_input)
            print(f"[Parser] Fields updated. New completion: {cv.metadata.completionPercentage}%")
        
        return cv


def invoke_llm_with_fallback(system_message: str, prompt_message: str, temperature: float = 0.7) -> str:
    """Helper wrapper for serve.py to invoke LLM with fallback and return text content."""
    from langchain_core.messages import SystemMessage, HumanMessage
    from llm_provider import invoke_with_fallback
    
    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content=prompt_message)
    ]
    _, response = invoke_with_fallback(messages)
    return response.content


# Example usage
if __name__ == "__main__":
    parser_agent = ParserAgent()
    
    # Example: Parse a PDF
    # cv = parser_agent.parse_workflow("sample_resume.pdf")
    # print("\nExtracted Master CV:")
    # print(cv.model_dump_json(indent=2))
    
    # Example: Parse PDF + fill missing fields
    # user_input = {
    #     "name": "John Doe",
    #     "email": "john@example.com",
    #     "phone": "+1234567890",
    #     "location": {"city": "Bangalore", "country": "India"}
    # }
    # cv = parser_agent.parse_workflow("sample_resume.pdf", user_input)
