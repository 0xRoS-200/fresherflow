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
        self.target_ats_score = 0.90
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
        prompt = """
Tailor the Master CV provided below for this specific job.
Focus on highlighting relevant skills and experience.

CRITICAL PROJECT TAILORING RULES:
For all project descriptions and accomplishments:
1. Every bullet point/item MUST start with a strong action verb (e.g., Developed, Designed, Engineered, Implemented).
2. Every item MUST contain a quantitative metric showing achievement (e.g., "reduced latency by 60%", "boosted throughput by 45%", "improved accuracy to 98%").
3. Every item MUST contain the workload/productivity impact (e.g., "reducing team workload by 30%", "making debugging 20% easier", "saving 15 hours of manual work weekly").
Example: "Developed an automated regression testing pipeline using PyTest and Docker, reducing test execution latency by 60% and decreasing developer workload by 30%."

Please provide:
1. Tailored professional summary
2. Reordered experience highlighting relevant achievements
3. Skills matching job requirements
4. Custom accomplishments for this role following the strict Action Verb + Quantitative Metric + Impact formatting above.

Keep professional tone and be specific to the job.

TARGET JOB Title: {job_title}
Required Skills: {required_skills}

MASTER CV:
{master_cv_str}

JOB DESCRIPTION:
{job_description}
""".format(
            job_title=job_data.get('title'),
            required_skills=', '.join(job_data.get('required_skills', [])),
            master_cv_str=str(master_cv),
            job_description=job_data.get('description', '')
        )
        return prompt

    def _build_latex_generation_prompt(self, content: Dict) -> str:
        """Build prompt for LaTeX generation"""
        prompt = """
Generate a professional LaTeX/Jake format CV from the content provided below.

Requirements:
- Use Jake CV template style
- Professional formatting
- ATS-friendly without graphics/tables
- Clear sections: Contact, Summary, Experience, Skills, Education, Projects
- Projects MUST contain accomplishments that strictly follow the syntax: Action Verb + Quantitative Metric + Impact (e.g. "Developed... reducing execution time by 60% and decreasing team workload by 30%").
- Proper LaTeX syntax. Ensure all percentage symbols are escaped as \\% and all ampersands are escaped as \\&.
- Return complete, compilable LaTeX code starting directly with \\documentclass. Do not wrap the code in markdown formatting or backticks.

TAILORED CONTENT TO GENERATE LATEX:
{content_str}
""".format(content_str=str(content))
        return prompt

    def _build_reconfiguration_prompt(self, cv_content: str, ats_score: float, job_data: Dict) -> str:
        """Build prompt for CV reconfiguration"""
        prompt = """
Improve the CV provided below to increase its ATS score (current score: {ats_score_percent}, target is 90%+).

Suggestions to improve:
1. Add more keywords from the job description.
2. Use stronger action verbs.
3. Quantify achievements more: ensure every project bullet point contains a clear metric (e.g., "reduced latency by 60%") and a workload/productivity impact (e.g., "reducing workload by 30%").
4. Better skill matching.

Return improved CV content keeping the structure.

TARGET JOB DESCRIPTION:
{job_description}

CURRENT CV CONTENT:
{cv_content}
""".format(
            ats_score_percent=f"{ats_score:.1%}",
            job_description=job_data.get('description', ''),
            cv_content=cv_content
        )
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
