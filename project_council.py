#!/usr/bin/env python3
"""
Project Council - Deep Project-Aware Multi-LLM Council

This agent:
1. Analyzes your project structure (files, architecture, dependencies)
2. Each LLM asks 5 clarifying questions to understand context
3. Gathers all context and presents it to the full council
4. Council provides optimal, project-aware recommendations

Usage:
    python project_council.py              # Interactive mode
    python project_council.py --task "Add authentication"
    python project_council.py --analyze    # Just analyze project
"""

import os
import sys
import json
import glob
import concurrent.futures
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm

from openai import OpenAI
import anthropic
from dotenv import load_dotenv

try:
    from google import genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

load_dotenv(override=True)

console = Console()


@dataclass
class ProjectContext:
    """Collected project context."""
    name: str
    path: str
    language: str
    framework: str
    structure: Dict[str, Any]
    key_files: List[str]
    dependencies: List[str]
    architecture_notes: str = ""
    user_answers: Dict[str, str] = field(default_factory=dict)
    relevant_code: Dict[str, str] = field(default_factory=dict)


@dataclass
class CouncilQuestion:
    """A clarifying question from a council member."""
    model: str
    question: str
    purpose: str  # Why this question matters


class ProjectCouncil:
    """
    Project-aware LLM Council that deeply understands your codebase
    before providing recommendations.
    """

    def __init__(self, project_path: str = "."):
        """Initialize the council with project path."""
        self.project_path = Path(project_path).resolve()
        self.context: Optional[ProjectContext] = None

        # Initialize LLM clients
        self.openai_client = None
        self.anthropic_client = None
        self.google_client = None

        if os.getenv("OPENAI_API_KEY"):
            self.openai_client = OpenAI()
        if os.getenv("ANTHROPIC_API_KEY"):
            self.anthropic_client = anthropic.Anthropic()
        if GOOGLE_AVAILABLE and os.getenv("GOOGLE_API_KEY"):
            self.google_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    def get_available_models(self) -> List[str]:
        """Return list of available models."""
        models = []
        if self.openai_client:
            models.append("o3 (OpenAI)")
        if self.anthropic_client:
            models.append("Claude Opus 4 (Anthropic)")
        if self.google_client:
            models.append("Gemini 2.5 Pro (Google)")
        return models

    def analyze_project(self) -> ProjectContext:
        """Analyze the project structure and gather initial context."""

        # Detect project type
        files = list(self.project_path.rglob("*"))
        file_names = [f.name for f in files if f.is_file()]

        # Detect language/framework
        language = "Unknown"
        framework = "Unknown"

        if "package.json" in file_names:
            language = "JavaScript/TypeScript"
            pkg_path = self.project_path / "package.json"
            if pkg_path.exists():
                try:
                    pkg = json.loads(pkg_path.read_text())
                    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                    if "next" in deps:
                        framework = "Next.js"
                    elif "react" in deps:
                        framework = "React"
                    elif "vue" in deps:
                        framework = "Vue.js"
                    elif "express" in deps:
                        framework = "Express.js"
                except:
                    pass

        elif "requirements.txt" in file_names or "pyproject.toml" in file_names or "setup.py" in file_names:
            language = "Python"
            # Check for frameworks
            req_files = ["requirements.txt", "pyproject.toml", "setup.py"]
            for req_file in req_files:
                req_path = self.project_path / req_file
                if req_path.exists():
                    content = req_path.read_text().lower()
                    if "django" in content:
                        framework = "Django"
                    elif "flask" in content:
                        framework = "Flask"
                    elif "fastapi" in content:
                        framework = "FastAPI"
                    elif "streamlit" in content:
                        framework = "Streamlit"
                    break

        elif "Cargo.toml" in file_names:
            language = "Rust"
        elif "go.mod" in file_names:
            language = "Go"
        elif "pom.xml" in file_names or "build.gradle" in file_names:
            language = "Java"

        # Build structure
        structure = self._get_directory_structure()

        # Find key files
        key_files = self._identify_key_files()

        # Get dependencies
        dependencies = self._get_dependencies()

        self.context = ProjectContext(
            name=self.project_path.name,
            path=str(self.project_path),
            language=language,
            framework=framework,
            structure=structure,
            key_files=key_files,
            dependencies=dependencies,
        )

        return self.context

    def _get_directory_structure(self, max_depth: int = 3) -> Dict[str, Any]:
        """Get project directory structure."""
        structure = {}

        def walk(path: Path, depth: int) -> Dict:
            if depth > max_depth:
                return {"...": "truncated"}

            result = {}
            try:
                for item in sorted(path.iterdir()):
                    # Skip hidden and common ignore patterns
                    if item.name.startswith(".") or item.name in [
                        "node_modules", "__pycache__", "venv", ".venv",
                        "dist", "build", ".git", "target"
                    ]:
                        continue

                    if item.is_dir():
                        result[item.name + "/"] = walk(item, depth + 1)
                    else:
                        result[item.name] = f"{item.stat().st_size} bytes"
            except PermissionError:
                pass
            return result

        return walk(self.project_path, 0)

    def _identify_key_files(self) -> List[str]:
        """Identify key project files."""
        key_patterns = [
            # Config
            "*.config.*", "*.json", "*.toml", "*.yaml", "*.yml",
            # Entry points
            "main.*", "app.*", "index.*", "__init__.py",
            # Core files
            "*.py", "*.ts", "*.tsx", "*.js", "*.jsx",
            # Docs
            "README*", "CONTRIBUTING*",
        ]

        key_files = []
        for pattern in key_patterns:
            matches = list(self.project_path.glob(pattern))
            for match in matches[:5]:  # Limit per pattern
                rel_path = match.relative_to(self.project_path)
                if not any(part.startswith(".") for part in rel_path.parts):
                    key_files.append(str(rel_path))

        return key_files[:30]  # Limit total

    def _get_dependencies(self) -> List[str]:
        """Extract project dependencies."""
        deps = []

        # Python
        req_path = self.project_path / "requirements.txt"
        if req_path.exists():
            lines = req_path.read_text().strip().split("\n")
            deps.extend([l.split("==")[0].split(">=")[0].strip() for l in lines if l.strip() and not l.startswith("#")])

        # JavaScript
        pkg_path = self.project_path / "package.json"
        if pkg_path.exists():
            try:
                pkg = json.loads(pkg_path.read_text())
                deps.extend(list(pkg.get("dependencies", {}).keys()))
            except:
                pass

        return deps[:30]

    def _read_file_content(self, file_path: str, max_lines: int = 200) -> str:
        """Read file content with size limit."""
        try:
            full_path = self.project_path / file_path
            if full_path.exists():
                lines = full_path.read_text().split("\n")[:max_lines]
                return "\n".join(lines)
        except:
            pass
        return ""

    def _call_openai(self, prompt: str, system: str) -> tuple:
        """Call OpenAI o3."""
        if not self.openai_client:
            return None, "Not configured"
        try:
            response = self.openai_client.chat.completions.create(
                model="o3",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
            )
            return response.choices[0].message.content, None
        except Exception as e:
            return None, str(e)

    def _call_anthropic(self, prompt: str, system: str) -> tuple:
        """Call Claude Opus 4."""
        if not self.anthropic_client:
            return None, "Not configured"
        try:
            response = self.anthropic_client.messages.create(
                model="claude-opus-4-20250514",
                max_tokens=8192,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text, None
        except Exception as e:
            return None, str(e)

    def _call_google(self, prompt: str, system: str) -> tuple:
        """Call Gemini 2.5 Pro."""
        if not self.google_client:
            return None, "Not configured"
        try:
            full_prompt = f"{system}\n\n{prompt}"
            response = self.google_client.models.generate_content(
                model="gemini-2.5-pro",
                contents=full_prompt,
            )
            return response.text, None
        except Exception as e:
            return None, str(e)

    def generate_clarifying_questions(self, task: str) -> Dict[str, List[CouncilQuestion]]:
        """
        Each LLM generates 5 clarifying questions to understand the task better.
        """
        if not self.context:
            self.analyze_project()

        context_summary = f"""
PROJECT: {self.context.name}
LANGUAGE: {self.context.language}
FRAMEWORK: {self.context.framework}
KEY FILES: {', '.join(self.context.key_files[:10])}
DEPENDENCIES: {', '.join(self.context.dependencies[:15])}

STRUCTURE:
{json.dumps(self.context.structure, indent=2)[:2000]}
"""

        system_prompt = """You are an expert software engineer preparing to help with a coding task.
Before providing recommendations, you need to understand the project deeply.

Generate exactly 5 clarifying questions that would help you provide better advice.
Each question should uncover critical context about:
1. The specific requirements or constraints
2. The current architecture or implementation
3. Edge cases or potential issues
4. User preferences or priorities
5. Integration points or dependencies

Format your response as JSON:
{
    "questions": [
        {"question": "...", "purpose": "Why this matters..."},
        {"question": "...", "purpose": "..."},
        ...
    ]
}
"""

        prompt = f"""
{context_summary}

TASK: {task}

Generate 5 clarifying questions to better understand this task in the context of this project.
"""

        questions = {}

        # Call all models in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}

            if self.openai_client:
                futures[executor.submit(self._call_openai, prompt, system_prompt)] = "o3 (OpenAI)"
            if self.anthropic_client:
                futures[executor.submit(self._call_anthropic, prompt, system_prompt)] = "Claude Opus 4"
            if self.google_client:
                futures[executor.submit(self._call_google, prompt, system_prompt)] = "Gemini 2.5 Pro"

            for future in concurrent.futures.as_completed(futures):
                model_name = futures[future]
                response, error = future.result()

                if response and not error:
                    try:
                        # Parse JSON from response
                        # Handle potential markdown code blocks
                        clean = response.strip()
                        if "```json" in clean:
                            clean = clean.split("```json")[1].split("```")[0]
                        elif "```" in clean:
                            clean = clean.split("```")[1].split("```")[0]

                        data = json.loads(clean)
                        questions[model_name] = [
                            CouncilQuestion(
                                model=model_name,
                                question=q["question"],
                                purpose=q.get("purpose", "")
                            )
                            for q in data.get("questions", [])[:5]
                        ]
                    except:
                        # Fallback: extract questions manually
                        questions[model_name] = [
                            CouncilQuestion(
                                model=model_name,
                                question=f"Question parsing failed. Raw response available.",
                                purpose=""
                            )
                        ]

        return questions

    def gather_context_interactively(self, task: str) -> Dict[str, str]:
        """
        Interactive mode: ask user the clarifying questions and collect answers.
        """
        console.print(f"\n[bold cyan]Gathering context for:[/bold cyan] {task}\n")

        with console.status("[cyan]Council members generating questions..."):
            all_questions = self.generate_clarifying_questions(task)

        answers = {}

        # Deduplicate similar questions across models
        seen_questions = set()
        unique_questions = []

        for model, questions in all_questions.items():
            for q in questions:
                # Simple dedup by checking if question is substantially different
                q_lower = q.question.lower()
                if not any(existing.lower() in q_lower or q_lower in existing.lower()
                          for existing in seen_questions):
                    seen_questions.add(q_lower)
                    unique_questions.append(q)

        console.print(f"\n[bold]The council has {len(unique_questions)} questions to better understand your task:[/bold]\n")

        for i, q in enumerate(unique_questions, 1):
            console.print(Panel(
                f"[cyan]{q.question}[/cyan]\n\n[dim]Purpose: {q.purpose}[/dim]",
                title=f"[bold]Question {i}/{len(unique_questions)} ({q.model})[/bold]",
                border_style="blue"
            ))

            answer = Prompt.ask("[green]Your answer[/green]")
            answers[q.question] = answer
            console.print()

        return answers

    def read_relevant_files(self, task: str, answers: Dict[str, str]) -> Dict[str, str]:
        """Ask council which files to read, then read them."""

        context_text = f"""
TASK: {task}

USER ANSWERS TO CLARIFYING QUESTIONS:
{json.dumps(answers, indent=2)}

PROJECT FILES:
{', '.join(self.context.key_files)}
"""

        system = """Based on the task and user's answers, identify which project files would be most relevant to read.
Return a JSON list of file paths (max 10 files):
{"files": ["path/to/file1.py", "path/to/file2.ts"]}
"""

        # Use Claude to identify relevant files
        response, error = self._call_anthropic(context_text, system)

        files_to_read = []
        if response:
            try:
                clean = response.strip()
                if "```json" in clean:
                    clean = clean.split("```json")[1].split("```")[0]
                elif "```" in clean:
                    clean = clean.split("```")[1].split("```")[0]
                data = json.loads(clean)
                files_to_read = data.get("files", [])[:10]
            except:
                pass

        # Read the files
        relevant_code = {}
        for file_path in files_to_read:
            content = self._read_file_content(file_path)
            if content:
                relevant_code[file_path] = content

        return relevant_code

    def consult_council(
        self,
        task: str,
        answers: Dict[str, str],
        relevant_code: Dict[str, str],
        council_type: str = "general"
    ) -> str:
        """
        Consult the full council with all gathered context.
        """
        if not self.context:
            self.analyze_project()

        # Build comprehensive context
        context_parts = [
            f"# Project: {self.context.name}",
            f"Language: {self.context.language}",
            f"Framework: {self.context.framework}",
            f"\n## Dependencies\n{', '.join(self.context.dependencies[:20])}",
            f"\n## Project Structure\n```\n{json.dumps(self.context.structure, indent=2)[:1500]}\n```",
        ]

        if answers:
            context_parts.append("\n## User's Context (Answers to Clarifying Questions)")
            for q, a in answers.items():
                context_parts.append(f"\n**Q:** {q}\n**A:** {a}")

        if relevant_code:
            context_parts.append("\n## Relevant Code")
            for file_path, code in relevant_code.items():
                context_parts.append(f"\n### {file_path}\n```\n{code[:3000]}\n```")

        full_context = "\n".join(context_parts)

        # Council system prompts
        system_prompts = {
            "implement": """You are an expert software engineer. Based on the comprehensive project context provided,
give detailed implementation recommendations. Consider:
- The existing architecture and patterns
- Dependencies already in use
- User's specific requirements from their answers
- Best practices for this stack

Provide specific, actionable code and steps.""",

            "review": """You are an expert code reviewer. With full knowledge of the project context,
provide a thorough review considering:
- Security implications in this specific context
- Performance within the existing architecture
- Code quality and consistency with the codebase
- Potential edge cases based on user's requirements""",

            "architecture": """You are a senior software architect. With complete project understanding,
advise on architecture considering:
- Current tech stack and patterns
- Scalability within the existing system
- User's specific constraints and goals
- Migration path from current state""",

            "debug": """You are an expert debugger. With full project context,
help identify the root cause considering:
- The specific stack and dependencies
- User's description of the issue
- Relevant code sections
- Common issues in this framework""",

            "general": """You are an expert AI assistant with complete knowledge of this project.
Provide thorough, context-aware recommendations considering all the information provided."""
        }

        system = system_prompts.get(council_type, system_prompts["general"])

        prompt = f"""
{full_context}

---

TASK: {task}

Provide your expert recommendations with full awareness of the project context, user's requirements,
and relevant code. Be specific and actionable.
"""

        # Call all models in parallel
        responses = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}

            if self.openai_client:
                futures[executor.submit(self._call_openai, prompt, system)] = "o3 (OpenAI)"
            if self.anthropic_client:
                futures[executor.submit(self._call_anthropic, prompt, system)] = "Claude Opus 4"
            if self.google_client:
                futures[executor.submit(self._call_google, prompt, system)] = "Gemini 2.5 Pro"

            for future in concurrent.futures.as_completed(futures):
                model_name = futures[future]
                response, error = future.result()
                responses.append({
                    "model": model_name,
                    "response": response,
                    "error": error
                })

        # Aggregate responses
        successful = [r for r in responses if r["response"]]

        if not successful:
            return "Error: No successful responses from council"

        if len(successful) == 1:
            return f"**{successful[0]['model']}:**\n\n{successful[0]['response']}"

        # Aggregate with Claude Opus 4
        responses_text = "\n\n".join([
            f"=== {r['model']} ===\n{r['response']}"
            for r in successful
        ])

        aggregation_prompt = f"""You are synthesizing expert recommendations from multiple AI models.
All models had full context about the project, the task, and user's specific requirements.

TASK: {task}

RESPONSES:
{responses_text}

SYNTHESIS INSTRUCTIONS:
1. Identify the key recommendations each model provided
2. Note any different approaches or trade-offs
3. Synthesize the best elements considering the specific project context
4. Provide clear, prioritized action items
5. If models disagree, explain which approach fits this project better and why

Provide a comprehensive, actionable synthesis."""

        synthesis, error = self._call_anthropic(aggregation_prompt, "You are an expert at synthesizing technical recommendations.")

        if synthesis:
            return synthesis
        else:
            return responses_text


