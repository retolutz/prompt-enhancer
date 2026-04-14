"""
Prompt Enhancer Core Engine
Uses OpenAI API to transform basic prompts into professional-grade prompts.
"""

import os
import json
from typing import Optional, List
from dataclasses import dataclass

from openai import OpenAI
from dotenv import load_dotenv

from strategies import ALL_STRATEGIES, EnhancementStrategy, MASTER_ENHANCER

# Models that don't support max_tokens and custom temperature
REASONING_MODELS = {'o3', 'o3-mini', 'o1', 'o1-pro', 'o1-mini', 'gpt-5', 'gpt-5.4', 'gpt-5.2', 'gpt-5.1'}


@dataclass
class EnhancementResult:
    """Result of a prompt enhancement."""
    original_prompt: str
    enhanced_prompt: str
    strategy_used: str
    tokens_used: int


class PromptEnhancer:
    """
    Core engine for enhancing prompts using OpenAI o3.

    Based on research from:
    - DSE v7.0 (Deep Semantic Enhancer)
    - AutoPrompt (Intent-based Calibration)
    - MCP Prompt Optimizer (Research-backed strategies)
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "o3"):
        """
        Initialize the enhancer.

        Args:
            api_key: OpenAI API key. If not provided, reads from OPENAI_API_KEY env var.
            model: Model to use for enhancement. Default: o3 (best available)
        """
        load_dotenv(override=True)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def _is_reasoning_model(self) -> bool:
        """Check if current model is a reasoning model with limited parameters."""
        return any(self.model.startswith(m) for m in REASONING_MODELS)

    def _create_completion(self, messages: list, temperature: float = 0.7) -> dict:
        """Create a chat completion with model-appropriate parameters."""
        if self._is_reasoning_model():
            # Reasoning models: no max_tokens, temperature must be 1
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
            )
        else:
            # Standard models: full parameter support
            return self.client.chat.completions.create(
                model=self.model,
                max_tokens=2048,
                temperature=temperature,
                messages=messages,
            )

    def enhance(
        self,
        prompt: str,
        strategy: str = "master",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> EnhancementResult:
        """
        Enhance a prompt using the specified strategy.

        Args:
            prompt: The original prompt to enhance.
            strategy: Enhancement strategy to use. Options:
                - "master": Comprehensive enhancement (default, recommended)
                - "semantic": Semantic analysis
                - "role": Role injection
                - "constraint": Constraint engineering
                - "cot": Chain-of-thought
                - "context": Contextual saturation
                - "decompose": Task decomposition
                - "output": Output specification
                - "fewshot": Few-shot examples
                - "refine": Self-refine integration
            temperature: Creativity level (0.0-1.0). Ignored for reasoning models.
            max_tokens: Maximum tokens in response. Ignored for reasoning models.

        Returns:
            EnhancementResult with original and enhanced prompts.
        """
        if strategy not in ALL_STRATEGIES:
            raise ValueError(f"Unknown strategy: {strategy}. Available: {list(ALL_STRATEGIES.keys())}")

        enhancement_strategy = ALL_STRATEGIES[strategy]

        messages = [
            {"role": "system", "content": enhancement_strategy.system_prompt},
            {"role": "user", "content": f"Enhance this prompt:\n\n{prompt}"}
        ]

        response = self._create_completion(messages, temperature)

        enhanced = response.choices[0].message.content.strip()
        tokens = response.usage.total_tokens

        return EnhancementResult(
            original_prompt=prompt,
            enhanced_prompt=enhanced,
            strategy_used=enhancement_strategy.name,
            tokens_used=tokens
        )

    def enhance_iterative(
        self,
        prompt: str,
        strategies: List[str] = None,
        temperature: float = 0.7,
    ) -> EnhancementResult:
        """
        Apply multiple strategies sequentially for maximum enhancement.

        Args:
            prompt: The original prompt to enhance.
            strategies: List of strategies to apply in order.
                       Default: ["role", "constraint", "cot", "output"]
            temperature: Creativity level. Ignored for reasoning models.

        Returns:
            EnhancementResult with fully enhanced prompt.
        """
        if strategies is None:
            strategies = ["role", "constraint", "cot", "output"]

        current_prompt = prompt
        total_tokens = 0
        strategies_applied = []

        for strategy_name in strategies:
            if strategy_name not in ALL_STRATEGIES:
                continue

            result = self.enhance(
                current_prompt,
                strategy=strategy_name,
                temperature=temperature
            )
            current_prompt = result.enhanced_prompt
            total_tokens += result.tokens_used
            strategies_applied.append(strategy_name)

        return EnhancementResult(
            original_prompt=prompt,
            enhanced_prompt=current_prompt,
            strategy_used=" -> ".join(strategies_applied),
            tokens_used=total_tokens
        )

    def analyze(self, prompt: str) -> dict:
        """
        Analyze a prompt without enhancing it.
        Returns analysis of intent, entities, constraints, and issues.
        """
        messages = [
            {
                "role": "system",
                "content": """Analyze the given prompt and return a JSON object with:
{
    "intent": "primary goal of the prompt",
    "entities": ["list", "of", "key", "entities"],
    "explicit_constraints": ["stated requirements"],
    "implicit_constraints": ["implied requirements"],
    "ambiguities": ["potential misinterpretations"],
    "quality_score": 1-10,
    "suggestions": ["improvement suggestions"]
}"""
            },
            {"role": "user", "content": f"Analyze this prompt:\n\n{prompt}"}
        ]

        response = self._create_completion(messages, temperature=0.3)

        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return {"raw_analysis": response.choices[0].message.content}

    def compare(self, original: str, enhanced: str) -> dict:
        """
        Compare original and enhanced prompts.
        Returns analysis of improvements.
        """
        messages = [
            {
                "role": "system",
                "content": """Compare the original and enhanced prompts. Return a JSON object:
{
    "improvements": ["list of specific improvements made"],
    "original_score": 1-10,
    "enhanced_score": 1-10,
    "clarity_delta": "+X or -X",
    "specificity_delta": "+X or -X",
    "actionability_delta": "+X or -X"
}"""
            },
            {"role": "user", "content": f"ORIGINAL:\n{original}\n\nENHANCED:\n{enhanced}"}
        ]

        response = self._create_completion(messages, temperature=0.3)

        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return {"raw_comparison": response.choices[0].message.content}
