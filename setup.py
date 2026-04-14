"""Setup script for Prompt Enhancer."""

from setuptools import setup, find_packages

setup(
    name="prompt-enhancer",
    version="1.0.0",
    description="Transform basic prompts into professional-grade prompts using o3",
    author="retolutz",
    python_requires=">=3.9",
    py_modules=["enhancer", "strategies", "cli"],
    install_requires=[
        "openai>=1.40.0",
        "rich>=13.7.0",
        "click>=8.1.7",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "prompt-enhancer=cli:cli",
        ],
    },
)
