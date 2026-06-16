"""CV Tailor Agent - CV generation and tailoring using LangGraph"""

import logging
from typing import Dict, Optional
from cv_customizer.agents.llm_provider import LLMProvider, LLMResponse
from cv_customizer.agents.workflows import CVTailorAgentWorkflow

logger = logging.getLogger(__name__)


class CVTailorAgent:
    """
    Agent 3: Generate and tailor CV for specific job
    
    Customizes Master CV content for target job,
    generates LaTeX format, integrates with Overleaf,
    and optimizes ATS scores.
    """

    def __init__(self, provider: LLMProvider):
        self.provider = provider
        self.workflow = CVTailorAgentWorkflow(provider)
        self.max_iterations = 3
        self.target_ats_score = 0.95
        logger.info(f"CVTailorAgent initialized with provider: {provider.provider_type.value}")

    def tailor_cv_content(self, master_cv: Dict, job_data: Dict) -> str:
        """
        Tailor CV content for specific job using LLM
        
        Args:
            master_cv: User's Master CV
            job_data: Target job requirements and description
            
        Returns:
            Customized CV content
        """
        logger.info("Tailoring CV content for job...")
        try:
            prompt = self._build_tailoring_prompt(master_cv, job_data)
            response: LLMResponse = self.provider.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=5000
            )
            return response.content
        except Exception as e:
            logger.error(f"CV tailoring failed: {e}")
            raise

    def generate_latex(self, tailored_content: Dict) -> str:
        """
        Generate LaTeX CV in Jake format
        
        Args:
            tailored_content: Customized CV content
            
        Returns:
            LaTeX/Jake format CV code
        """
        logger.info("Generating LaTeX CV...")
        try:
            prompt = self._build_latex_generation_prompt(tailored_content)
            response: LLMResponse = self.provider.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=8000
            )
            latex_code = response.content
            return latex_code
        except Exception as e:
            logger.error(f"LaTeX generation failed: {e}")
            raise

    def sync_to_overleaf(self, latex_content: str, user_email: str) -> Dict:
        """
        Sync CV to Overleaf and generate PDF
        
        Args:
            latex_content: LaTeX/Jake format CV
            user_email: User's Overleaf email
            
        Returns:
            Dictionary with project_id and download_url
        """
        logger.info(f"Syncing to Overleaf for {user_email}...")
        try:
            # TODO: Implement Overleaf API integration
            project_data = self._create_overleaf_project(latex_content, user_email)
            return project_data
        except Exception as e:
            logger.error(f"Overleaf sync failed: {e}")
            raise

    def check_ats_score(self, cv_content: str) -> Dict:
        """
        Check ATS score of generated CV
        
        Args:
            cv_content: CV content to check
            
        Returns:
            ATS score and feedback
        """
        logger.info("Checking ATS score...")
        try:
            # TODO: Integrate with Resume Worded API or similar
            ats_result = self._calculate_ats_score(cv_content)
            return ats_result
        except Exception as e:
            logger.error(f"ATS check failed: {e}")
            raise

    def reconfigure_cv(
        self, cv_content: str, ats_score: float, job_data: Dict, iteration: int = 1
    ) -> str:
        """
        Reconfigure CV if ATS score below target
        
        Args:
            cv_content: Current CV content
            ats_score: Current ATS score
            job_data: Job requirements for context
            iteration: Current iteration number
            
        Returns:
            Improved CV content
        """
        if ats_score >= self.target_ats_score or iteration >= self.max_iterations:
            logger.info(f"Stopping reconfiguration: score={ats_score}, iterations={iteration}")
            return cv_content

        logger.info(f"Reconfiguring CV (iteration {iteration}/{self.max_iterations})...")
        try:
            prompt = self._build_reconfiguration_prompt(cv_content, ats_score, job_data)
            response: LLMResponse = self.provider.generate(
                prompt=prompt,
                temperature=0.7,
                max_tokens=5000
            )
            return response.content
        except Exception as e:
            logger.error(f"CV reconfiguration failed: {e}")
            raise

    def _build_tailoring_prompt(self, master_cv: Dict, job_data: Dict) -> str:
        """Build prompt for CV tailoring"""
        prompt = f"""
Tailor the following CV for this specific job.
Focus on highlighting relevant skills and experience.

MASTER CV:
{str(master_cv)[:2000]}

JOB REQUIREMENTS:
Title: {job_data.get('title')}
Description: {job_data.get('description', '')[:1000]}
Required Skills: {', '.join(job_data.get('required_skills', []))}

Please provide:
1. Tailored professional summary
2. Reordered experience highlighting relevant achievements
3. Skills matching job requirements
4. Custom accomplishments for this role

Keep professional tone and be specific to the job.
"""
        return prompt

    def _build_latex_generation_prompt(self, content: Dict) -> str:
        """Build prompt for LaTeX generation"""
        prompt = f"""
Generate a professional LaTeX/Jake format CV from this content:

{str(content)[:2000]}

Requirements:
- Use Jake CV template style
- Professional formatting
- ATS-friendly without graphics/tables
- Clear sections: Contact, Summary, Experience, Skills, Education
- Proper LaTeX syntax

Return complete, compilable LaTeX code.
"""
        return prompt

    def _build_reconfiguration_prompt(self, cv_content: str, ats_score: float, job_data: Dict) -> str:
        """Build prompt for CV reconfiguration"""
        prompt = f"""
Improve this CV to increase ATS score (current: {ats_score:.1%}).

CURRENT CV:
{cv_content[:2000]}

TARGET JOB:
{job_data.get('description', '')[:1000]}

Suggestions to improve:
1. Add more keywords from job description
2. Use stronger action verbs
3. Quantify achievements more
4. Better skill matching

Return improved CV content keeping the structure.
"""
        return prompt

    def _create_overleaf_project(self, latex_content: str, user_email: str) -> Dict:
        """Create Overleaf project and return details"""
        # TODO: Implement actual Overleaf API integration
        logger.info(f"Creating Overleaf project for {user_email}...")
        return {
            "project_id": "placeholder-project-id",
            "download_url": "https://example.com/download",
        }

    def _calculate_ats_score(self, cv_content: str) -> Dict:
        """Calculate ATS score using external API or internal logic"""
        # TODO: Integrate with Resume Worded API or similar
        logger.info("Calculating ATS score...")
        return {
            "score": 0.88,
            "feedback": "Add more keywords from job description",
            "missing_keywords": ["AI", "Machine Learning"],
            "strengths": ["Clear experience", "Good skills list"],
        }
