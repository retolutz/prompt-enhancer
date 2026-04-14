# Claude Code Council Integration

Set up the LLM Council as a tool for Claude Code.

## Quick Start

### Option 1: MCP Server (Recommended)

The MCP server integrates directly with Claude Code as a native tool.

#### 1. Install dependencies

```bash
cd /Users/retolutz/Desktop/prompt_enhancer
pip install -r requirements.txt
```

#### 2. Configure Claude Code

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "council": {
      "command": "python",
      "args": ["/Users/retolutz/Desktop/prompt_enhancer/mcp_council_server.py"],
      "env": {
        "OPENAI_API_KEY": "sk-proj-...",
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "GOOGLE_API_KEY": "AIza..."
      }
    }
  }
}
```

#### 3. Restart Claude Code

```bash
claude
```

#### 4. Use the Council

Claude Code now has access to these tools:
- `council_review` - Code review from multiple models
- `council_architecture` - Architecture decisions
- `council_debug` - Debugging assistance
- `council_security` - Security audits
- `council_refactor` - Refactoring suggestions
- `council_ask` - General questions

**Example prompts:**
- "Ask the council to review this file"
- "Get the council's opinion on whether I should use Redis or Memcached"
- "Have the council help debug this authentication issue"

---

### Option 2: Standalone Agent Script

Use the council agent directly from command line.

#### Usage

```bash
# Code review
python council_agent.py review path/to/file.py

# Architecture decision
python council_agent.py architect "Should I use microservices or monolith?"

# Debug help
python council_agent.py debug "App crashes on login" --code auth.py

# Security audit
python council_agent.py security api.py

# General question
python council_agent.py ask "What's the best caching strategy?"

# Interactive mode
python council_agent.py interactive

# Check status
python council_agent.py status
```

---

## Council Types

| Type | Use Case | Example |
|------|----------|---------|
| `review` | Code quality, bugs, best practices | "Review this PR" |
| `architecture` | System design decisions | "Monolith vs microservices?" |
| `debug` | Complex bug analysis | "Why does this timeout?" |
| `security` | Vulnerability assessment | "Audit this API endpoint" |
| `refactor` | Code improvement | "How to simplify this?" |
| `test` | Test case generation | "What tests am I missing?" |
| `general` | Any complex question | "Best approach for X?" |

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                         YOUR TASK                               │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌───────────┐   ┌───────────┐   ┌───────────┐
       │    o3     │   │  Claude   │   │  Gemini   │
       │ (OpenAI)  │   │  Opus 4   │   │  2.5 Pro  │
       │ Reasoning │   │ Synthesis │   │ Creative  │
       └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
             │               │               │
             └───────────────┼───────────────┘
                             ▼
                   ┌─────────────────┐
                   │  Aggregator     │
                   │  (Claude Opus)  │
                   │  Synthesizes    │
                   │  best elements  │
                   └────────┬────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    COUNCIL DECISION                             │
│  - Key insights from each model                                 │
│  - Disagreements explained                                      │
│  - Trade-offs analyzed                                          │
│  - Actionable recommendations                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Models Used

| Provider | Model | Strength |
|----------|-------|----------|
| OpenAI | **o3** | Deep reasoning, complex problems |
| Anthropic | **Claude Opus 4** | Synthesis, nuance, aggregation |
| Google | **Gemini 2.5 Pro** | Broad knowledge, creative solutions |

---

## When to Use the Council

**Use the Council when:**
- Making important architecture decisions
- Reviewing security-critical code
- Debugging complex issues with multiple possible causes
- Wanting diverse perspectives on a problem
- The cost of being wrong is high

**Don't use the Council when:**
- Simple, straightforward tasks
- Time-sensitive quick fixes
- Budget is a concern (3x API costs)

---

## Cost Considerations

Each council consultation calls 3 models + 1 aggregation call.

Estimated cost per consultation:
- o3: ~$0.10-0.50 (depending on reasoning)
- Claude Opus 4: ~$0.05-0.20
- Gemini 2.5 Pro: ~$0.01-0.05
- Aggregation: ~$0.05-0.15

**Total: ~$0.20-0.90 per consultation**

Use wisely for high-value decisions!
