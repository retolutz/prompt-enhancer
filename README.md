# Prompt Enhancer

Transform basic prompts into professional-grade prompts using the best AI models.

## Features

- **Single Model**: Use o3 (OpenAI) for fast enhancement
- **LLM Council**: Use 3 models in parallel (o3 + Claude Opus 4 + Gemini 2.5 Pro) with intelligent aggregation
- **10 Enhancement Strategies**: Master, role injection, chain-of-thought, and more
- **Prompt Analysis**: Analyze prompts for ambiguities and improvements

## Models Used

| Provider | Model | Role |
|----------|-------|------|
| OpenAI | **o3** | Best reasoning model |
| Anthropic | **Claude Opus 4** | Best Claude + Aggregator |
| Google | **Gemini 2.5 Pro** | Best Gemini model |

## Installation

```bash
pip install -e .
```

## Setup

```bash
cp .env.example .env
```

Add your API keys to `.env`:
```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
```

## Usage

### LLM Council (Recommended for important prompts)

Uses all 3 models in parallel, then aggregates the best result:

```bash
prompt-enhancer council "Write a business plan for an AI startup"

# Show all individual responses
prompt-enhancer council -a "Create a marketing strategy"
```

### Single Model Enhancement

Fast enhancement using o3:

```bash
prompt-enhancer enhance "Write a blog post about AI"

# With comparison analysis
prompt-enhancer enhance -c "Create a marketing strategy"

# Interactive mode
prompt-enhancer enhance -i

# Specific strategy
prompt-enhancer enhance -s role "Help me code"
prompt-enhancer enhance -s cot "Solve this problem"
```

### Iterative Enhancement

Apply multiple strategies sequentially:

```bash
prompt-enhancer iterative "Build an app"
```

### Analyze a Prompt

```bash
prompt-enhancer analyze "Make my website faster"
```

## LLM Council Architecture

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   o3 (OpenAI)   │  │ Claude Opus 4   │  │ Gemini 2.5 Pro  │
│    Reasoning    │  │    Synthesis    │  │    Creative     │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └───────────── parallel ─────────────────┘
                              │
                              ▼
                   ┌──────────────────────┐
                   │   Claude Opus 4      │
                   │   (Aggregator)       │
                   │   Selects/merges     │
                   │   best elements      │
                   └──────────┬───────────┘
                              │
                              ▼
                   ┌──────────────────────┐
                   │   Final Prompt       │
                   └──────────────────────┘
```

## Available Strategies

| Strategy | Description |
|----------|-------------|
| `master` | **Comprehensive enhancement (recommended)** |
| `semantic` | Analyze semantic components |
| `role` | Add expert persona |
| `constraint` | Add MUST/MUST NOT rules |
| `cot` | Chain-of-thought reasoning |
| `context` | Full context saturation |
| `decompose` | Break into sub-tasks |
| `output` | Specify output format |
| `fewshot` | Add examples |
| `refine` | Self-critique loop |

## Example

**Input:**
```
Schreibe einen LinkedIn Post über KI
```

**Output (Council):**
```
Du bist ein erfahrener deutschsprachiger LinkedIn Content Creator
mit nachweislicher Expertise in Tech-Themen und viralen B2B-Posts.

**STRUKTURVORGABEN:**
1. Hook (erste 2 Zeilen): Starke, überraschende Aussage
2. Story/Insight (2-3 Absätze): Persönliche Anekdote oder Datenpunkt
3. Praktischer Nutzen: 3-5 konkrete Takeaways
4. Call-to-Action: Engagementfördernde Frage

**FORMATVORGABEN:**
- Länge: 150-250 Wörter
- Kurze Absätze (max. 2-3 Sätze)
- 1 passendes Emoji pro Absatz
- 3-5 relevante Hashtags am Ende

**VIRALITÄTSFAKTOREN:**
- Polarisierend ohne unsachlich zu sein
- Emotionaler Bezug
- Diskussionsanregend und teilbar
```

## Python API

```python
# Single model
from enhancer import PromptEnhancer

enhancer = PromptEnhancer()
result = enhancer.enhance("Your prompt", strategy="master")
print(result.enhanced_prompt)

# LLM Council
from council import LLMCouncil

council = LLMCouncil()
result = council.enhance("Your prompt")
print(result.enhanced_prompt)
print(result.aggregator_reasoning)

# Access individual responses
for member in result.members:
    print(f"{member.name}: {member.response[:100]}...")
```

## Council Agents

### Project Council (Deep Context)

The most powerful mode - analyzes your entire project and asks clarifying questions:

```bash
# Interactive mode - council asks questions to understand your task
python project_council.py

# With specific task
python project_council.py --task "Add authentication"

# Quick mode (skip questions)
python project_council.py ask "How should I structure the API?" --quick

# Just analyze project
python project_council.py --analyze
```

**How it works:**
1. Analyzes project structure, dependencies, framework
2. Each LLM generates 5 clarifying questions
3. Reads relevant code files based on your answers
4. Council deliberates with full context
5. Synthesizes project-aware recommendations

### Council Agent (Standalone CLI)

Direct council access for specific tasks:

```bash
# Code review
python council_agent.py review path/to/file.py

# Architecture decision
python council_agent.py architect "Should I use microservices?"

# Debug help
python council_agent.py debug "App crashes on login" --code auth.py

# Security audit
python council_agent.py security api.py

# General question
python council_agent.py ask "Best caching strategy?"

# Check status
python council_agent.py status
```

### MCP Server (Claude Code Integration)

Integrate the council directly into Claude Code:

1. Create `.mcp.json` in your project:
```json
{
  "mcpServers": {
    "council": {
      "command": "python",
      "args": ["/path/to/mcp_council_server.py"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "GOOGLE_API_KEY": "AIza..."
      }
    }
  }
}
```

2. Restart Claude Code - now you can say:
   - "Ask the council to review this code"
   - "Get the council's opinion on this architecture"

## Based On

Research from top prompt engineering projects:
- [AI-Prompt-Enhancer](https://github.com/Pythonation/AI-Prompt-Enhancer) - DSE v7.0 cognitive architecture
- [AutoPrompt](https://github.com/Eladlev/AutoPrompt) - Intent-based calibration
- [MCP Prompt Optimizer](https://github.com/Bubobot-Team/mcp-prompt-optimizer) - Research-backed strategies

## License

MIT
