"""Enhanced LLM Provider Abstraction with LangChain Integration"""

import os
import json
import logging
from typing import Optional, Dict, List, Any, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Supported LLM provider types"""
    GEMINI = "gemini"
    OLLAMA = "ollama"
    GROQ = "groq"


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

    def generate(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048, **kwargs
    ) -> LLMResponse:
        """Generate text response from prompt (with cache check and token extraction)"""
        from cv_customizer.utils.redis_cache import redis_cache
        
        cache_key = redis_cache.generate_key(prompt)
        cached_val = redis_cache.get(cache_key)
        
        if cached_val:
            try:
                cached_data = json.loads(cached_val)
                logger.info(f"[Cache Hit] Provider: {self.provider_type.value}, Model: {self.model_name}")
                return LLMResponse(
                    content=cached_data["content"],
                    tokens_used=cached_data.get("tokens_used", {"input": 0, "output": 0, "total": 0}),
                    provider=self.provider_type.value,
                    model=self.model_name,
                    raw_response=None
                )
            except Exception as e:
                logger.warning(f"Failed to parse cached response: {e}")

        # Cache miss, call actual generation
        response = self._generate(prompt, temperature, max_tokens, **kwargs)
        
        # Extract token usage
        tokens = self._extract_tokens(response.raw_response)
        response.tokens_used = tokens
        
        # Log token usage to console
        logger.info(f"[Token Metrics] Provider: {self.provider_type.value}, Model: {self.model_name}, "
                    f"Input Tokens: {tokens.get('input', 0)}, Output Tokens: {tokens.get('output', 0)}, Total: {tokens.get('total', 0)}")
        
        # Save to cache
        try:
            cached_payload = {
                "content": response.content,
                "tokens_used": tokens
            }
            redis_cache.set(cache_key, json.dumps(cached_payload))
        except Exception as e:
            logger.warning(f"Failed to write to cache: {e}")
            
        return response

    @abstractmethod
    def _generate(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048, **kwargs
    ) -> LLMResponse:
        """Actual LLM generation to be implemented by subclass"""
        pass

    def _extract_tokens(self, response: Any) -> dict[str, int]:
        tokens = {"input": 0, "output": 0, "total": 0}
        if not response:
            return tokens
        
        # 1. Try standard LangChain usage_metadata
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            meta = response.usage_metadata
            tokens["input"] = meta.get("input_tokens", 0)
            tokens["output"] = meta.get("output_tokens", 0)
            tokens["total"] = meta.get("total_tokens", tokens["input"] + tokens["output"])
            return tokens

        # 2. Try response_metadata
        metadata = getattr(response, "response_metadata", {}) or {}
        
        # Check for token_usage (OpenAI, Groq)
        token_usage = metadata.get("token_usage")
        if isinstance(token_usage, dict):
            tokens["input"] = token_usage.get("prompt_tokens") or token_usage.get("input_tokens") or 0
            tokens["output"] = token_usage.get("completion_tokens") or token_usage.get("output_tokens") or 0
            tokens["total"] = token_usage.get("total_tokens") or (tokens["input"] + tokens["output"])
            return tokens

        # Check for Anthropic-style usage
        usage = metadata.get("usage")
        if isinstance(usage, dict):
            tokens["input"] = usage.get("input_tokens") or 0
            tokens["output"] = usage.get("output_tokens") or 0
            tokens["total"] = tokens["input"] + tokens["output"]
            return tokens

        # Check for Ollama-style usage in response_metadata
        if "prompt_eval_count" in metadata:
            tokens["input"] = metadata["prompt_eval_count"]
        elif "prompt_tokens" in metadata:
            tokens["input"] = metadata["prompt_tokens"]
        
        if "eval_count" in metadata:
            tokens["output"] = metadata["eval_count"]
        elif "completion_tokens" in metadata:
            tokens["output"] = metadata["completion_tokens"]
        
        # Gemini usage
        gemini_usage = metadata.get("usage_metadata")
        if isinstance(gemini_usage, dict):
            tokens["input"] = gemini_usage.get("prompt_token_count") or gemini_usage.get("input_token_count") or gemini_usage.get("input_tokens") or 0
            tokens["output"] = gemini_usage.get("candidates_token_count") or gemini_usage.get("output_token_count") or gemini_usage.get("output_tokens") or 0
            tokens["total"] = gemini_usage.get("total_token_count") or (tokens["input"] + tokens["output"])
            return tokens

        tokens["total"] = tokens["input"] + tokens["output"]
        return tokens

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available and configured"""
        pass

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize provider with API credentials"""
        pass


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

    def _generate(
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

    def _generate(
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

    def _generate(
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


class LLMProviderFactory:
    """Factory for creating and managing LLM providers with fallback support"""

    _providers: Dict[ProviderType, type[LLMProvider]] = {
        ProviderType.GEMINI: GeminiProvider,
        ProviderType.OLLAMA: OllamaProvider,
        ProviderType.GROQ: GroqProvider,
    }

    _instances: Dict[str, LLMProvider] = {}
    _fallback_chain: List[ProviderType] = [
        ProviderType.GEMINI,
        ProviderType.GROQ,
        ProviderType.OLLAMA,
    ]

    @classmethod
    def get_provider(
        cls, provider_type: ProviderType | str, use_fallback: bool = True, allowed_types: Optional[List[ProviderType]] = None
    ) -> LLMProvider:
        """
        Get LLM provider by type

        Args:
            provider_type: Provider type or name
            use_fallback: Use fallback provider if primary unavailable
            allowed_types: Optional list of allowed ProviderType enums to restrict fallback/primary selection

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

        # Check if requested provider is allowed
        if allowed_types is not None and provider_type not in allowed_types:
            if use_fallback:
                logger.warning(
                    f"{provider_type.value} not allowed for this agent, attempting fallback within allowed types"
                )
                return cls._get_fallback_provider(allowed_types)
            raise ValueError(f"Provider {provider_type.value} is not allowed for this agent.")

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
            return cls._get_fallback_provider(allowed_types)

        raise RuntimeError(f"Provider {provider_type.value} not available")

    @classmethod
    def _get_fallback_provider(cls, allowed_types: Optional[List[ProviderType]] = None) -> LLMProvider:
        """Get first available fallback provider"""
        fallback_chain = cls._fallback_chain
        if allowed_types is not None:
            fallback_chain = [p for p in fallback_chain if p in allowed_types]

        for provider_type in fallback_chain:
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
