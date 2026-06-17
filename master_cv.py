"""
Master CV Schema - Standardized format for all agents
Defines the structure for storing candidate information
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, EmailStr, HttpUrl, field_validator
from datetime import datetime


class Skill(BaseModel):
    """Single skill with proficiency level"""
    name: str
    proficiency: Literal["beginner", "intermediate", "expert"]
    category: Optional[Literal["technical", "soft", "domain"]] = None


class Experience(BaseModel):
    """Work experience entry"""
    role: str
    company: str
    startDate: str  # YYYY-MM
    endDate: Optional[str] = None  # YYYY-MM or "present"
    description: str
    responsibilities: Optional[List[str]] = None


class Education(BaseModel):
    """Educational qualification"""
    degree: str
    university: str
    field: Optional[str] = None
    graduationYear: int
    gpa: Optional[float] = None
    description: Optional[str] = None


class Certification(BaseModel):
    """Professional certification"""
    name: str
    issuer: str
    issueDate: int  # YYYY
    expiryDate: Optional[int] = None  # YYYY
    credentialUrl: Optional[str] = None


class Project(BaseModel):
    """Portfolio project"""
    title: str
    description: str
    technologies: Optional[List[str]] = None
    repositoryUrl: Optional[str] = None
    deployedUrl: Optional[str] = None
    date: str  # YYYY-MM


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
    source: Literal["pdf", "portfolio", "manual"]
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
    
    # Metadata
    metadata: CVMetadata = CVMetadata(source="manual")

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
        
        # Check required fields
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
        if not self.experience or len(self.experience) == 0:
            missing.append("experience")
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
            "summary": bool(self.summary),
            "skills": len(self.skills) > 0,
            "experience": len(self.experience) > 0,
            "education": len(self.education) > 0,
            "certifications": bool(self.certifications) and len(self.certifications) > 0,
            "projects": bool(self.projects) and len(self.projects) > 0,
            "socialLinks": bool(self.socialLinks),
            "languages": bool(self.languages) and len(self.languages) > 0,
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


# Example usage for testing
if __name__ == "__main__":
    cv = MasterCV(
        name="John Doe",
        email="john@example.com",
        phone="+1234567890",
        location=Location(city="Bangalore", country="India"),
        summary="Senior Software Engineer with 5+ years experience",
        skills=[
            Skill(name="Python", proficiency="expert", category="technical"),
            Skill(name="JavaScript", proficiency="intermediate", category="technical"),
        ],
        experience=[
            Experience(
                role="Senior Engineer",
                company="Tech Corp",
                startDate="2021-01",
                endDate="present",
                description="Led backend team",
                responsibilities=["Managed team of 5", "Designed architecture"]
            )
        ],
        education=[
            Education(
                degree="B.Tech",
                university="IIT Delhi",
                field="Computer Science",
                graduationYear=2019,
                gpa=3.8
            )
        ]
    )
    
    print("Master CV:")
    print(cv.model_dump_json(indent=2))
    print(f"\nCompletion: {cv.calculate_completion()}%")
    print(f"Missing fields: {cv.get_missing_fields()}")
