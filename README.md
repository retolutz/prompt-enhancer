# Prompt Enhancer

Transform basic prompts into professional-grade prompts using o3.

Based on research from top prompt engineering projects:
- [AI-Prompt-Enhancer](https://github.com/Pythonation/AI-Prompt-Enhancer) - DSE v7.0 cognitive architecture
- [AutoPrompt](https://github.com/Eladlev/AutoPrompt) - Intent-based calibration
- [MCP Prompt Optimizer](https://github.com/Bubobot-Team/mcp-prompt-optimizer) - Research-backed strategies

## Installation

```bash
pip install -e .
```

## Setup

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

## Usage

### Enhance a prompt (Master strategy - recommended)

```bash
prompt-enhancer enhance "Write a blog post about AI"
```

### With comparison analysis

```bash
prompt-enhancer enhance -c "Create a marketing strategy"
```

### Interactive mode

```bash
prompt-enhancer enhance -i
```

### Specific strategy

```bash
prompt-enhancer enhance -s role "Help me code"
prompt-enhancer enhance -s cot "Solve this problem"
```

### Iterative enhancement (multiple strategies)

```bash
prompt-enhancer iterative "Build an app"
```

### Analyze a prompt

```bash
prompt-enhancer analyze "Make my website faster"
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
Schreibe einen Blog über KI
```

**Output:**
```
Als erfahrener Tech-Blogger und KI-Experte, erstelle einen
umfassenden Blog-Artikel über Künstliche Intelligenz.

1. **Einleitung**: Captivating hook über die Bedeutung von KI
2. **Geschichte**: Wichtige Meilensteine der KI-Entwicklung
3. **Anwendungen**: 3+ aktuelle Use Cases mit Beispielen
4. **Zukunft**: Prognosen und gesellschaftliche Auswirkungen
5. **Ethik**: Herausforderungen und Lösungsansätze
6. **Fazit**: Zusammenfassung und Ausblick

**Constraints:**
- Länge: 1000-1500 Wörter
- Sprache: Deutsch
- Ton: Informativ, aber zugänglich
- Format: Unterüberschriften verwenden

**Quality Gates:**
- Logischer Aufbau
- Quellenangaben für Fakten
- Grammatik-Check vor Abgabe
```

## Python API

```python
from enhancer import PromptEnhancer

enhancer = PromptEnhancer()

# Single strategy
result = enhancer.enhance("Your prompt", strategy="master")
print(result.enhanced_prompt)

# Iterative (multiple strategies)
result = enhancer.enhance_iterative("Your prompt")
print(result.enhanced_prompt)

# Analyze only
analysis = enhancer.analyze("Your prompt")
print(analysis)
```

## License

MIT
