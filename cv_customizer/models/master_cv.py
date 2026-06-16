"""Master CV Schema - Comprehensive data model for all CV information

This is the central data structure used across all three agents:
- Parser Agent: Creates/populates this schema
- Job Search Agent: Uses it for ATS matching
- CV Tailor Agent: Tailors content from this schema
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, HttpUrl, Field, validator
from datetime import datetime
from enum import Enum


# ==================== Enums ====================

class EmploymentType(str, Enum):
    """Employment types"""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"


class EducationLevel(str, Enum):
    """Education qualification levels"""
    HIGH_SCHOOL = "high_school"
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"
    DIPLOMA = "diploma"
    CERTIFICATION = "certification"


class SkillLevel(str, Enum):
    """Skill proficiency levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


# ==================== Personal Information ====================

class PersonalInfo(BaseModel):
    """User personal information"""
    first_name: str = Field(..., min_length=1, description="First name")
    last_name: str = Field(..., min_length=1, description="Last name")
    email: EmailStr = Field(..., description="Primary email address")
    phone: str = Field(..., min_length=10, description="Phone number with country code")
    location: str = Field(..., min_length=1, description="City, State, Country")
    
    # Optional contact details
    linkedin_url: Optional[HttpUrl] = None
    github_url: Optional[HttpUrl] = None
    portfolio_url: Optional[HttpUrl] = None
    personal_website: Optional[HttpUrl] = None
    twitter_handle: Optional[str] = None

    class Config:
        example = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "+1-555-123-4567",
            "location": "San Francisco, CA, USA",
            "linkedin_url": "https://linkedin.com/in/johndoe",
            "github_url": "https://github.com/johndoe",
        }


# ==================== Professional Summary ====================

class ProfessionalSummary(BaseModel):
    """Professional headline and summary"""
    headline: str = Field(..., min_length=10, max_length=200, description="Professional headline")
    summary: str = Field(..., min_length=20, max_length=1000, description="Career summary/objective")
    total_experience_years: float = Field(..., ge=0, description="Total years of experience")
    specialization: Optional[str] = None
    key_achievements: Optional[List[str]] = None

    class Config:
        example = {
            "headline": "Full Stack Developer | Python & React Expert",
            "summary": "Experienced full-stack developer with 5+ years building scalable web applications...",
            "total_experience_years": 5.5,
            "key_achievements": ["Led 10+ projects", "Team lead for 5 engineers"]
        }


# ==================== Work Experience ====================

class Experience(BaseModel):
    """Work experience entry"""
    company_name: str = Field(..., min_length=1, description="Company name")
    job_title: str = Field(..., min_length=1, description="Job title/position")
    employment_type: EmploymentType = Field(default=EmploymentType.FULL_TIME)
    location: Optional[str] = None
    
    start_date: str = Field(..., description="Start date (YYYY-MM or YYYY-MM-DD)")
    end_date: Optional[str] = None
    is_current: bool = Field(default=False, description="Currently working here")
    
    description: str = Field(..., min_length=10, description="Job responsibilities and achievements")
    achievements: List[str] = Field(default_factory=list, description="Key achievements")
    skills_used: List[str] = Field(default_factory=list, description="Skills used in this role")
    
    @validator('is_current')
    def validate_current(cls, v, values):
        if v and 'end_date' in values and values['end_date']:
            raise ValueError("is_current must be False if end_date is provided")
        return v

    class Config:
        example = {
            "company_name": "Tech Corp",
            "job_title": "Senior Backend Engineer",
            "employment_type": "full_time",
            "start_date": "2022-01",
            "end_date": None,
            "is_current": True,
            "description": "Led development of microservices architecture...",
            "achievements": ["Improved performance by 40%", "Mentored 3 junior developers"],
            "skills_used": ["Python", "FastAPI", "Docker", "PostgreSQL"]
        }


# ==================== Education ====================

