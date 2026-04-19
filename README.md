# LLM Council

Ask three top AI models in parallel, get three independent answers. Built for high-impact decisions where a single model can be wrong in expensive ways.

---

## What it does

You send one question. Three models answer it independently. You (or the calling session) synthesize the three answers into a single recommendation.

No server-side aggregation — the raw responses come back to you. This keeps the architecture simple, the cost lower, and gives the caller full context when deciding how to weight each response.

Works as:
- A **CLI tool** for quick one-off consultations
- A **project-aware agent** that reads your codebase first
- An **MCP server** that plugs directly into Claude Code

---

## Why use it

- **Blind spots get smaller.** Different model families are wrong about different things.
- **Disagreement is a signal.** When the council splits, you learn where the real trade-offs are.
- **Synthesis beats voting.** You see the full reasoning of each model and decide.

Not a silver bullet. Good for architecture choices, security reviews, hard bugs. Overkill for renaming a variable.

---

## The council

| Provider | Model | Role |
|----------|-------|------|
| OpenAI | `gpt-5.4` | Deep reasoning, complex logic |
| Anthropic | `claude-opus-4-7` | Nuance, synthesis |
| Google | `gemini-3-pro-preview` | Breadth, creative solutions |

All three can also be configured to use live web search (see _Research mode_ below).

---

## Quick start

```bash
git clone https://github.com/retolutz/llm-council.git
cd llm-council
pip install -r requirements.txt
cp .env.example .env
# Open .env and add your three API keys
```

First consultation:

```bash
python council_agent.py ask "Should we split this monolith now or later?"
```

---

## How to use it

### Option 1 — Quick CLI

For one-off questions. Fastest to get started.

```bash
# General question
python council_agent.py ask "Redis vs Memcached for a high-traffic API?"

# Code review
python council_agent.py review src/auth.py --focus security

# Architecture decision
python council_agent.py architect "Microservices or modular monolith for a 4-person team?"

# Debug help
python council_agent.py debug "App crashes on login, memory spikes to 4GB"

# Security audit
python council_agent.py security src/api/ --context "Public-facing REST API"

# Refactor suggestions
python council_agent.py refactor legacy/old_service.py --goals "modernize, add tests"

# Interactive session
python council_agent.py interactive

# Check which models are configured
python council_agent.py status
```

### Option 2 — Project-aware council

The council reads your codebase before answering. Slower, better for non-trivial changes.

```bash
# Interactive: council asks clarifying questions first
python project_council.py

# With a specific task
python project_council.py --task "Add JWT authentication with refresh tokens"

# Skip clarifying questions
python project_council.py ask "How should I structure the API layer?" --quick

# Just analyze the project structure
python project_council.py --analyze
```

### Option 3 — Claude Code integration (MCP)

Make the council available as tools inside Claude Code. Once set up, any Claude Code session can call the council tools below.

**Standard tools** (fast, no web search):

| Tool | Use case |
|------|----------|
| `council_ask` | General questions, research, planning |
| `council_review` | Code quality, bugs, best practices |
| `council_architecture` | System design, tech stack choices |
| `council_debug` | Root cause analysis for complex issues |
| `council_security` | OWASP-style audits, auth patterns |
| `council_refactor` | Modernization, reducing technical debt |

**Research tools** (slower, web search enabled on all three models):

| Tool | Use case |
|------|----------|
| `council_research_ask` | Questions that need current information (versions, prices, news) |
| `council_research_architecture` | Tech decisions where the landscape shifts fast |
| `council_research_security` | Audits that need current CVE / advisory data |

**Global install (all projects):**

```bash
claude mcp add council python /path/to/llm-council/mcp_council_server.py \
  --scope user \
  -e "OPENAI_API_KEY=sk-..." \
  -e "ANTHROPIC_API_KEY=sk-ant-..." \
  -e "GOOGLE_API_KEY=AIza..."
```

**Per-project install** — drop this in your project root as `.mcp.json`:

```json
{
  "mcpServers": {
    "council": {
      "command": "python",
      "args": ["/path/to/llm-council/mcp_council_server.py"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "GOOGLE_API_KEY": "AIza..."
      }
    }
  }
}
```

Restart Claude Code. Then in any session:

> "Ask the council to review this authentication code."
> "Get the council's opinion on GraphQL vs REST for our use case."
> "Have the council research the current stable Stripe API version and any recent breaking changes."

---

## Standard mode vs Research mode

| | Standard | Research |
|---|---|---|
| Web search | Off | On (all three models) |
| Latency | ~5-20s | ~30-90s |
| Cost per call | ~$0.20-0.90 | ~$0.60-2.50 |
| Best for | Architecture, code review, debugging | Current versions, pricing, advisories, recent news |

Standard mode uses the models' training knowledge — reliable for timeless concepts, unreliable for anything that changed recently. Research mode costs more and takes longer, but every answer is grounded in sources the model fetched at call time.

---

## When to use the council

**Yes:**
- Architecture or framework choices you will live with for months
- Security-critical code before it ships
- Complex bugs where the root cause is unclear
- Decisions where being wrong is expensive

**No:**
- Simple refactors or renames
- Time-sensitive production fixes
- Trivia a search engine answers
- Budget-constrained routine work

---

## Cost per consultation

Three model calls in parallel. No server-side aggregation — the calling session synthesizes.

| Step | Standard | Research |
|------|----------|----------|
| GPT-5.4 | $0.05 - $0.30 | $0.15 - $0.80 |
| Claude Opus 4.7 | $0.05 - $0.25 | $0.20 - $0.80 |
| Gemini 3 Pro | $0.05 - $0.15 | $0.15 - $0.40 |
| **Total** | **$0.15 - $0.70** | **$0.50 - $2.00** |

Rule of thumb: if being wrong costs you less than 15 minutes of work, skip the council.

---

## Requirements

- Python 3.9+
- At least one API key (all three recommended)
- For Claude Code integration: Claude Code CLI installed

Dependencies:

```
openai>=1.40.0
anthropic>=0.40.0
google-genai>=1.0.0
rich>=13.7.0
click>=8.1.7
python-dotenv>=1.0.0
mcp>=1.0.0
```

---

## Python API

```python
from council_agent import CouncilAgent

agent = CouncilAgent()
result = agent.consult(
    task="Review this code for security issues",
    context=open("api.py").read(),
    council_type="security",
    show_individual=True,
)
print(result["responses"])
```

Low-level direct call:

```python
from mcp_council_server import init_clients, run_council

init_clients()
output = run_council(
    task="Microservices vs modular monolith for a 4-person team?",
    context="Current stack: Django + Postgres. Expected load: 10k req/day.",
    council_type="architecture",
    web_search=False,  # flip to True for research mode
)
print(output)
```

---

## Project layout

```
llm-council/
├── council_agent.py         CLI for quick consultations
├── project_council.py       Project-aware interactive agent
├── mcp_council_server.py    MCP server for Claude Code (with web-search variants)
├── council.py               Core multi-model library
├── enhancer.py              Single-model prompt enhancer
├── strategies.py            Prompt enhancement strategies
├── cli.py                   CLI entry point
├── requirements.txt
├── setup.py
└── .env.example
```

---

## Updating model versions

Model IDs live at the top of `mcp_council_server.py`:

```python
MODEL_OPENAI = "gpt-5.4"
MODEL_ANTHROPIC = "claude-opus-4-7"
MODEL_GOOGLE = "gemini-3-pro-preview"
```

When a provider ships a new flagship model, update these three constants.

---

## License

MIT