# CLI
@click.group(invoke_without_command=True)
@click.option("--task", "-t", help="Task to get help with")
@click.option("--analyze", "-a", is_flag=True, help="Just analyze project")
@click.option("--path", "-p", default=".", help="Project path")
@click.pass_context
def cli(ctx, task, analyze, path):
    """Project Council - Deep project-aware multi-LLM assistance."""

    if ctx.invoked_subcommand is not None:
        return

    council = ProjectCouncil(path)

    console.print("\n[bold magenta]╔══════════════════════════════════════════════════════════╗[/bold magenta]")
    console.print("[bold magenta]║           PROJECT COUNCIL                                ║[/bold magenta]")
    console.print("[bold magenta]║   Deep project-aware multi-LLM assistance                ║[/bold magenta]")
    console.print("[bold magenta]╚══════════════════════════════════════════════════════════╝[/bold magenta]\n")

    console.print(f"[bold]Available Models:[/bold] {', '.join(council.get_available_models())}\n")

    # Analyze project
    with console.status("[cyan]Analyzing project..."):
        context = council.analyze_project()

    # Show project info
    table = Table(title="Project Analysis")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Name", context.name)
    table.add_row("Path", context.path)
    table.add_row("Language", context.language)
    table.add_row("Framework", context.framework)
    table.add_row("Key Files", str(len(context.key_files)))
    table.add_row("Dependencies", str(len(context.dependencies)))
    console.print(table)

    if analyze:
        # Just show structure
        console.print("\n[bold]Project Structure:[/bold]")
        console.print(json.dumps(context.structure, indent=2))
        return

    if not task:
        task = Prompt.ask("\n[bold cyan]What do you need help with?[/bold cyan]")

    # Gather context through questions
    console.print("\n[bold]Phase 1: Gathering Context[/bold]")
    answers = council.gather_context_interactively(task)

    # Read relevant files
    console.print("\n[bold]Phase 2: Analyzing Relevant Code[/bold]")
    with console.status("[cyan]Identifying and reading relevant files..."):
        relevant_code = council.read_relevant_files(task, answers)

    if relevant_code:
        console.print(f"[green]Read {len(relevant_code)} relevant files:[/green]")
        for f in relevant_code.keys():
            console.print(f"  - {f}")

    # Consult council
    console.print("\n[bold]Phase 3: Consulting the Council[/bold]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold magenta]Council is deliberating with full project context..."),
        console=console
    ) as progress:
        progress.add_task("council", total=None)
        result = council.consult_council(task, answers, relevant_code)

    # Show result
    console.print("\n")
    console.print(Panel(
        Markdown(result),
        title="[bold green]Council Recommendation (Project-Aware)[/bold green]",
        border_style="green"
    ))


