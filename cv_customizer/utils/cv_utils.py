"""Utilities for Master CV operations and validation"""

import json
import logging
from typing import Dict, List, Optional, Any
from cv_customizer.models.master_cv import MasterCV, CVValidationResponse, SkillLevel

logger = logging.getLogger(__name__)


class CVValidator:
    """Validates CV data completeness and quality"""

    # Minimum requirements
    MIN_SKILLS = 3
    MIN_EXPERIENCE_YEARS = 0
    MIN_EXPERIENCE_ENTRIES = 0
    MIN_EDUCATION_ENTRIES = 1

    @classmethod
    def validate_cv(cls, cv: MasterCV) -> CVValidationResponse:
        """Comprehensive CV validation"""
        warnings = []
        missing_fields = cv.get_missing_fields()

        # Check skill count
        if len(cv.skills) < cls.MIN_SKILLS:
            warnings.append(
                f"Only {len(cv.skills)} skills listed (recommended: {cls.MIN_SKILLS}+)"
            )

        # Check experience
        if not cv.experience:
            warnings.append("No work experience entries found")

        # Check education
        if not cv.education:
            warnings.append("No education entries found")

        # Check summary length
        if cv.professional_summary and len(cv.professional_summary.summary) < 50:
            warnings.append("Professional summary is quite short (recommended: 50+ chars)")

        # Check project counts for freshers (2-3) and experienced candidates (2+)
        is_fresher = True
        if cv.professional_summary and cv.professional_summary.total_experience_years >= 1.0:
            is_fresher = False
        elif cv.experience and len(cv.experience) > 0:
            is_fresher = False

        num_projects = len(cv.projects)
        if is_fresher:
            if num_projects < 2 or num_projects > 3:
                warnings.append(
                    f"Candidate identified as fresher. Listed {num_projects} projects (recommended: 2-3 to maintain optimal ATS score)"
                )
        else:
            if num_projects < 2:
                warnings.append(
                    f"Candidate identified as experienced/freelancer. Listed {num_projects} projects (recommended: 2+ to maintain optimal ATS score)"
                )

        # Calculate confidence score
        confidence = cls._calculate_confidence(cv)

        return CVValidationResponse(
            is_valid=len(missing_fields) == 0,
            missing_fields=missing_fields,
            warnings=warnings,
            confidence_score=confidence,
        )

    @classmethod
    def _calculate_confidence(cls, cv: MasterCV) -> float:
        """Calculate data quality confidence score (0-1)"""
        score = 0.0
        total_weight = 0

        # Personal info (30% weight)
        personal_score = 1.0
        if not cv.personal_info.linkedin_url:
            personal_score -= 0.1
        if not cv.personal_info.github_url:
            personal_score -= 0.1
        score += personal_score * 0.3
        total_weight += 0.3

        # Professional summary (20% weight)
        if cv.professional_summary and len(cv.professional_summary.summary) > 100:
            score += 1.0 * 0.2
        elif cv.professional_summary and len(cv.professional_summary.summary) > 50:
            score += 0.8 * 0.2
        total_weight += 0.2

        # Experience (20% weight)
        exp_score = min(1.0, len(cv.experience) / 3)  # Max 3 entries for full score
        if cv.experience and all(e.achievements for e in cv.experience):
            exp_score = 1.0
        score += exp_score * 0.2
        total_weight += 0.2

        # Skills (15% weight)
        skill_score = min(1.0, len(cv.skills) / 10)  # Max 10 skills for full score
        score += skill_score * 0.15
        total_weight += 0.15

        # Certifications & Projects (15% weight)
        other_score = min(1.0, (len(cv.certifications) + len(cv.projects)) / 5)
        score += other_score * 0.15
        total_weight += 0.15

        return round(score / total_weight, 2)


class CVMerger:
    """Merge CV data from multiple sources (PDF, portfolio, manual)"""

    @staticmethod
    def merge_cvs(primary: MasterCV, secondary: MasterCV) -> MasterCV:
        """Merge secondary CV into primary, preferring primary data"""
        merged = primary.model_copy(deep=True)

        # Merge personal info (prefer primary, fill missing from secondary)
        if not merged.personal_info.first_name and secondary.personal_info.first_name:
            merged.personal_info.first_name = secondary.personal_info.first_name

        if not merged.personal_info.linkedin_url and secondary.personal_info.linkedin_url:
            merged.personal_info.linkedin_url = secondary.personal_info.linkedin_url

        # Merge skills (avoid duplicates, prefer higher expertise level)
        secondary_skills = {s.name: s for s in secondary.skills}
        for skill in merged.skills:
            if skill.name in secondary_skills:
                secondary_skill = secondary_skills[skill.name]
                if secondary_skill.level.value > skill.level.value:
                    skill.level = secondary_skill.level
                secondary_skills.pop(skill.name)

        # Add remaining secondary skills
        merged.skills.extend(secondary_skills.values())

        # Merge experience, education, certifications (append secondary if not duplicate)
        merged.experience.extend(
            [
                e
                for e in secondary.experience
                if e not in merged.experience
            ]
        )
        merged.education.extend(
            [
                e
                for e in secondary.education
                if e not in merged.education
            ]
        )
        merged.certifications.extend(
            [
                c
                for c in secondary.certifications
                if c not in merged.certifications
            ]
        )
        merged.projects.extend(
            [
                p
                for p in secondary.projects
                if p not in merged.projects
            ]
        )

        return merged


