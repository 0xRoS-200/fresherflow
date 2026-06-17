"""
Parser Agent Tools - Extract resume data from PDF and portfolio URLs
"""

import json
import re
from typing import Optional, Dict, Any, List
import pdfplumber
from master_cv import MasterCV, Location, Skill, Experience, Education, Project, SocialLinks


class PDFExtractor:
    """Extract text and structure from PDF resumes"""
    
    @staticmethod
    def extract_text(pdf_path: str) -> str:
        """Extract all text from PDF file"""
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
                    text += "\n"
            return text.strip()
        except Exception as e:
            print(f"Error extracting PDF: {e}")
            return ""

    @staticmethod
    def extract_sections(text: str) -> Dict[str, str]:
        """
        Identify resume sections (Experience, Education, Skills, etc.)
        Returns dict mapping section name to section text
        """
        sections = {}
        
        # Common section headers
        section_patterns = {
            "summary": r"(summary|objective|profile|about)[\s\n]*:?",
            "experience": r"(experience|work experience|employment history|professional experience)[\s\n]*:?",
            "education": r"(education|academic|qualifications)[\s\n]*:?",
            "skills": r"(skills|technical skills|core competencies)[\s\n]*:?",
            "projects": r"(projects?|portfolio|work samples)[\s\n]*:?",
            "certifications": r"(certifications?|credentials?|licenses?)[\s\n]*:?",
            "languages": r"(languages?)[\s\n]*:?",
            "contact": r"(contact|contact information)[\s\n]*:?",
        }
        
        lines = text.split("\n")
        current_section = None
        section_content = {}
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if this line is a section header
            matched_section = None
            for section_name, pattern in section_patterns.items():
                if re.search(pattern, line_lower):
                    matched_section = section_name
                    break
            
            if matched_section:
                current_section = matched_section
                if current_section not in section_content:
                    section_content[current_section] = []
            elif current_section and line.strip():
                section_content[current_section].append(line.strip())
        
        # Convert lists to strings
        for section, lines_list in section_content.items():
            sections[section] = "\n".join(lines_list)
        
        return sections


