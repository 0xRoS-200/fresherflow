"""Enhanced LLM Provider Abstraction with LangChain Integration"""

import os
import logging
from typing import Optional, Dict, List, Any, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Supported LLM provider types"""
    CLAUDE = "claude"
    GEMINI = "gemini"
    CHATGPT = "chatgpt"
    GROQ = "groq"
    OLLAMA = "ollama"
    KIMI = "kimi"


@dataclass
class LLMResponse:
    """Standardized LLM response object"""
    content: str
    tokens_used: Dict[str, int] = None  # {input: x, output: y}
    provider: str = None
    model: str = None
    raw_response: Any = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(self, model_name: str, provider_type: ProviderType):
        self.model_name = model_name
        self.provider_type = provider_type
        self.api_key = None

    @abstractmethod
    def generate(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048, **kwargs
    ) -> LLMResponse:
        """Generate text response from prompt"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available and configured"""
        pass

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize provider with API credentials"""
        pass


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider with LangChain integration"""

    def __init__(self):
        super().__init__("claude-3-sonnet-20240229", ProviderType.CLAUDE)
        self.client = None

    def initialize(self) -> bool:
        """Initialize Claude client"""
        try:
            self.api_key = os.getenv("ANTHROPIC_API_KEY")
            if not self.api_key:
                logger.warning("ANTHROPIC_API_KEY not configured")
                return False

            from langchain_anthropic import ChatAnthropic

            self.client = ChatAnthropic(
                api_key=self.api_key,
                model=self.model_name,
                temperature=0.7,
            )
            logger.info(f"Claude provider initialized with model {self.model_name}")
            return True
        except ImportError:
            logger.error("langchain_anthropic not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Claude: {e}")
            return False

    def generate(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048, **kwargs
    ) -> LLMResponse:
        """Generate response using Claude"""
        if not self.is_available():
            raise RuntimeError("Claude provider not initialized")

        try:
            from langchain_core.messages import HumanMessage

            message = HumanMessage(content=prompt)
            response = self.client.invoke([message])

            return LLMResponse(
                content=response.content,
                provider=self.provider_type.value,
                model=self.model_name,
                raw_response=response,
            )
        except Exception as e:
            logger.error(f"Claude generation failed: {e}")
            raise

    def is_available(self) -> bool:
        return self.client is not None


