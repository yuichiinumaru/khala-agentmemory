from setuptools import setup, find_packages

setup(
    name="khala-memory",
    version="2.0.0",
    description="KHALA v2.0 - Knowledge Hierarchical Adaptive Long-term Agent",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "agno>=2.2.0",
        "surrealdb>=1.0.0",
        "google-genai>=1.0.0",
        "mcp>=1.0.0",
        "openai>=2.6.0",
        "redis>=7.0.0",
        "pydantic>=2.12.0",
        "numpy>=2.3.0",
        "scikit-learn>=1.3.0",
        "asyncio-mqtt>=0.16.0",
        "structlog>=23.0.0",
        "click>=8.0.0",
        "rich>=13.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.0.0",
            "pre-commit>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "khala=khala.interface.cli.main:cli",
        ],
    },
)