class Education(BaseModel):
    """Education entry"""
    institution: str = Field(..., min_length=1, description="School/University name")
    degree: EducationLevel = Field(..., description="Degree type")
    field_of_study: str = Field(..., min_length=1, description="Major/Field of study")
    location: Optional[str] = None
    
    start_date: str = Field(..., description="Start date (YYYY-MM or YYYY-MM-DD)")
    graduation_date: str = Field(..., description="Graduation date (YYYY-MM or YYYY-MM-DD)")
    
    gpa: Optional[float] = Field(None, ge=0, le=4.0, description="GPA (if applicable)")
    grade: Optional[str] = None
    description: Optional[str] = None
    
    activities: List[str] = Field(default_factory=list, description="Clubs, societies, awards")
    courses: List[str] = Field(default_factory=list, description="Relevant courses taken")

    class Config:
        example = {
            "institution": "University of California",
            "degree": "bachelor",
            "field_of_study": "Computer Science",
            "graduation_date": "2020-05",
            "gpa": 3.8,
            "activities": ["Debate Club President", "Dean's List"],
            "courses": ["Data Structures", "Machine Learning", "Web Development"]
        }


# ==================== Skills ====================

class Skill(BaseModel):
    """Individual skill entry"""
    name: str = Field(..., min_length=1, description="Skill name")
    level: SkillLevel = Field(default=SkillLevel.INTERMEDIATE, description="Proficiency level")
    category: str = Field(..., description="Category (e.g., Programming, Data Analysis)")
    endorsements: Optional[int] = Field(None, ge=0, description="Number of endorsements")
    years_of_experience: Optional[float] = Field(None, ge=0)

    class Config:
        example = {
            "name": "Python",
            "level": "expert",
            "category": "Programming Languages",
            "years_of_experience": 5
        }


# ==================== Certifications ====================

class Certification(BaseModel):
    """Certification entry"""
    name: str = Field(..., min_length=1, description="Certification name")
    issuer: str = Field(..., min_length=1, description="Issuing organization")
    issue_date: str = Field(..., description="Date issued (YYYY-MM or YYYY-MM-DD)")
    expiration_date: Optional[str] = None
    is_active: bool = Field(default=True, description="Certification is still valid")
    credential_id: Optional[str] = None
    credential_url: Optional[HttpUrl] = None
    description: Optional[str] = None

    class Config:
        example = {
            "name": "AWS Certified Solutions Architect",
            "issuer": "Amazon Web Services",
            "issue_date": "2023-06",
            "expiration_date": "2025-06",
            "credential_url": "https://aws.example.com/cert/12345"
        }


# ==================== Projects ====================

class Project(BaseModel):
    """Project entry"""
    name: str = Field(..., min_length=1, description="Project name")
    description: str = Field(..., min_length=10, description="Project description")
    
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = Field(default=False)
    
    technologies_used: List[str] = Field(default_factory=list, description="Tech stack")
    role: Optional[str] = None
    team_size: Optional[int] = Field(None, ge=1)
    
    project_url: Optional[HttpUrl] = None
    github_url: Optional[HttpUrl] = None
    demo_url: Optional[HttpUrl] = None
    
    key_achievements: List[str] = Field(default_factory=list, description="Key results")
    outcomes: Optional[str] = None

    class Config:
        example = {
            "name": "AI Resume Parser",
            "description": "Built an AI-powered tool to parse and analyze resumes...",
            "start_date": "2024-01",
            "technologies_used": ["Python", "FastAPI", "LangChain"],
            "github_url": "https://github.com/user/project",
            "key_achievements": ["Parsed 10k+ resumes", "95% accuracy rate"]
        }


# ==================== Languages ====================

class Language(BaseModel):
    """Language proficiency"""
    name: str = Field(..., min_length=1, description="Language name")
    proficiency: SkillLevel = Field(default=SkillLevel.INTERMEDIATE)
    native: bool = Field(default=False, description="Native language")

    class Config:
        example = {
            "name": "English",
            "proficiency": "expert",
            "native": True
        }