class GeminiProvider(LLMProvider):
    """Google Gemini provider with LangChain integration"""

    def __init__(self):
        super().__init__("gemini-pro", ProviderType.GEMINI)
        self.client = None

    def initialize(self) -> bool:
        """Initialize Gemini client"""
        try:
            self.api_key = os.getenv("GOOGLE_API_KEY")
            if not self.api_key:
                logger.warning("GOOGLE_API_KEY not configured")
                return False

            from langchain_google_genai import ChatGoogleGenerativeAI

            self.client = ChatGoogleGenerativeAI(
                api_key=self.api_key,
                model=self.model_name,
                temperature=0.7,
            )
            logger.info(f"Gemini provider initialized with model {self.model_name}")
            return True
        except ImportError:
            logger.error("langchain_google_genai not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            return False

    def generate(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048, **kwargs
    ) -> LLMResponse:
        """Generate response using Gemini"""
        if not self.is_available():
            raise RuntimeError("Gemini provider not initialized")

        try:
            from langchain_core.messages import HumanMessage

            message = HumanMessage(content=prompt)
            response = self.client.invoke([message])

            return LLMResponse(
                content=response.content,
                provider=self.provider_type.value,
                model=self.model_name,
                raw_response=response,
            )
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise

    def is_available(self) -> bool:
        return self.client is not None


class ChatGPTProvider(LLMProvider):
    """OpenAI ChatGPT provider with LangChain integration"""

    def __init__(self):
        super().__init__("gpt-4-turbo-preview", ProviderType.CHATGPT)
        self.client = None

    def initialize(self) -> bool:
        """Initialize ChatGPT client"""
        try:
            self.api_key = os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                logger.warning("OPENAI_API_KEY not configured")
                return False

            from langchain_openai import ChatOpenAI

            self.client = ChatOpenAI(
                api_key=self.api_key,
                model=self.model_name,
                temperature=0.7,
            )
            logger.info(f"ChatGPT provider initialized with model {self.model_name}")
            return True
        except ImportError:
            logger.error("langchain_openai not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize ChatGPT: {e}")
            return False

    def generate(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048, **kwargs
    ) -> LLMResponse:
        """Generate response using ChatGPT"""
        if not self.is_available():
            raise RuntimeError("ChatGPT provider not initialized")

        try:
            from langchain_core.messages import HumanMessage

            message = HumanMessage(content=prompt)
            response = self.client.invoke([message])

            return LLMResponse(
                content=response.content,
                provider=self.provider_type.value,
                model=self.model_name,
                raw_response=response,
            )
        except Exception as e:
            logger.error(f"ChatGPT generation failed: {e}")
            raise

    def is_available(self) -> bool:
        return self.client is not None


class GroqProvider(LLMProvider):
    """Groq provider (fast inference) with LangChain integration"""

    def __init__(self):
        super().__init__("mixtral-8x7b-32768", ProviderType.GROQ)
        self.client = None

    def initialize(self) -> bool:
        """Initialize Groq client"""
        try:
            self.api_key = os.getenv("GROQ_API_KEY")
            if not self.api_key:
                logger.warning("GROQ_API_KEY not configured")
                return False

            from langchain_groq import ChatGroq

            self.client = ChatGroq(
                api_key=self.api_key,
                model=self.model_name,
                temperature=0.7,
            )
            logger.info(f"Groq provider initialized with model {self.model_name}")
            return True
        except ImportError:
            logger.error("langchain_groq not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Groq: {e}")
            return False

    def generate(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048, **kwargs
    ) -> LLMResponse:
        """Generate response using Groq"""
        if not self.is_available():
            raise RuntimeError("Groq provider not initialized")

        try:
            from langchain_core.messages import HumanMessage

            message = HumanMessage(content=prompt)
            response = self.client.invoke([message])

            return LLMResponse(
                content=response.content,
                provider=self.provider_type.value,
                model=self.model_name,
                raw_response=response,
            )
        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            raise

    def is_available(self) -> bool:
        return self.client is not None


class OllamaProvider(LLMProvider):
    """Ollama provider (local/self-hosted) with LangChain integration"""

    def __init__(self, model: str = "llama2"):
        super().__init__(model, ProviderType.OLLAMA)
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.client = None

    def initialize(self) -> bool:
        """Initialize Ollama client"""
        try:
            from langchain_ollama import ChatOllama
            import requests

            # Check if Ollama is running
            headers = {}
            if "ngrok" in self.base_url.lower():
                headers["ngrok-skip-browser-warning"] = "true"

            try:
                # Strip trailing slash from base_url to avoid duplicate slashes
                clean_url = self.base_url.rstrip('/')
                resp = requests.get(f"{clean_url}/api/tags", headers=headers, timeout=5)
                if resp.status_code != 200:
                    logger.warning(f"Ollama server not responding at {self.base_url} (status code {resp.status_code})")
                    return False
            except requests.RequestException as e:
                logger.warning(f"Cannot connect to Ollama at {self.base_url}: {e}")
                return False

            client_kwargs = {}
            if headers:
                client_kwargs["client_kwargs"] = {"headers": headers}

            self.client = ChatOllama(
                base_url=self.base_url,
                model=self.model_name,
                temperature=0.7,
                **client_kwargs
            )
            logger.info(f"Ollama provider initialized with model {self.model_name}")
            return True
        except ImportError:
            logger.error("langchain_ollama not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Ollama: {e}")
            return False

    def generate(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048, **kwargs
    ) -> LLMResponse:
        """Generate response using Ollama"""
        if not self.is_available():
            raise RuntimeError("Ollama provider not initialized")

        try:
            from langchain_core.messages import HumanMessage

            message = HumanMessage(content=prompt)
            response = self.client.invoke([message])

            return LLMResponse(
                content=response.content,
                provider=self.provider_type.value,
                model=self.model_name,
                raw_response=response,
            )
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    def is_available(self) -> bool:
        return self.client is not None


class KimiProvider(LLMProvider):
    """Kimi (Moonshot) provider with LangChain integration"""

    def __init__(self):
        super().__init__("moonshot-v1", ProviderType.KIMI)
        self.client = None

    def initialize(self) -> bool:
        """Initialize Kimi client"""
        try:
            self.api_key = os.getenv("KIMI_API_KEY")
            if not self.api_key:
                logger.warning("KIMI_API_KEY not configured")
                return False

            # Using OpenAI-compatible API wrapper for Kimi
            from langchain_openai import ChatOpenAI

            self.client = ChatOpenAI(
                api_key=self.api_key,
                base_url="https://api.moonshot.cn/v1",
                model="moonshot-v1",
                temperature=0.7,
            )
            logger.info(f"Kimi provider initialized with model {self.model_name}")
            return True
        except ImportError:
            logger.error("langchain_openai not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Kimi: {e}")
            return False

    def generate(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048, **kwargs
    ) -> LLMResponse:
        """Generate response using Kimi"""
        if not self.is_available():
            raise RuntimeError("Kimi provider not initialized")

        try:
            from langchain_core.messages import HumanMessage

            message = HumanMessage(content=prompt)
            response = self.client.invoke([message])

            return LLMResponse(
                content=response.content,
                provider=self.provider_type.value,
                model=self.model_name,
                raw_response=response,
            )
        except Exception as e:
            logger.error(f"Kimi generation failed: {e}")
            raise

    def is_available(self) -> bool:
        return self.client is not None


class LLMProviderFactory:
    """Factory for creating and managing LLM providers with fallback support"""

    _providers: Dict[ProviderType, type[LLMProvider]] = {
        ProviderType.CLAUDE: ClaudeProvider,
        ProviderType.GEMINI: GeminiProvider,
        ProviderType.CHATGPT: ChatGPTProvider,
        ProviderType.GROQ: GroqProvider,
        ProviderType.OLLAMA: OllamaProvider,
        ProviderType.KIMI: KimiProvider,
    }

    _instances: Dict[str, LLMProvider] = {}
    _fallback_chain: List[ProviderType] = [
        ProviderType.GROQ,
        ProviderType.OLLAMA,
        ProviderType.CLAUDE,
        ProviderType.GEMINI,
        ProviderType.CHATGPT,
    ]

    @classmethod
    def get_provider(
        cls, provider_type: ProviderType | str, use_fallback: bool = True
    ) -> LLMProvider:
        """
        Get LLM provider by type

        Args:
            provider_type: Provider type or name
            use_fallback: Use fallback provider if primary unavailable

        Returns:
            Initialized LLM provider

        Raises:
            ValueError: If provider type invalid
            RuntimeError: If no available provider found
        """
        if isinstance(provider_type, str):
            try:
                provider_type = ProviderType(provider_type.lower())
            except ValueError:
                raise ValueError(f"Unknown provider: {provider_type}")

        # Check if already initialized
        if provider_type.value in cls._instances:
            provider = cls._instances[provider_type.value]
            if provider.is_available():
                logger.debug(f"Using cached provider: {provider_type.value}")
                return provider

        # Create new instance
        provider_class = cls._providers.get(provider_type)
        if not provider_class:
            raise ValueError(f"Unsupported provider: {provider_type}")

        provider = provider_class()
        if provider.initialize():
            cls._instances[provider_type.value] = provider
            logger.info(f"Provider initialized: {provider_type.value}")
            return provider

        # Fallback to alternative provider
        if use_fallback:
            logger.warning(
                f"{provider_type.value} not available, attempting fallback"
            )
            return cls._get_fallback_provider()

        raise RuntimeError(f"Provider {provider_type.value} not available")

    @classmethod
    def _get_fallback_provider(cls) -> LLMProvider:
        """Get first available fallback provider"""
        for provider_type in cls._fallback_chain:
            try:
                provider_class = cls._providers.get(provider_type)
                if provider_class:
                    provider = provider_class()
                    if provider.initialize():
                        logger.info(f"Using fallback provider: {provider_type.value}")
                        return provider
            except Exception as e:
                logger.debug(f"Fallback attempt failed for {provider_type.value}: {e}")
                continue

        raise RuntimeError("No available LLM provider found")

    @classmethod
    def register_provider(
        cls, provider_type: ProviderType, provider_class: type[LLMProvider]
    ) -> None:
        """Register custom provider"""
        cls._providers[provider_type] = provider_class
        logger.info(f"Registered custom provider: {provider_type.value}")

    @classmethod
    def list_providers(cls) -> Dict[str, bool]:
        """List all providers and their availability"""
        status = {}
        for provider_type in ProviderType:
            try:
                provider_class = cls._providers.get(provider_type)
                if provider_class:
                    provider = provider_class()
                    status[provider_type.value] = provider.is_available()
            except Exception:
                status[provider_type.value] = False
        return status

    @classmethod
    def reset(cls) -> None:
        """Reset all cached providers"""
        cls._instances.clear()
        logger.info("Provider instances cleared")
