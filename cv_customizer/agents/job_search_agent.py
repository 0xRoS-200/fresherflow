"""Job Search Agent - Find and rank jobs using LangGraph"""

import logging
import json
import re
from typing import Dict, Optional, List, Tuple
from cv_customizer.agents.llm_provider import LLMProvider, LLMResponse
from cv_customizer.agents.workflows import JobSearchAgentWorkflow
from cv_customizer.utils.job_prompts import JobSearchPrompts, JobFilteringPrompts
from cv_customizer.models.master_cv import MasterCV
from cv_customizer.utils.cv_utils import CVComparator

logger = logging.getLogger(__name__)


class JobMetadata:
    """Structured job metadata"""
    def __init__(self, data: Dict):
        self.job_title = data.get("job_title", "")
        self.company_name = data.get("company_name", "")
        self.job_level = data.get("job_level", "")
        self.employment_type = data.get("employment_type", "")
        self.location = data.get("location", [])
        self.salary_min = data.get("salary_min")
        self.salary_max = data.get("salary_max")
        self.required_skills = data.get("required_skills", [])
        self.required_experience_years = data.get("required_experience_years")
        self.preferred_skills = data.get("preferred_skills", [])
        self.responsibilities = data.get("responsibilities", [])
        self.benefits = data.get("benefits", [])


