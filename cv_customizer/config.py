"""Configuration management for CV Customizer"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class LLMConfig:
    """LLM Provider configuration"""
    PROVIDERS = {
        "claude": {
            "name": "Claude (Anthropic)",
            "env_var": "ANTHROPIC_API_KEY",
            "required": True,
        },
        "gemini": {
            "name": "Gemini (Google)",
            "env_var": "GOOGLE_API_KEY",
            "required": True,
        },
        "chatgpt": {
            "name": "ChatGPT (OpenAI)",
            "env_var": "OPENAI_API_KEY",
            "required": True,
        },
        "groq": {
            "name": "Groq (Fast LLM)",
            "env_var": "GROQ_API_KEY",
            "required": False,
        },
        "ollama": {
            "name": "Ollama (Local)",
            "env_var": None,
            "required": False,
            "base_url": "http://localhost:11434",
        },
        "kimi": {
            "name": "Kimi (Moonshot)",
            "env_var": "KIMI_API_KEY",
            "required": False,
        },
    }

    # Selected providers
    PARSER_PROVIDER = os.getenv("PARSER_LLM_PROVIDER", "gemini")  # Agent1
    JOB_SEARCH_PROVIDER = os.getenv("JOB_SEARCH_LLM_PROVIDER", "claude")  # Agent2
    CV_TAILOR_PROVIDER = os.getenv("CV_TAILOR_LLM_PROVIDER", "chatgpt")  # Agent3


class AppConfig:
    """Application configuration"""
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class ExternalAPIs:
    """External API configurations"""
    # Overleaf
    OVERLEAF_API_URL = "https://www.overleaf.com/api"
    OVERLEAF_USER_EMAIL = os.getenv("OVERLEAF_EMAIL")
    OVERLEAF_PASSWORD = os.getenv("OVERLEAF_PASSWORD")

    # ATS Scoring (Resume Worded or similar)
    ATS_SCORING_API_KEY = os.getenv("ATS_SCORING_API_KEY")
    ATS_TARGET_SCORE = int(os.getenv("ATS_TARGET_SCORE", "95"))

    # Job Search APIs
    LINKEDIN_API_KEY = os.getenv("LINKEDIN_API_KEY")
    INDEED_API_KEY = os.getenv("INDEED_API_KEY")


class MasterCVSchema:
    """Master CV template with all fields"""
    REQUIRED_FIELDS = [
        "name",
        "email",
        "phone",
        "location",
        "summary",
    ]

    ALL_FIELDS = {
        "personal": {
            "name": None,
            "email": None,
            "phone": None,
            "location": None,
            "linkedin_url": None,
            "github_url": None,
            "portfolio_url": None,
        },
        "professional": {
            "summary": None,
            "total_experience_years": None,
        },
        "skills": [],
        "certifications": [],
        "experience": [],
        "education": [],
        "projects": [],
        "languages": [],
        "achievements": [],
    }


# Create required directories
os.makedirs(AppConfig.UPLOAD_DIR, exist_ok=True)
os.makedirs(AppConfig.OUTPUT_DIR, exist_ok=True)
