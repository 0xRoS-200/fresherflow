"""LLM provider chain with automatic fallback."""

import os
import json
from typing import Any, Callable, Iterator, Optional

ProviderFactory = Callable[[], Optional[Any]]

DEFAULT_PROVIDER_ORDER = ("gemini", "groq", "ollama")


def _try_ollama() -> Optional[Any]:
    from langchain_ollama import ChatOllama

    model_name = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    print(f"[LLM] Trying Ollama '{model_name}' at {base_url}")
    
    kwargs = {}
    if "ngrok" in base_url.lower():
        kwargs["client_kwargs"] = {"headers": {"ngrok-skip-browser-warning": "true"}}
        
    return ChatOllama(model=model_name, base_url=base_url, temperature=0.1, **kwargs)


def _try_gemini() -> Optional[Any]:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    from langchain_google_genai import ChatGoogleGenerativeAI

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    print(f"[LLM] Trying Gemini '{model_name}'")
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.1,
    )


def _try_groq() -> Optional[Any]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None

    from langchain_groq import ChatGroq

    model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    print(f"[LLM] Trying Groq '{model_name}'")
    return ChatGroq(model=model_name, groq_api_key=api_key, temperature=0.1)


PROVIDER_FACTORIES: dict[str, ProviderFactory] = {
    "gemini": _try_gemini,
    "ollama": _try_ollama,
    "groq": _try_groq,
}


def get_provider_order() -> tuple[str, ...]:
    configured = os.getenv("LLM_PROVIDER_ORDER")
    if configured:
        return tuple(p.strip().lower() for p in configured.split(",") if p.strip())
    return DEFAULT_PROVIDER_ORDER


def iter_llm_providers(allowed_providers: Optional[list[str]] = None) -> Iterator[tuple[str, Any]]:
    """Yield (name, llm) for each provider that can be initialized."""
    for name in get_provider_order():
        if allowed_providers is not None and name not in allowed_providers:
            continue
        factory = PROVIDER_FACTORIES.get(name)
        if not factory:
            print(f"[LLM] Unknown provider '{name}', skipping")
            continue
        try:
            llm = factory()
            if llm is not None:
                yield name, llm
        except Exception as e:
            print(f"[LLM] Could not initialize {name}: {e}")


def invoke_with_fallback(messages: list, allowed_providers: Optional[list[str]] = None) -> tuple[str, Any]:
    """Invoke messages against providers in order until one succeeds (with caching and token tracking)."""
    from cv_customizer.utils.redis_cache import redis_cache
    from langchain_core.messages import AIMessage
    
    # 1. Cache lookup
    cache_key = redis_cache.generate_messages_key(messages)
    cached_val = redis_cache.get(cache_key)
    if cached_val:
        try:
            cached_data = json.loads(cached_val)
            provider_name = cached_data.get("provider")
            if allowed_providers is None or provider_name in allowed_providers:
                print(f"[Cache Hit] Fallback chain hit (Provider: {provider_name})")
                mock_response = AIMessage(content=cached_data["content"])
                return provider_name, mock_response
        except Exception as e:
            print(f"[LLM] Failed to parse cached fallback response: {e}")

    # 2. Actual invocation loop
    last_error: Optional[Exception] = None
    for name, llm in iter_llm_providers(allowed_providers):
        try:
            print(f"[LLM] Using {name}")
            response = llm.invoke(messages)
            
            # Extract token metrics
            tokens = _extract_tokens_fallback(response)
            print(f"[Token Metrics] Provider: {name}, Input: {tokens.get('input', 0)}, Output: {tokens.get('output', 0)}, Total: {tokens.get('total', 0)}")
            
            # Save to cache
            try:
                cached_payload = {
                    "content": response.content,
                    "provider": name,
                    "tokens_used": tokens
                }
                redis_cache.set(cache_key, json.dumps(cached_payload))
            except Exception as e:
                print(f"[LLM] Failed to cache fallback response: {e}")
                
            return name, response
        except Exception as e:
            last_error = e
            print(f"[LLM] {name} failed: {e}, falling back...")
            
    raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")


def _extract_tokens_fallback(response: Any) -> dict[str, int]:
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