@cli.command()
@click.option("--path", "-p", default=".", help="Project path")
def status(path):
    """Check council status."""
    council = ProjectCouncil(path)

    table = Table(title="Council Status")
    table.add_column("Model", style="cyan")
    table.add_column("Status", style="green")

    models = [
        ("o3 (OpenAI)", council.openai_client is not None),
        ("Claude Opus 4 (Anthropic)", council.anthropic_client is not None),
        ("Gemini 2.5 Pro (Google)", council.google_client is not None),
    ]

    for name, available in models:
        status_text = "[green]Available[/green]" if available else "[red]Not configured[/red]"
        table.add_row(name, status_text)

    console.print(table)


@cli.command()
@click.argument("task")
@click.option("--path", "-p", default=".", help="Project path")
@click.option("--quick", "-q", is_flag=True, help="Skip clarifying questions")
def ask(task, path, quick):
    """Quick question to the council."""
    council = ProjectCouncil(path)

    with console.status("[cyan]Analyzing project..."):
        council.analyze_project()

    if quick:
        answers = {}
        relevant_code = {}
    else:
        answers = council.gather_context_interactively(task)
        with console.status("[cyan]Reading relevant files..."):
            relevant_code = council.read_relevant_files(task, answers)

    with console.status("[magenta]Consulting council..."):
        result = council.consult_council(task, answers, relevant_code)

    console.print(Panel(
        Markdown(result),
        title="[bold green]Council Recommendation[/bold green]",
        border_style="green"
    ))


if __name__ == "__main__":
    cli()
