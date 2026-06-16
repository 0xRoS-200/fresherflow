# LLM Provider Abstraction Layer Documentation

## Overview

The **LLM Provider Abstraction Layer** provides a unified interface for using multiple LLM providers across the CV Customizer system. It features:

- ✅ Support for 6+ LLM providers
- ✅ Automatic fallback mechanism
- ✅ LangChain integration
- ✅ Provider caching and lifecycle management
- ✅ Standardized response format

## Supported Providers

| Provider | Model | Speed | Cost | Local | API Key |
|----------|-------|-------|------|-------|---------|
| **Claude** | claude-3-sonnet | Moderate | Moderate | ❌ | ANTHROPIC_API_KEY |
| **Gemini** | gemini-pro | Fast | Low | ❌ | GOOGLE_API_KEY |
| **ChatGPT** | gpt-4-turbo | Moderate | High | ❌ | OPENAI_API_KEY |
| **Groq** | mixtral-8x7b | ⚡ Very Fast | Low/Free | ❌ | GROQ_API_KEY |
| **Ollama** | llama2 (custom) | Slow | Free | ✅ | None |
| **Kimi** | moonshot-v1 | Fast | Moderate | ❌ | KIMI_API_KEY |

## Quick Start

### 1. Initialize Providers

```python
from cv_customizer.agents.llm_provider import LLMProviderFactory, ProviderType

# Get Claude provider
provider = LLMProviderFactory.get_provider(ProviderType.CLAUDE)

# Or by string name
provider = LLMProviderFactory.get_provider("claude")
```

### 2. Generate Response

```python
from cv_customizer.agents.llm_provider import LLMResponse

response = provider.generate(
    prompt="Extract skills from this resume...",
    temperature=0.3,
    max_tokens=2000
)

print(response.content)  # Generated text
print(response.provider)  # Which provider was used
print(response.model)     # Model name
```

### 3. Handle Fallback

```python
# Automatic fallback if Claude unavailable
try:
    provider = LLMProviderFactory.get_provider("claude", use_fallback=True)
except RuntimeError:
    print("No providers available")
```

## Agent Integration

### Parser Agent (Agent 1)
```python
from cv_customizer.agents.parser_agent import ParserAgent
from cv_customizer.agents.llm_provider import LLMProviderFactory

provider = LLMProviderFactory.get_provider("gemini")
parser = ParserAgent(provider=provider)

master_cv = parser.generate_master_cv(extracted_data)
```

### Job Search Agent (Agent 2)
```python
from cv_customizer.agents.job_search_agent import JobSearchAgent

provider = LLMProviderFactory.get_provider("claude")
job_agent = JobSearchAgent(provider=provider)

jobs = job_agent.search_jobs(["Python", "FastAPI"])
```

### CV Tailor Agent (Agent 3)
```python
from cv_customizer.agents.cv_tailor_agent import CVTailorAgent

provider = LLMProviderFactory.get_provider("chatgpt")
tailor_agent = CVTailorAgent(provider=provider)

tailored = tailor_agent.tailor_cv_content(master_cv, job_data)
```

## Configuration

### Environment Variables

```bash
# Required for respective providers
ANTHROPIC_API_KEY=sk-ant-xxxxx
GOOGLE_API_KEY=AIza-xxxxx
OPENAI_API_KEY=sk-xxxxx
GROQ_API_KEY=gsk-xxxxx
KIMI_API_KEY=sk-xxxxx

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
```

### Agent-Specific Providers

Set in `.env`:
```
PARSER_LLM_PROVIDER=gemini      # Data extraction
JOB_SEARCH_LLM_PROVIDER=claude  # Job analysis
CV_TAILOR_LLM_PROVIDER=chatgpt  # CV wording
```

### Temperature & Tokens

Each agent has configured defaults:

```python
from cv_customizer.agents.agent_manager import AgentConfig

# Parser Agent (conservative)
config = AgentConfig.get_config("parser")
# {"temperature": 0.3, "max_tokens": 4000}

# CV Tailor Agent (creative)
config = AgentConfig.get_config("cv_tailor")
# {"temperature": 0.7, "max_tokens": 5000}
```

## Standardized Response Format

All providers return `LLMResponse`:

```python
@dataclass
class LLMResponse:
    content: str                           # Generated text
    tokens_used: Dict[str, int] = None    # {input: 150, output: 200}
    provider: str = None                  # "claude", "gemini", etc.
    model: str = None                     # "claude-3-sonnet"
    raw_response: Any = None              # Original provider response
```

## Provider Availability Check

