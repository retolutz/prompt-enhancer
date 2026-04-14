"""
LLM Council - Multi-model prompt enhancement
Uses multiple LLMs in parallel and aggregates the best result.

Models used (best available):
- OpenAI: o3 (best reasoning model)
- Anthropic: Claude Opus 4 (best Claude model)
- Google: Gemini 2.5 Pro (best Gemini model)
"""

import os
import concurrent.futures
from typing import Optional, List
from dataclasses import dataclass, field

from openai import OpenAI
import anthropic
from dotenv import load_dotenv

try:
    from google import genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

from strategies import ALL_STRATEGIES


@dataclass
class CouncilMember:
    """Represents a single LLM in the council."""
    name: str
    provider: str  # 'openai', 'anthropic', 'google'
    model: str
    response: Optional[str] = None
    tokens_used: int = 0
    error: Optional[str] = None


@dataclass
class CouncilResult:
    """Result from the LLM Council."""
    original_prompt: str
    enhanced_prompt: str  # Final aggregated result
    members: List[CouncilMember] = field(default_factory=list)
    aggregator_reasoning: str = ""
    total_tokens: int = 0


class LLMCouncil:
    """
    LLM Council for multi-model prompt enhancement.

    Runs multiple LLMs in parallel, then uses an aggregator to select
    or merge the best result.

    Best models per provider:
    - OpenAI: o3 (reasoning model)
    - Anthropic: Claude Opus 4
    - Google: Gemini 2.0 Flash
    """

    def __init__(
        self,
        openai_key: Optional[str] = None,
        anthropic_key: Optional[str] = None,
        google_key: Optional[str] = None,
    ):
        """Initialize the council with API keys."""
        load_dotenv(override=True)

        self.openai_key = openai_key or os.getenv("OPENAI_API_KEY")
        self.anthropic_key = anthropic_key or os.getenv("ANTHROPIC_API_KEY")
        self.google_key = google_key or os.getenv("GOOGLE_API_KEY")

        # Initialize clients
        self.openai_client = OpenAI(api_key=self.openai_key) if self.openai_key else None
        self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_key) if self.anthropic_key else None
        self.google_client = None
        if GOOGLE_AVAILABLE and self.google_key:
            self.google_client = genai.Client(api_key=self.google_key)

        # Available council members (BEST models)
        self.members_config = []

        if self.openai_client:
            self.members_config.append({
                "name": "o3 (OpenAI)",
                "provider": "openai",
                "model": "o3",  # Best reasoning model
            })

        if self.anthropic_client:
            self.members_config.append({
                "name": "Claude Opus 4 (Anthropic)",
                "provider": "anthropic",
                "model": "claude-opus-4-20250514",  # Best Claude model
            })

        if self.google_client:
            self.members_config.append({
                "name": "Gemini 2.5 Pro (Google)",
                "provider": "google",
                "model": "gemini-2.5-pro",  # Best Gemini model
            })

    def _call_openai(self, prompt: str, system_prompt: str, model: str) -> tuple:
        """Call OpenAI API."""
        try:
            # o3 doesn't support max_tokens/temperature
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Enhance this prompt:\n\n{prompt}"}
                ],
            )
            return response.choices[0].message.content.strip(), response.usage.total_tokens, None
        except Exception as e:
            return None, 0, str(e)

    def _call_anthropic(self, prompt: str, system_prompt: str, model: str) -> tuple:
        """Call Anthropic API."""
        try:
            response = self.anthropic_client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": f"Enhance this prompt:\n\n{prompt}"}
                ],
            )
            tokens = response.usage.input_tokens + response.usage.output_tokens
            return response.content[0].text.strip(), tokens, None
        except Exception as e:
            return None, 0, str(e)

    def _call_google(self, prompt: str, system_prompt: str, model: str) -> tuple:
        """Call Google Gemini API."""
        try:
            full_prompt = f"{system_prompt}\n\nEnhance this prompt:\n\n{prompt}"
            response = self.google_client.models.generate_content(
                model=model,
                contents=full_prompt,
            )
            # Gemini doesn't provide token count in same way
            return response.text.strip(), 0, None
        except Exception as e:
            return None, 0, str(e)

    def _call_member(self, prompt: str, system_prompt: str, config: dict) -> CouncilMember:
        """Call a single council member."""
        member = CouncilMember(
            name=config["name"],
            provider=config["provider"],
            model=config["model"],
        )

        if config["provider"] == "openai":
            member.response, member.tokens_used, member.error = self._call_openai(
                prompt, system_prompt, config["model"]
            )
        elif config["provider"] == "anthropic":
            member.response, member.tokens_used, member.error = self._call_anthropic(
                prompt, system_prompt, config["model"]
            )
        elif config["provider"] == "google":
            member.response, member.tokens_used, member.error = self._call_google(
                prompt, system_prompt, config["model"]
            )

        return member

    def _aggregate_results(self, original_prompt: str, members: List[CouncilMember]) -> tuple:
        """Use Claude Opus 4 to aggregate/select the best result."""

        # Filter successful responses
        successful = [m for m in members if m.response and not m.error]

        if len(successful) == 0:
            return "Error: No successful responses from council members", "", 0

        if len(successful) == 1:
            return successful[0].response, f"Only one successful response from {successful[0].name}", 0

        # Build aggregation prompt
        responses_text = "\n\n".join([
            f"=== {m.name} ===\n{m.response}"
            for m in successful
        ])

        aggregation_prompt = f"""You are an expert prompt engineer. Multiple AI models have enhanced the same prompt.
Your task is to select the BEST enhanced prompt OR create an improved version by combining the best elements from each.

ORIGINAL PROMPT:
{original_prompt}

ENHANCED VERSIONS:
{responses_text}

INSTRUCTIONS:
1. Analyze each enhanced version for: clarity, specificity, actionability, and completeness
2. Either select the best one OR create a merged version with the best elements
3. First, briefly explain your reasoning (2-3 sentences)
4. Then output the final enhanced prompt

FORMAT:
REASONING: [Your brief analysis]

FINAL PROMPT:
[The best or merged prompt]"""

        # Use Claude Opus 4 for aggregation (best at synthesis)
        if self.anthropic_client:
            try:
                response = self.anthropic_client.messages.create(
                    model="claude-opus-4-20250514",  # Best model for aggregation
                    max_tokens=4096,
                    messages=[{"role": "user", "content": aggregation_prompt}],
                )
                result = response.content[0].text.strip()
                tokens = response.usage.input_tokens + response.usage.output_tokens

                # Parse response
                if "FINAL PROMPT:" in result:
                    parts = result.split("FINAL PROMPT:", 1)
                    reasoning = parts[0].replace("REASONING:", "").strip()
                    final_prompt = parts[1].strip()
                else:
                    reasoning = ""
                    final_prompt = result

                return final_prompt, reasoning, tokens
            except Exception as e:
                # Fallback: return first successful response
                return successful[0].response, f"Aggregation failed: {e}", 0

        # Fallback if no Anthropic: use OpenAI
        elif self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4.1",
                    messages=[{"role": "user", "content": aggregation_prompt}],
                    max_tokens=4096,
                )
                result = response.choices[0].message.content.strip()
                tokens = response.usage.total_tokens

                if "FINAL PROMPT:" in result:
                    parts = result.split("FINAL PROMPT:", 1)
                    reasoning = parts[0].replace("REASONING:", "").strip()
                    final_prompt = parts[1].strip()
                else:
                    reasoning = ""
                    final_prompt = result

                return final_prompt, reasoning, tokens
            except:
                return successful[0].response, "Aggregation failed, using first response", 0

        return successful[0].response, "No aggregator available", 0

    def enhance(
        self,
        prompt: str,
        strategy: str = "master",
    ) -> CouncilResult:
        """
        Enhance a prompt using the LLM Council.

        Args:
            prompt: The original prompt to enhance.
            strategy: Enhancement strategy (default: master).

        Returns:
            CouncilResult with aggregated enhancement and individual responses.
        """
        if not self.members_config:
            raise ValueError("No LLM providers configured. Add API keys to .env")

        if strategy not in ALL_STRATEGIES:
            raise ValueError(f"Unknown strategy: {strategy}")

        system_prompt = ALL_STRATEGIES[strategy].system_prompt

        # Call all council members in parallel
        members = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._call_member, prompt, system_prompt, config): config
                for config in self.members_config
            }
            for future in concurrent.futures.as_completed(futures):
                members.append(future.result())

        # Aggregate results
        final_prompt, reasoning, agg_tokens = self._aggregate_results(prompt, members)

        # Calculate total tokens
        total_tokens = sum(m.tokens_used for m in members) + agg_tokens

        return CouncilResult(
            original_prompt=prompt,
            enhanced_prompt=final_prompt,
            members=members,
            aggregator_reasoning=reasoning,
            total_tokens=total_tokens,
        )

    def get_available_members(self) -> List[str]:
        """Return list of available council members."""
        return [m["name"] for m in self.members_config]