# ==================== Achievements & Awards ====================

class Achievement(BaseModel):
    """Notable achievement or award"""
    title: str = Field(..., min_length=1, description="Achievement title")
    description: str = Field(..., min_length=10)
    date: str = Field(..., description="Date achieved (YYYY-MM or YYYY-MM-DD)")
    issuer: Optional[str] = None
    url: Optional[HttpUrl] = None

    class Config:
        example = {
            "title": "Employee of the Year",
            "description": "Recognized for exceptional contribution to company growth...",
            "date": "2023-12",
            "issuer": "Tech Corp"
        }


# ==================== Metadata ====================

class CVMetadata(BaseModel):
    """Metadata about the CV itself"""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    source: str = Field(default="manual", description="Source: pdf, portfolio, manual")
    extraction_confidence: float = Field(default=1.0, ge=0, le=1, description="Parser confidence score")
    parser_version: Optional[str] = None
    last_ats_score: Optional[float] = None
    last_ats_check_date: Optional[datetime] = None

    class Config:
        example = {
            "source": "pdf",
            "extraction_confidence": 0.95
        }


# ==================== Master CV ====================

class MasterCV(BaseModel):
    """
    Master CV Schema - Complete standardized CV structure
    Used by all three agents (Parser, Job Search, CV Tailor)
    """
    
    # Unique identifier
    cv_id: Optional[str] = Field(None, description="Unique CV identifier (UUID)")
    user_id: Optional[str] = Field(None, description="User identifier")
    
    # Core sections
    personal_info: PersonalInfo
    professional_summary: ProfessionalSummary
    
    # Experience and education
    experience: List[Experience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    
    # Skills and proficiencies
    skills: List[Skill] = Field(default_factory=list)
    languages: List[Language] = Field(default_factory=list)
    
    # Additional content
    certifications: List[Certification] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    achievements: List[Achievement] = Field(default_factory=list)
    
    # Custom sections
    additional_sections: Optional[Dict[str, str]] = Field(
        default_factory=dict, 
        description="Custom sections (e.g., publications, volunteering, interests)"
    )
    
    # Metadata
    metadata: CVMetadata = Field(default_factory=CVMetadata)

    def get_missing_fields(self) -> List[str]:
        """Get list of missing required fields"""
        missing = []
        if not self.personal_info.first_name:
            missing.append("personal_info.first_name")
        if not self.personal_info.email:
            missing.append("personal_info.email")
        if not self.personal_info.phone:
            missing.append("personal_info.phone")
        if not self.professional_summary.summary:
            missing.append("professional_summary.summary")
        if not self.experience:
            missing.append("experience (at least 1)")
        if not self.skills:
            missing.append("skills (at least 3)")
        return missing

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict"""
        return self.model_dump(by_alias=True, exclude_none=False)

    def to_json_minimal(self) -> Dict[str, Any]:
        """Convert to minimal JSON (excluding empty lists)"""
        return self.model_dump(by_alias=True, exclude_none=True)

    class Config:
        example = {
            "personal_info": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "phone": "+1-555-123-4567",
                "location": "San Francisco, CA, USA",
            },
            "professional_summary": {
                "headline": "Senior Backend Engineer",
                "summary": "5+ years building scalable systems...",
                "total_experience_years": 5,
            },
            "skills": [
                {"name": "Python", "level": "expert", "category": "Programming"}
            ],
            "experience": [],
            "education": [],
        }


# ==================== API Response Models ====================

class CVValidationResponse(BaseModel):
    """Response from CV validation"""
    is_valid: bool
    missing_fields: List[str]
    warnings: List[str] = []
    confidence_score: float


class CVComparisonResult(BaseModel):
    """Result of comparing CV with job requirements"""
    cv_id: str
    job_id: str
    match_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    matched_experience_years: float
    required_experience_years: float