class ContactInfoExtractor:
    """Extract contact information (name, email, phone, location)"""
    
    @staticmethod
    def extract_email(text: str) -> Optional[str]:
        """Extract first email address from text"""
        pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        match = re.search(pattern, text)
        return match.group(0) if match else None
    
    @staticmethod
    def extract_phone(text: str) -> Optional[str]:
        """Extract phone number from text"""
        # Match various phone formats: +1234567890, (123)456-7890, 123-456-7890, etc.
        patterns = [
            r"\+?\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}",
            r"\(\d{3}\)\s?\d{3}[-.]?\d{4}",
            r"\d{10,}",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return None
    
    @staticmethod
    def extract_name(text: str, contact_section: Optional[str] = None) -> Optional[str]:
        """
        Extract name - usually first or second line of resume
        or from contact section
        """
        # Try contact section first
        if contact_section:
            lines = contact_section.split("\n")
            for line in lines[:3]:  # Check first 3 lines
                cleaned = line.strip()
                if cleaned and len(cleaned) > 2 and len(cleaned) < 100:
                    return cleaned
        
        # Otherwise, try first line of entire text
        lines = text.split("\n")
        for line in lines[:5]:
            cleaned = line.strip()
            if cleaned and len(cleaned) > 2 and len(cleaned) < 100:
                # Filter out common headers
                if "linkedin" not in cleaned.lower() and "email" not in cleaned.lower():
                    return cleaned
        
        return None
    
    @staticmethod
    def extract_location(text: str) -> Optional[Location]:
        """
        Extract city and country from resume
        Look for location indicators in contact info or education sections
        """
        # Common location patterns
        india_cities = ["bangalore", "bengaluru", "hyderabad", "pune", "mumbai", "delhi", "delhi ncr", "noida", "gurgaon", "gurugram", "kolkata", "ahmed abad"]
        countries = ["india", "usa", "canada", "uk", "united kingdom", "australia", "germany", "singapore"]
        
        text_lower = text.lower()
        
        city = None
        country = None
        
        # Extract city
        for ind_city in india_cities:
            if ind_city in text_lower:
                city = ind_city.title()
                break
        
        # Extract country
        for ctry in countries:
            if ctry in text_lower:
                country = ctry.title()
                break
        
        if city or country:
            return Location(
                city=city or "Unknown",
                country=country or "India"
            )
        return None


class SkillExtractor:
    """Extract skills from resume text"""
    
    # Master skill dictionary
    SKILL_KEYWORDS = {
        "technical": [
            "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "ruby", "php",
            "react", "vue", "angular", "svelte", "node.js", "node", "express", "django", "flask",
            "spring", "spring boot", "fastapi", "dotnet", ".net",
            "sql", "mysql", "postgresql", "mongodb", "redis", "dynamodb", "firestore",
            "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd",
            "git", "github", "gitlab", "bitbucket",
            "html", "css", "scss", "tailwind", "bootstrap",
            "api", "rest", "graphql", "grpc", "websocket",
            "testing", "jest", "pytest", "unittest", "vitest",
            "linux", "unix", "windows", "macos",
            "machine learning", "deep learning", "nlp", "tensorflow", "pytorch", "scikit-learn",
            "data analysis", "pandas", "numpy", "matplotlib", "seaborn",
            "agile", "scrum", "kanban", "jira",
            "figma", "adobe xd", "sketch", "ui/ux", "ux design",
        ],
        "soft": [
            "communication", "teamwork", "leadership", "problem solving", "critical thinking",
            "project management", "time management", "organization", "adaptability",
            "collaboration", "creativity", "analytical", "strategic thinking",
        ]
    }
    
    @staticmethod
    def extract_skills(text: str) -> List[Skill]:
        """Extract skills from text and return structured Skill objects"""
        skills = []
        text_lower = text.lower()
        seen = set()
        
        # Check technical skills
        for skill_name in SkillExtractor.SKILL_KEYWORDS["technical"]:
            if skill_name in text_lower and skill_name not in seen:
                skills.append(Skill(
                    name=skill_name.title(),
                    proficiency="intermediate",  # Default, can be refined by LLM
                    category="technical"
                ))
                seen.add(skill_name)
        
        # Check soft skills
        for skill_name in SkillExtractor.SKILL_KEYWORDS["soft"]:
            if skill_name in text_lower and skill_name not in seen:
                skills.append(Skill(
                    name=skill_name.title(),
                    proficiency="intermediate",
                    category="soft"
                ))
                seen.add(skill_name)
        
        return skills


class SocialLinkExtractor:
    """Extract social media and portfolio links"""
    
    @staticmethod
    def extract_social_links(text: str) -> Optional[SocialLinks]:
        """Extract LinkedIn, GitHub, portfolio URLs"""
        linkedin = None
        github = None
        portfolio = None
        
        # LinkedIn pattern
        linkedin_match = re.search(r"linkedin\.com/in/[\w-]+", text)
        if linkedin_match:
            linkedin = f"https://{linkedin_match.group(0)}"
        
        # GitHub pattern
        github_match = re.search(r"github\.com/[\w-]+", text)
        if github_match:
            github = f"https://{github_match.group(0)}"
        
        # Portfolio pattern
        portfolio_match = re.search(r"(portfolio|website|personal site)[\s:]+([^\s]+)", text)
        if portfolio_match:
            portfolio = portfolio_match.group(2)
        
        if linkedin or github or portfolio:
            return SocialLinks(
                linkedin=linkedin,
                github=github,
                portfolio=portfolio
            )
        return None


class ResumeParserUnstructured:
    """Main parser combining all extractors"""
    
    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        self.contact_extractor = ContactInfoExtractor()
        self.skill_extractor = SkillExtractor()
        self.social_extractor = SocialLinkExtractor()
    
    def parse_pdf(self, pdf_path: str) -> MasterCV:
        """
        Parse PDF resume and return MasterCV object
        """
        # Extract text
        text = self.pdf_extractor.extract_text(pdf_path)
        if not text:
            raise ValueError(f"Could not extract text from {pdf_path}")
        
        # Extract sections
        sections = self.pdf_extractor.extract_sections(text)
        
        # Extract contact information
        name = self.contact_extractor.extract_name(text, sections.get("contact"))
        email = self.contact_extractor.extract_email(text)
        phone = self.contact_extractor.extract_phone(text)
        location = self.contact_extractor.extract_location(text)
        
        # Extract skills
        skills_section = sections.get("skills", "")
        combined_skills_text = f"{text} {skills_section}"
        skills = self.skill_extractor.extract_skills(combined_skills_text)
        
        # Extract social links
        social_links = self.social_extractor.extract_social_links(text)
        
        # Create Master CV
        cv = MasterCV(
            name=name or "Unknown",
            email=email or "",
            phone=phone or "",
            location=location or Location(city="", country=""),
            summary=sections.get("summary"),
            skills=skills,
            socialLinks=social_links,
            metadata={"source": "pdf"}
        )
        
        cv.mark_null_fields()
        return cv


# Test the parser
if __name__ == "__main__":
    # Example usage (requires a test PDF)
    parser = ResumeParserUnstructured()
    # cv = parser.parse_pdf("sample_resume.pdf")
    # print(cv.model_dump_json(indent=2))