class JobSearchAgent:
    """
    Agent 2: Search for jobs and filter by ATS score
    
    Uses LLM to extract job metadata and calculate ATS scores.
    Ranks jobs by match and relevance.
    """

    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.workflow = JobSearchAgentWorkflow(provider)
        logger.info(f"JobSearchAgent initialized with provider: {provider.provider_type.value}")

    def process_job_listings(self, master_cv: MasterCV, job_listings: List[Dict]) -> Dict:
        """
        Process multiple job listings and rank them
        
        Args:
            master_cv: User's Master CV
            job_listings: List of job postings (with 'description' field)
            
        Returns:
            Dict with ranked jobs and analysis
        """
        logger.info(f"Processing {len(job_listings)} job listings...")
        
        result = {
            "processed_count": 0,
            "passed_ats": 0,
            "jobs_with_scores": [],
            "ranked_jobs": [],
            "top_opportunities": [],
            "pass_threshold": 75,
        }
        
        try:
            # Process each job
            for job in job_listings:
                try:
                    processed = self._process_single_job(master_cv, job)
                    result["jobs_with_scores"].append(processed)
                    result["processed_count"] += 1
                    
                    if processed.get("ats_score", 0) >= result["pass_threshold"]:
                        result["passed_ats"] += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to process job: {e}")
                    continue
            
            # Rank passed jobs
            if result["jobs_with_scores"]:
                result["ranked_jobs"] = self.rank_jobs(result["jobs_with_scores"])
                result["top_opportunities"] = result["ranked_jobs"][:5]
            
            logger.info(f"Processed: {result['processed_count']}, Passed ATS: {result['passed_ats']}")
            
        except Exception as e:
            logger.error(f"Job listing processing failed: {e}")
            result["errors"] = [str(e)]
        
        return result

    def extract_job_metadata(self, job_description: str) -> Tuple[JobMetadata, float]:
        """
        Extract structured metadata from job description
        
        Args:
            job_description: Raw job description text
            
        Returns:
            Tuple of (JobMetadata object, extraction_confidence)
        """
        logger.info("Extracting job metadata...")
        try:
            prompt = JobSearchPrompts.build_job_metadata_extraction_prompt(job_description)
            
            response: LLMResponse = self.provider.generate(
                prompt=prompt,
                temperature=0.2,
                max_tokens=3000
            )
            
            metadata_dict = self._parse_json_response(response.content)
            metadata = JobMetadata(metadata_dict)
            confidence = self._estimate_metadata_confidence(metadata_dict)
            
            logger.info(f"Metadata extraction confidence: {confidence}")
            return metadata, confidence
            
        except Exception as e:
            logger.error(f"Metadata extraction failed: {e}")
            raise

    def extract_keywords_for_ats(self, job_description: str, cv_text: str) -> Dict:
        """
        Extract keywords for ATS matching
        
        Args:
            job_description: Job requirements text
            cv_text: CV text content
            
        Returns:
            Dict with required and matched keywords
        """
        logger.info("Extracting keywords for ATS analysis...")
        try:
            prompt = JobSearchPrompts.build_keyword_extraction_prompt(
                job_description,
                cv_text
            )
            
            response: LLMResponse = self.provider.generate(
                prompt=prompt,
                temperature=0.2,
                max_tokens=2000
            )
            
            keywords = self._parse_json_response(response.content)
            return keywords
            
        except Exception as e:
            logger.error(f"Keyword extraction failed: {e}")
            raise

    def calculate_ats_score(self, master_cv: MasterCV, job_description: str) -> Tuple[float, Dict]:
        """
        Calculate comprehensive ATS score for CV against job
        
        Args:
            master_cv: User's Master CV
            job_description: Job description text
            
        Returns:
            Tuple of (ats_score, analysis_details)
        """
        logger.info("Calculating comprehensive ATS score...")
        
        # Convert Master CV to text
        cv_text = self._master_cv_to_text(master_cv)
        
        try:
            # Get LLM analysis
            prompt = JobSearchPrompts.build_ats_analysis_prompt(cv_text, job_description)
            
            response: LLMResponse = self.provider.generate(
                prompt=prompt,
                temperature=0.2,
                max_tokens=2000
            )
            
            analysis = self._parse_json_response(response.content)
            ats_score = analysis.get("total_ats_score", 0)
            
            logger.info(f"ATS Score: {ats_score}/100")
            return float(ats_score), analysis
            
        except Exception as e:
            logger.error(f"ATS calculation failed: {e}")
            # Fallback to keyword matching
            return self._fallback_ats_score(cv_text, job_description), {}

    def filter_jobs_by_ats(self, jobs_with_scores: List[Dict], 
                          min_score: float = 75.0) -> List[Dict]:
        """
        Filter jobs by minimum ATS score
        
        Args:
            jobs_with_scores: Jobs with calculated ATS scores
            min_score: Minimum ATS score to pass
            
        Returns:
            Filtered list of jobs above threshold
        """
        logger.info(f"Filtering jobs by ATS score (min: {min_score})...")
        
        filtered = [job for job in jobs_with_scores 
                   if job.get("ats_score", 0) >= min_score]
        
        logger.info(f"Filtered: {len(filtered)} / {len(jobs_with_scores)} jobs passed")
        return filtered

    def rank_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """
        Rank jobs by ATS score and other factors
        
        Args:
            jobs: List of jobs with ATS scores
            
        Returns:
            Ranked list of jobs with rank field
        """
        logger.info(f"Ranking {len(jobs)} jobs...")
        
        # Sort by ATS score
        ranked = sorted(jobs, key=lambda x: x.get("ats_score", 0), reverse=True)
        
        # Add rank field
        for i, job in enumerate(ranked):
            job["rank"] = i + 1
            job["fit_category"] = self._categorize_fit(job.get("ats_score", 0))
        
        return ranked

    def generate_job_search_queries(self, master_cv: MasterCV, experience_level: str) -> Dict:
        """
        Generate optimized job search queries based on CV
        
        Args:
            master_cv: User's Master CV
            experience_level: User's experience level
            
        Returns:
            Dict with search queries for various portals
        """
        logger.info(f"Generating job search queries for {experience_level} level...")
        
        # Extract CV skills
        cv_skills = ", ".join([s.name for s in master_cv.skills[:20]])
        
        try:
            prompt = JobSearchPrompts.build_job_search_query_prompt(
                cv_skills,
                experience_level
            )
            
            response: LLMResponse = self.provider.generate(
                prompt=prompt,
                temperature=0.5,
                max_tokens=2000
            )
            
            queries = self._parse_json_response(response.content)
            logger.info("Job search queries generated successfully")
            return queries
            
        except Exception as e:
            logger.error(f"Query generation failed: {e}")
            # Return basic queries
            return self._generate_basic_queries(cv_skills)

    def assess_company_culture_fit(self, company_info: str, master_cv: MasterCV) -> Dict:
        """
        Assess cultural fit between candidate and company
        
        Args:
            company_info: Company information/description
            master_cv: User's Master CV
            
        Returns:
            Culture fit assessment
        """
        logger.info("Assessing company culture fit...")
        
        cv_profile = self._master_cv_to_text(master_cv)
        
        try:
            prompt = JobFilteringPrompts.build_company_culture_assessment_prompt(
                company_info,
                cv_profile
            )
            
            response: LLMResponse = self.provider.generate(
                prompt=prompt,
                temperature=0.5,
                max_tokens=1500
            )
            
            assessment = self._parse_json_response(response.content)
            return assessment
            
        except Exception as e:
            logger.error(f"Culture fit assessment failed: {e}")
            return {"culture_fit_score": 0, "insights": []}

    def _process_single_job(self, master_cv: MasterCV, job: Dict) -> Dict:
        """Process a single job listing"""
        job_desc = job.get("description", "")
        
        # Extract metadata
        metadata, meta_conf = self.extract_job_metadata(job_desc)
        
        # Calculate ATS score
        ats_score, ats_analysis = self.calculate_ats_score(master_cv, job_desc)
        
        return {
            "job_id": job.get("id", "unknown"),
            "title": metadata.job_title,
            "company": metadata.company_name,
            "location": metadata.location,
            "job_level": metadata.job_level,
            "employment_type": metadata.employment_type,
            "salary_range": (metadata.salary_min, metadata.salary_max),
            "ats_score": ats_score,
            "ats_analysis": ats_analysis,
            "metadata": {
                "required_skills": metadata.required_skills,
                "preferred_skills": metadata.preferred_skills,
                "required_experience": metadata.required_experience_years,
                "responsibilities": metadata.responsibilities,
                "benefits": metadata.benefits,
            },
            "source_url": job.get("url"),
            "raw_description": job_desc[:500],  # Store first 500 chars
        }

    def _master_cv_to_text(self, master_cv: MasterCV) -> str:
        """Convert Master CV to plain text for LLM processing"""
        text_parts = []
        
        # Personal info
        if master_cv.personal_info:
            text_parts.append(f"Name: {master_cv.personal_info.first_name} {master_cv.personal_info.last_name}")
            if master_cv.personal_info.email:
                text_parts.append(f"Email: {master_cv.personal_info.email}")
        
        # Professional summary
        if master_cv.professional_summary:
            text_parts.append(f"Professional Summary: {master_cv.professional_summary.summary}")
        
        # Experience
        if master_cv.experience:
            text_parts.append("Experience:")
            for exp in master_cv.experience[:5]:
                text_parts.append(f"- {exp.job_title} at {exp.company_name}")
                text_parts.append(f"  Skills: {', '.join(exp.skills_used)}")
        
        # Skills
        if master_cv.skills:
            text_parts.append(f"Skills: {', '.join([s.name for s in master_cv.skills])}")
        
        # Education
        if master_cv.education:
            text_parts.append("Education:")
            for edu in master_cv.education[:3]:
                text_parts.append(f"- {edu.degree.value} in {edu.field_of_study}")
        
        # Certifications
        if master_cv.certifications:
            text_parts.append(f"Certifications: {', '.join([c.name for c in master_cv.certifications])}")
        
        return "\n".join(text_parts)

    def _fallback_ats_score(self, cv_text: str, job_description: str) -> float:
        """Fallback ATS scoring using keyword matching"""
        logger.info("Using fallback ATS scoring...")
        
        cv_words = set(re.findall(r'\w+', cv_text.lower()))
        job_words = set(re.findall(r'\w+', job_description.lower()))
        
        # Find common words
        common = cv_words.intersection(job_words)
        
        # Filter out common English words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        common = common - stopwords
        
        # Calculate percentage
        if len(job_words) > 0:
            score = (len(common) / len(job_words)) * 100
            return min(100.0, score * 1.5)  # Boost the score
        
        return 50.0

    def _categorize_fit(self, ats_score: float) -> str:
        """Categorize job fit based on ATS score"""
        if ats_score >= 90:
            return "excellent_fit"
        elif ats_score >= 80:
            return "strong_fit"
        elif ats_score >= 75:
            return "good_fit"
        else:
            return "below_threshold"

    def _estimate_metadata_confidence(self, metadata: Dict) -> float:
        """Estimate metadata extraction confidence"""
        score = 0.0
        factors = 0
        
        if metadata.get("job_title"):
            score += 0.2
        factors += 1
        
        if metadata.get("company_name"):
            score += 0.2
        factors += 1
        
        if metadata.get("required_skills"):
            score += 0.2
        factors += 1
        
        if metadata.get("salary_min") or metadata.get("salary_max"):
            score += 0.2
        factors += 1
        
        if metadata.get("responsibilities"):
            score += 0.2
        factors += 1
        
        return score / 5 if factors > 0 else 0.0

    def _generate_basic_queries(self, cv_skills: str) -> Dict:
        """Generate basic search queries when LLM fails"""
        return {
            "linkedin": {
                "queries": cv_skills.split(","),
                "filters": {"experience": "all"}
            },
            "indeed": {
                "queries": cv_skills.split(","),
            },
            "job_boards": []
        }

    def _parse_json_response(self, response_text: str) -> Dict:
        """Parse JSON from LLM response"""
        try:
            text = response_text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            text = text.strip()
            parsed = json.loads(text)
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            logger.debug(f"Response text: {response_text[:200]}")
            return {}
