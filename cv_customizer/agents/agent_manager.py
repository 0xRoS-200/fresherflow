"""Agent Initialization and Management"""

import logging
from typing import Dict, Optional
from cv_customizer.agents.llm_provider import LLMProviderFactory, ProviderType
from cv_customizer.config import LLMConfig

logger = logging.getLogger(__name__)


class AgentManager:
    """Manages agent initialization and lifecycle"""

    _agents = {}

    @classmethod
    def initialize_parser_agent(cls):
        """Initialize Parser Agent (Agent 1)"""
        try:
            from cv_customizer.agents.parser_agent import ParserAgent

            provider = LLMProviderFactory.get_provider(
                LLMConfig.PARSER_PROVIDER,
                allowed_types=[ProviderType.GEMINI, ProviderType.GROQ]
            )
            agent = ParserAgent(provider=provider)
            cls._agents["parser"] = agent
            logger.info(f"Parser Agent initialized with {provider.provider_type.value} (requested: {LLMConfig.PARSER_PROVIDER})")
            return agent
        except Exception as e:
            logger.error(f"Failed to initialize Parser Agent: {e}")
            raise

    @classmethod
    def initialize_job_search_agent(cls):
        """Initialize Job Search Agent (Agent 2)"""
        try:
            from cv_customizer.agents.job_search_agent import JobSearchAgent

            provider = LLMProviderFactory.get_provider(
                LLMConfig.JOB_SEARCH_PROVIDER,
                allowed_types=[ProviderType.GEMINI, ProviderType.GROQ]
            )
            agent = JobSearchAgent(provider=provider)
            cls._agents["job_search"] = agent
            logger.info(f"Job Search Agent initialized with {provider.provider_type.value} (requested: {LLMConfig.JOB_SEARCH_PROVIDER})")
            return agent
        except Exception as e:
            logger.error(f"Failed to initialize Job Search Agent: {e}")
            raise

    @classmethod
    def initialize_cv_tailor_agent(cls):
        """Initialize CV Tailor Agent (Agent 3)"""
        try:
            from cv_customizer.agents.cv_tailor_agent import CVTailorAgent

            provider = LLMProviderFactory.get_provider(
                LLMConfig.CV_TAILOR_PROVIDER,
                allowed_types=[ProviderType.OLLAMA, ProviderType.GEMINI, ProviderType.GROQ]
            )
            agent = CVTailorAgent(provider=provider)
            cls._agents["cv_tailor"] = agent
            logger.info(f"CV Tailor Agent initialized with {provider.provider_type.value} (requested: {LLMConfig.CV_TAILOR_PROVIDER})")
            return agent
        except Exception as e:
            logger.error(f"Failed to initialize CV Tailor Agent: {e}")
            raise

    @classmethod
    def initialize_all_agents(cls):
        """Initialize all three agents"""
        agents = {}
        try:
            agents["parser"] = cls.initialize_parser_agent()
        except Exception as e:
            logger.warning(f"Parser Agent initialization failed: {e}")

        try:
            agents["job_search"] = cls.initialize_job_search_agent()
        except Exception as e:
            logger.warning(f"Job Search Agent initialization failed: {e}")

        try:
            agents["cv_tailor"] = cls.initialize_cv_tailor_agent()
        except Exception as e:
            logger.warning(f"CV Tailor Agent initialization failed: {e}")

        return agents

    @classmethod
    def get_agent(cls, agent_name: str):
        """Get initialized agent by name"""
        if agent_name not in cls._agents:
            raise ValueError(f"Agent not found: {agent_name}")
        return cls._agents[agent_name]

    @classmethod
    def get_all_agents(cls) -> Dict:
        """Get all initialized agents"""
        return cls._agents.copy()


class ProviderStatus:
    """Check and report provider availability"""

    @staticmethod
    def check_all_providers() -> Dict[str, bool]:
        """Check all provider availability"""
        return LLMProviderFactory.list_providers()

    @staticmethod
    def get_status_report() -> str:
        """Get detailed status report"""
        status = ProviderStatus.check_all_providers()
        available = [p for p, v in status.items() if v]
        unavailable = [p for p, v in status.items() if not v]

        report = "\n📋 LLM Provider Status Report\n"
        report += "=" * 50 + "\n\n"

        if available:
            report += "✅ Available Providers:\n"
            for provider in available:
                report += f"  • {provider}\n"
        else:
            report += "❌ No providers available\n"

        report += "\n"

        if unavailable:
            report += "❌ Unavailable Providers:\n"
            for provider in unavailable:
                report += f"  • {provider}\n"

        report += "\n" + "=" * 50

        return report

    @staticmethod
    def print_status():
        """Print status report"""
        print(ProviderStatus.get_status_report())


class AgentConfig:
    """Configuration for agent providers"""

    PROVIDER_CONFIGS = {
        "parser": {
            "primary": "gemini",
            "fallback": ["groq", "ollama"],
            "temperature": 0.3,
            "max_tokens": 4000,
        },
        "job_search": {
            "primary": "groq",
            "fallback": ["gemini", "ollama"],
            "temperature": 0.5,
            "max_tokens": 3000,
        },
        "cv_tailor": {
            "primary": "ollama",
            "fallback": ["gemini", "groq"],
            "temperature": 0.7,
            "max_tokens": 5000,
        },
    }

    @staticmethod
    def get_config(agent_name: str) -> Dict:
        """Get configuration for specific agent"""
        if agent_name not in AgentConfig.PROVIDER_CONFIGS:
            raise ValueError(f"Unknown agent: {agent_name}")
        return AgentConfig.PROVIDER_CONFIGS[agent_name]

    @staticmethod
    def get_primary_provider(agent_name: str) -> str:
        """Get primary provider for agent"""
        config = AgentConfig.get_config(agent_name)
        return config["primary"]

    @staticmethod
    def get_provider_params(agent_name: str) -> Dict:
        """Get LLM parameters for agent"""
        config = AgentConfig.get_config(agent_name)
        return {
            "temperature": config.get("temperature", 0.7),
            "max_tokens": config.get("max_tokens", 2048),
        }
