"""Pydantic schemas for request/response validation"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, HttpUrl


class PersonalInfo(BaseModel):
    name: str
    email: EmailStr
    phone: str
    location: str
    linkedin_url: Optional[HttpUrl] = None
    github_url: Optional[HttpUrl] = None
    portfolio_url: Optional[HttpUrl] = None


class Experience(BaseModel):
    job_title: str
    company: str
    start_date: str
    end_date: Optional[str] = None
    is_current: bool = False
    description: str
    skills_used: List[str] = []


class Education(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    graduation_date: str


class Certification(BaseModel):
    name: str
    issuer: str
    date_obtained: str
    credential_url: Optional[str] = None


class Project(BaseModel):
    name: str
    description: str
    technologies_used: List[str] = []
    project_url: Optional[str] = None
    github_url: Optional[str] = None


class MasterCV(BaseModel):
    personal: PersonalInfo
    professional_summary: Optional[str] = None
    total_experience_years: Optional[float] = None
    skills: List[str] = []
    certifications: List[Certification] = []
    experience: List[Experience] = []
    education: List[Education] = []
    projects: List[Project] = []
    languages: List[str] = []
    achievements: List[str] = []

    class Config:
        schema_extra = {
            "example": {
                "personal": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "phone": "+1234567890",
                    "location": "San Francisco, CA",
                },
                "skills": ["Python", "FastAPI", "Docker"],
                "experience": [],
            }
        }


class UploadRequest(BaseModel):
    upload_type: str  # "pdf" or "portfolio_link"
    file_path: Optional[str] = None
    portfolio_link: Optional[str] = None


class JobListing(BaseModel):
    job_id: str
    title: str
    company: str
    location: str
    description: str
    required_skills: List[str] = []
    required_experience_years: int = 0
    salary_range: Optional[str] = None
    job_url: str


class AtsScore(BaseModel):
    score: float
    feedback: str
    missing_keywords: List[str] = []
    strengths: List[str] = []


class TailoredCV(BaseModel):
    master_cv: MasterCV
    job_id: str
    tailored_content: str  # LaTeX content
    ats_score: AtsScore
    overleaf_project_id: Optional[str] = None
    download_url: Optional[str] = None


class ParseResponse(BaseModel):
    status: str
    master_cv: MasterCV
    missing_fields: List[str] = []
    confidence_score: float


class JobSearchResponse(BaseModel):
    jobs: List[JobListing] = []
    ats_scores: Dict[str, float] = {}
    top_matches: List[str] = []


class CVTailorResponse(BaseModel):
    tailored_cv: TailoredCV
    iterations_needed: int
    final_ats_score: float
    success: bool