class CVComparator:
    """Compare CV with job requirements"""

    @staticmethod
    def compare_skills(cv_skills: List[str], required_skills: List[str]) -> Dict[str, Any]:
        """Compare CV skills with required skills"""
        cv_skill_names = {s.lower() for s in cv_skills}
        required_skill_names = {s.lower() for s in required_skills}

        matched = cv_skill_names & required_skill_names
        missing = required_skill_names - cv_skill_names
        extra = cv_skill_names - required_skill_names

        return {
            "matched": list(matched),
            "missing": list(missing),
            "extra": list(extra),
            "match_percentage": len(matched) / len(required_skill_names) * 100
            if required_skill_names
            else 100,
        }

    @staticmethod
    def calculate_ats_score(cv: MasterCV, job_keywords: List[str]) -> float:
        """
        Calculate ATS score based on keyword matching
        Score ranges from 0 to 1
        """
        cv_text = CVComparator._extract_cv_text(cv).lower()
        job_keywords_lower = [k.lower() for k in job_keywords]

        matched_keywords = sum(1 for kw in job_keywords_lower if kw in cv_text)
        total_keywords = len(job_keywords_lower) if job_keywords_lower else 1

        base_score = matched_keywords / total_keywords
        return round(base_score, 2)

    @staticmethod
    def _extract_cv_text(cv: MasterCV) -> str:
        """Extract all text from CV for keyword matching"""
        text_parts = [
            cv.personal_info.first_name,
            cv.personal_info.last_name,
            cv.professional_summary.summary if cv.professional_summary else "",
        ]

        for skill in cv.skills:
            text_parts.append(skill.name)

        for exp in cv.experience:
            text_parts.extend([exp.company_name, exp.job_title, exp.description])
            text_parts.extend(exp.skills_used)

        for edu in cv.education:
            text_parts.extend([edu.institution, edu.field_of_study])

        for cert in cv.certifications:
            text_parts.append(cert.name)

        return " ".join(str(p) for p in text_parts if p)


class CVExporter:
    """Export CV to various formats"""

    @staticmethod
    def to_json(cv: MasterCV, minimal: bool = False) -> str:
        """Export CV as JSON"""
        if minimal:
            data = cv.to_json_minimal()
        else:
            data = cv.to_json()
        return json.dumps(data, indent=2, default=str)

    @staticmethod
    def to_dict(cv: MasterCV, minimal: bool = False) -> Dict[str, Any]:
        """Export CV as dictionary"""
        if minimal:
            return cv.to_json_minimal()
        return cv.to_json()

    @staticmethod
    def to_plain_text(cv: MasterCV) -> str:
        """Export CV as plain text"""
        lines = []

        # Header
        lines.append(f"{cv.personal_info.first_name} {cv.personal_info.last_name}".upper())
        lines.append("=" * 80)
        lines.append(f"Email: {cv.personal_info.email}")
        lines.append(f"Phone: {cv.personal_info.phone}")
        lines.append(f"Location: {cv.personal_info.location}")
        if cv.personal_info.linkedin_url:
            lines.append(f"LinkedIn: {cv.personal_info.linkedin_url}")
        lines.append("")

        # Professional Summary
        if cv.professional_summary:
            lines.append("PROFESSIONAL SUMMARY")
            lines.append("-" * 80)
            lines.append(cv.professional_summary.headline)
            lines.append(cv.professional_summary.summary)
            lines.append("")

        # Experience
        if cv.experience:
            lines.append("EXPERIENCE")
            lines.append("-" * 80)
            for exp in cv.experience:
                lines.append(f"{exp.job_title} at {exp.company_name}")
                lines.append(f"{exp.start_date} - {exp.end_date or 'Present'}")
                lines.append(exp.description)
                if exp.skills_used:
                    lines.append(f"Skills: {', '.join(exp.skills_used)}")
                lines.append("")

        # Skills
        if cv.skills:
            lines.append("SKILLS")
            lines.append("-" * 80)
            skill_groups = {}
            for skill in cv.skills:
                if skill.category not in skill_groups:
                    skill_groups[skill.category] = []
                skill_groups[skill.category].append(skill.name)

            for category, skills in skill_groups.items():
                lines.append(f"{category}: {', '.join(skills)}")
            lines.append("")

        # Education
        if cv.education:
            lines.append("EDUCATION")
            lines.append("-" * 80)
            for edu in cv.education:
                lines.append(f"{edu.degree.value.upper()} in {edu.field_of_study}")
                lines.append(f"{edu.institution} ({edu.graduation_date})")
                if edu.gpa:
                    lines.append(f"GPA: {edu.gpa}")
                lines.append("")

        # Certifications
        if cv.certifications:
            lines.append("CERTIFICATIONS")
            lines.append("-" * 80)
            for cert in cv.certifications:
                lines.append(f"{cert.name} - {cert.issuer} ({cert.issue_date})")
            lines.append("")

        # Projects
        if cv.projects:
            lines.append("PROJECTS")
            lines.append("-" * 80)
            for proj in cv.projects:
                lines.append(f"{proj.name}")
                lines.append(proj.description)
                if proj.technologies_used:
                    lines.append(f"Technologies: {', '.join(proj.technologies_used)}")
                lines.append("")

        return "\n".join(lines)
