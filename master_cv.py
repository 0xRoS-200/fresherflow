"""
Master CV Schema - Standardized format for all agents
Defines the structure for storing candidate information
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, field_validator, model_validator
from datetime import datetime
import json


class Skill(BaseModel):
    """Single skill with proficiency level"""
    name: str
    proficiency: Literal["beginner", "intermediate", "expert"] = "intermediate"
    category: Optional[Literal["technical", "soft", "domain"]] = None


class Experience(BaseModel):
    """Work experience entry"""
    role: str
    company: str
    startDate: str  # YYYY-MM
    endDate: Optional[str] = None  # YYYY-MM or "present"
    description: str = ""
    responsibilities: Optional[List[str]] = None
    # Raw accomplishments as extracted from resume - preserved for AI rewriting
    rawAccomplishments: List[str] = []


class Education(BaseModel):
    """Educational qualification"""
    degree: str
    # Support both 'university' (legacy) and 'institution' (new schema)
    university: Optional[str] = None
    institution: Optional[str] = None
    field: Optional[str] = None
    graduationYear: Optional[int] = None
    startDate: Optional[str] = None   # YYYY-MM or YYYY
    endDate: Optional[str] = None     # YYYY-MM or YYYY
    gpa: Optional[float] = None
    description: Optional[str] = None

    @model_validator(mode="after")
    def resolve_institution_alias(self):
        """Ensure university and institution are in sync (either can be used)"""
        if self.institution and not self.university:
            self.university = self.institution
        elif self.university and not self.institution:
            self.institution = self.university
        return self


class Certification(BaseModel):
    """Professional certification"""
    name: str
    issuer: str
    issueDate: Optional[int] = None   # YYYY
    expiryDate: Optional[int] = None  # YYYY
    credentialUrl: Optional[str] = None


class Project(BaseModel):
    """Portfolio project"""
    title: str
    description: str = ""
    # techStack as a comma-separated string OR technologies as a list
    techStack: Optional[str] = None
    technologies: Optional[List[str]] = None
    repositoryUrl: Optional[str] = None
    deployedUrl: Optional[str] = None
    date: Optional[str] = None  # YYYY-MM
    # Raw accomplishments as extracted from resume - preserved for AI rewriting
    rawAccomplishments: List[str] = []

    @model_validator(mode="after")
    def resolve_tech_fields(self):
        """Sync techStack string and technologies list"""
        if self.techStack and not self.technologies:
            self.technologies = [t.strip() for t in self.techStack.split(",") if t.strip()]
        elif self.technologies and not self.techStack:
            self.techStack = ", ".join(self.technologies)
        return self


class Language(BaseModel):
    """Language proficiency"""
    name: str
    proficiency: Literal["beginner", "intermediate", "fluent", "native"]


class Location(BaseModel):
    """Candidate location"""
    city: str
    country: str


class SocialLinks(BaseModel):
    """Social and portfolio links"""
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    twitter: Optional[str] = None
    other: Optional[Dict[str, str]] = None


class CVMetadata(BaseModel):
    """Metadata about CV"""
    source: Literal["pdf", "portfolio", "manual"] = "manual"
    createdAt: datetime = datetime.now()
    updatedAt: datetime = datetime.now()
    completionPercentage: int = 0  # 0-100
    nullFields: List[str] = []  # Fields that are None/empty


class MasterCV(BaseModel):
    """
    Master CV - Single source of truth for all resume operations
    All agent operations reference this schema
    """
    # Required fields
    name: str
    email: str
    phone: str
    location: Location

    # Profile classification
    profileType: Literal["fresher", "experienced"] = "fresher"
    totalExperienceYears: float = 0.0
    targetRole: Optional[str] = None
    jobDescription: Optional[str] = None  # populated during job tailoring

    # Optional but important
    summary: Optional[str] = None
    skills: List[Skill] = []
    experience: List[Experience] = []
    education: List[Education] = []

    # Nice to have
    certifications: Optional[List[Certification]] = None
    projects: Optional[List[Project]] = None
    socialLinks: Optional[SocialLinks] = None
    languages: Optional[List[Language]] = None

    # Standalone achievements (awards, honors, publications, competitions)
    achievements: List[str] = []

    # Metadata
    metadata: CVMetadata = CVMetadata(source="manual")

    @model_validator(mode="after")
    def infer_profile_type(self):
        """Auto-infer profileType from totalExperienceYears if not explicitly set"""
        if self.totalExperienceYears >= 1.0 and self.profileType == "fresher":
            self.profileType = "experienced"
        return self

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        """Validate email format"""
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        """Validate phone - at least 10 digits"""
        if v:
            digits = "".join(c for c in v if c.isdigit())
            if len(digits) < 10:
                raise ValueError("Phone must have at least 10 digits")
        return v

    def get_missing_fields(self) -> List[str]:
        """Return list of required fields that are None or empty"""
        missing = []

        if not self.name or self.name.strip() == "":
            missing.append("name")
        if not self.email or self.email.strip() == "":
            missing.append("email")
        if not self.phone or self.phone.strip() == "":
            missing.append("phone")
        if not self.location or (not self.location.city and not self.location.country):
            missing.append("location")
        if not self.skills or len(self.skills) == 0:
            missing.append("skills")
        if not self.education or len(self.education) == 0:
            missing.append("education")

        return missing

    def calculate_completion(self) -> int:
        """Calculate completion percentage (0-100)"""
        fields = {
            "name": bool(self.name),
            "email": bool(self.email),
            "phone": bool(self.phone),
            "location": bool(self.location.city and self.location.country),
            "profileType": bool(self.profileType),
            "summary": bool(self.summary),
            "skills": len(self.skills) > 0,
            "experience": len(self.experience) > 0,
            "education": len(self.education) > 0,
            "certifications": bool(self.certifications) and len(self.certifications) > 0,
            "projects": bool(self.projects) and len(self.projects) > 0,
            "socialLinks": bool(self.socialLinks),
            "achievements": len(self.achievements) > 0,
        }

        filled = sum(1 for v in fields.values() if v)
        completion = (filled / len(fields)) * 100
        self.metadata.completionPercentage = int(completion)
        return int(completion)

    def to_json(self) -> Dict[str, Any]:
        """Export as JSON-serializable dict"""
        return self.model_dump(mode="json")

    def mark_null_fields(self):
        """Mark fields that are None/empty in metadata"""
        missing = self.get_missing_fields()
        self.metadata.nullFields = missing
        self.metadata.updatedAt = datetime.now()

    def build_tailor_schema(self) -> Dict[str, Any]:
        """
        Build the structured JSON schema expected by the elite resume strategist prompt.
        Maps internal MasterCV fields to the canonical tailor schema.
        """
        skills_obj = {
            "languages": [s.name for s in self.skills if s.category == "technical" and any(
                lang in s.name.lower() for lang in
                ['python', 'java', 'javascript', 'c++', 'c#', 'typescript', 'kotlin', 'swift', 'go', 'rust', 'sql', 'html', 'css', 'c ', 'scala', 'php', 'ruby']
            )],
            "frameworks": [s.name for s in self.skills if s.category == "technical" and any(
                fw in s.name.lower() for fw in
                ['react', 'angular', 'vue', 'django', 'flask', 'spring', 'node', 'express', 'fastapi', 'numpy', 'pandas', 'tensorflow', 'pytorch', 'sklearn']
            )],
            "tools": [s.name for s in self.skills if s.category == "technical" and any(
                tool in s.name.lower() for tool in
                ['docker', 'git', 'aws', 'gcp', 'azure', 'kubernetes', 'jenkins', 'mongodb', 'postgresql', 'mysql', 'redis', 'linux', 'firebase']
            )],
        }
        # Any skill not categorized goes into languages bucket as fallback
        all_bucketed = set(skills_obj["languages"] + skills_obj["frameworks"] + skills_obj["tools"])
        unbucketed = [s.name for s in self.skills if s.name not in all_bucketed]
        skills_obj["languages"].extend(unbucketed)

        return {
            "profileType": self.profileType,
            "totalExperienceYears": self.totalExperienceYears,
            "personalInfo": {
                "name": self.name,
                "phone": self.phone,
                "email": self.email,
                "location": f"{self.location.city}, {self.location.country}".strip(", "),
                "linkedin": self.socialLinks.linkedin if self.socialLinks else "",
                "github": self.socialLinks.github if self.socialLinks else "",
            },
            "targetRole": self.targetRole or "",
            "jobDescription": self.jobDescription or "",
            "education": [
                {
                    "degree": e.degree,
                    "institution": e.university or e.institution or "",
                    "gpa": str(e.gpa) if e.gpa else "",
                    "startDate": e.startDate or "",
                    "endDate": e.endDate or str(e.graduationYear) if e.graduationYear else "",
                }
                for e in self.education
            ],
            "experience": [
                {
                    "company": exp.company,
                    "role": exp.role,
                    "startDate": exp.startDate,
                    "endDate": exp.endDate or "present",
                    "rawAccomplishments": exp.rawAccomplishments or (
                        exp.responsibilities if exp.responsibilities else
                        [exp.description] if exp.description else []
                    ),
                }
                for exp in self.experience
            ],
            "projects": [
                {
                    "name": proj.title,
                    "techStack": proj.techStack or (", ".join(proj.technologies) if proj.technologies else ""),
                    "rawAccomplishments": proj.rawAccomplishments or (
                        [proj.description] if proj.description else []
                    ),
                }
                for proj in (self.projects or [])
            ],
            "skills": skills_obj,
            "certifications": [c.name for c in (self.certifications or [])],
            "achievements": self.achievements,
        }


# Example usage for testing
if __name__ == "__main__":
    cv = MasterCV(
        name="John Doe",
        email="john@example.com",
        phone="+1234567890",
        location=Location(city="Bangalore", country="India"),
        profileType="fresher",
        totalExperienceYears=0,
        targetRole="Software Engineer",
        summary="Computer Science graduate seeking SWE roles",
        skills=[
            Skill(name="Python", proficiency="expert", category="technical"),
            Skill(name="JavaScript", proficiency="intermediate", category="technical"),
        ],
        experience=[
            Experience(
                role="SWE Intern",
                company="Tech Corp",
                startDate="2024-05",
                endDate="2024-08",
                description="Built REST APIs",
                rawAccomplishments=[
                    "Built REST APIs using Django that reduced response time by 40%",
                    "Implemented CI/CD pipeline cutting deployment time from 2 hours to 15 minutes"
                ]
            )
        ],
        education=[
            Education(
                degree="B.Tech",
                university="IIT Delhi",
                field="Computer Science",
                graduationYear=2025,
                gpa=3.8
            )
        ],
        achievements=[
            "Winner, Smart India Hackathon 2023",
            "Google CodeJam Top 500 globally"
        ]
    )

    print("Master CV:")
    print(cv.model_dump_json(indent=2))
    print(f"\nCompletion: {cv.calculate_completion()}%")
    print(f"Missing fields: {cv.get_missing_fields()}")
    print(f"\nTailor Schema:")
    print(json.dumps(cv.build_tailor_schema(), indent=2))