```python
from cv_customizer.agents.agent_manager import ProviderStatus

# Check all providers
status = ProviderStatus.check_all_providers()
# {"claude": True, "gemini": False, ...}

# Print status report
ProviderStatus.print_status()
# 📋 LLM Provider Status Report
# ✅ Available Providers:
#   • claude
#   • groq
# ❌ Unavailable Providers:
#   • gemini
#   ...
```

## Agent Manager

```python
from cv_customizer.agents.agent_manager import AgentManager

# Initialize all agents
agents = AgentManager.initialize_all_agents()

# Get specific agent
parser = AgentManager.get_agent("parser")

# Get all initialized agents
all_agents = AgentManager.get_all_agents()
```

## LangGraph Workflows

Each agent uses LangGraph for orchestration:

### Parser Agent Workflow
```
START
  ↓
validate_input (Check file)
  ↓
extract_data (PDF/web scraping)
  ↓
structure_cv (Map to schema)
  ↓
fill_missing (Add null values)
  ↓
validate_cv (Quality check)
  ↓
END
```

### Job Search Agent Workflow
```
START
  ↓
load_cv (Get Master CV)
  ↓
extract_keywords (Parse requirements)
  ↓
search_jobs (Find listings)
  ↓
extract_job_metadata (Parse job details)
  ↓
calculate_ats_scores (Score each job)
  ↓
rank_jobs (Sort by match)
  ↓
END
```

### CV Tailor Agent Workflow
```
START
  ↓
load_cv_and_job (Load inputs)
  ↓
tailor_content (Customize for job)
  ↓
generate_latex (Create LaTeX)
  ↓
check_ats_score (Quality check)
  ↓
reconfigure_if_needed ← (Loop if score < 95%)
  ↓
sync_to_overleaf (Export)
  ↓
END
```

## Fallback Chain

When primary provider unavailable, tries in order:

1. Groq (fastest, free tier)
2. Ollama (local, free)
3. Claude (high quality)
4. Gemini (fast)
5. ChatGPT (slower)

### Override Fallback

```python
# Disable fallback, raise error instead
provider = LLMProviderFactory.get_provider("claude", use_fallback=False)

# Reset cached instances
LLMProviderFactory.reset()
```

## Custom Provider

```python
from cv_customizer.agents.llm_provider import LLMProvider, ProviderType, LLMResponse

class CustomProvider(LLMProvider):
    def __init__(self):
        super().__init__("my-model", ProviderType.CLAUDE)  # Use enum or create new
    
    def initialize(self) -> bool:
        # Your initialization
        return True
    
    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        # Your implementation
        return LLMResponse(content="...", provider="custom")
    
    def is_available(self) -> bool:
        return True

# Register custom provider
LLMProviderFactory.register_provider(ProviderType.CLAUDE, CustomProvider)
```

## Error Handling

```python
from cv_customizer.agents.llm_provider import LLMProviderFactory

try:
    provider = LLMProviderFactory.get_provider("claude")
    response = provider.generate("Your prompt")
except ValueError as e:
    print(f"Unknown provider: {e}")
except RuntimeError as e:
    print(f"No providers available: {e}")
except Exception as e:
    print(f"Generation failed: {e}")
```

## Performance Considerations

### Temperature Settings
- **0.1-0.3** (low): For data extraction, parsing (deterministic)
- **0.5-0.7** (medium): For job analysis, filtering (balanced)
- **0.8-1.0** (high): For CV tailoring, creative writing

### Max Tokens
- **Parser Agent**: 4000 tokens (verbose extraction)
- **Job Search Agent**: 3000 tokens (metadata)
- **CV Tailor Agent**: 5000 tokens (comprehensive content)

### Response Caching
```python
# Providers are cached automatically
provider1 = LLMProviderFactory.get_provider("claude")
provider2 = LLMProviderFactory.get_provider("claude")
assert provider1 is provider2  # Same instance
```

## Monitoring & Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("cv_customizer.agents.llm_provider")

# Will log:
# INFO: Claude provider initialized with model claude-3-sonnet-20240229
# INFO: Provider initialized: claude
# DEBUG: Using cached provider: claude
# WARNING: claude not available, attempting fallback
# INFO: Using fallback provider: groq
```

## File Reference

- **LLM Provider**: `cv_customizer/agents/llm_provider.py`
- **Workflows**: `cv_customizer/agents/workflows.py`
- **Parser Agent**: `cv_customizer/agents/parser_agent.py`
- **Job Search Agent**: `cv_customizer/agents/job_search_agent.py`
- **CV Tailor Agent**: `cv_customizer/agents/cv_tailor_agent.py`
- **Agent Manager**: `cv_customizer/agents/agent_manager.py`

## Next Steps

Feature 4: **Parser Agent Implementation** - Full PDF parsing + portfolio scraping
