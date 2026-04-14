#!/usr/bin/env python3
"""
Example usage of the Prompt Enhancer library.
"""

from enhancer import PromptEnhancer

# Initialize (uses OPENAI_API_KEY env var)
enhancer = PromptEnhancer()

# Example 1: Simple enhancement with master strategy
print("=" * 60)
print("EXAMPLE 1: Master Enhancement")
print("=" * 60)

simple_prompt = "Write a blog post about AI"

result = enhancer.enhance(simple_prompt, strategy="master")
print(f"\nOriginal: {simple_prompt}")
print(f"\nEnhanced:\n{result.enhanced_prompt}")
print(f"\nTokens used: {result.tokens_used}")

# Example 2: Specific strategy (role injection)
print("\n" + "=" * 60)
print("EXAMPLE 2: Role Injection Strategy")
print("=" * 60)

coding_prompt = "Help me debug this Python code"

result = enhancer.enhance(coding_prompt, strategy="role")
print(f"\nOriginal: {coding_prompt}")
print(f"\nEnhanced:\n{result.enhanced_prompt}")

# Example 3: Iterative enhancement (multiple strategies)
print("\n" + "=" * 60)
print("EXAMPLE 3: Iterative Enhancement")
print("=" * 60)

complex_prompt = "Create a marketing strategy"

result = enhancer.enhance_iterative(complex_prompt)
print(f"\nOriginal: {complex_prompt}")
print(f"\nEnhanced (after {result.strategy_used}):\n{result.enhanced_prompt}")
print(f"\nTotal tokens: {result.tokens_used}")

# Example 4: Analyze a prompt
print("\n" + "=" * 60)
print("EXAMPLE 4: Prompt Analysis")
print("=" * 60)

prompt_to_analyze = "Make my website faster"

analysis = enhancer.analyze(prompt_to_analyze)
print(f"\nPrompt: {prompt_to_analyze}")
print(f"\nAnalysis:")
for key, value in analysis.items():
    print(f"  {key}: {value}")
