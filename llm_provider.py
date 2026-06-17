"""LLM provider chain with automatic fallback."""

import os
from typing import Any, Callable, Iterator, Optional

ProviderFactory = Callable[[], Optional[Any]]

DEFAULT_PROVIDER_ORDER = ("ollama", "gemini", "groq", "claude", "openai")


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


def _try_claude() -> Optional[Any]:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    from langchain_anthropic import ChatAnthropic

    model_name = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    print(f"[LLM] Trying Claude '{model_name}'")
    return ChatAnthropic(model=model_name, api_key=api_key, temperature=0.1)


def _try_openai() -> Optional[Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    from langchain_openai import ChatOpenAI

    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    print(f"[LLM] Trying OpenAI '{model_name}'")
    return ChatOpenAI(model=model_name, api_key=api_key, temperature=0.1)


PROVIDER_FACTORIES: dict[str, ProviderFactory] = {
    "ollama": _try_ollama,
    "gemini": _try_gemini,
    "groq": _try_groq,
    "claude": _try_claude,
    "openai": _try_openai,
}


def get_provider_order() -> tuple[str, ...]:
    configured = os.getenv("LLM_PROVIDER_ORDER")
    if configured:
        return tuple(p.strip().lower() for p in configured.split(",") if p.strip())
    return DEFAULT_PROVIDER_ORDER


def iter_llm_providers() -> Iterator[tuple[str, Any]]:
    """Yield (name, llm) for each provider that can be initialized."""
    for name in get_provider_order():
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


def invoke_with_fallback(messages: list) -> tuple[str, Any]:
    """Invoke messages against providers in order until one succeeds."""
    last_error: Optional[Exception] = None
    for name, llm in iter_llm_providers():
        try:
            print(f"[LLM] Using {name}")
            response = llm.invoke(messages)
            return name, response
        except Exception as e:
            last_error = e
            print(f"[LLM] {name} failed: {e}, falling back...")
    raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")
