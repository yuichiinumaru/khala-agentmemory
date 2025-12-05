from setuptools import setup, find_packages

setup(
    name="khala-memory",
    version="2.1.0",
    description="KHALA v2.1 - Knowledge Hierarchical Adaptive Long-term Agent",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "agno>=2.2.0",
        "surrealdb>=2.0.4",
        "google-generativeai>=0.8.0",
        "mcp>=1.0.0",
        "openai>=1.50.0",
        "redis>=5.0.0",
        "pydantic>=2.9.0",
        "numpy>=1.26.0",
        "scikit-learn>=1.5.0",
        "structlog>=24.0.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "networkx>=3.0.0",
        "fastapi>=0.115.0",
        "cachetools>=5.5.0",
        "uvicorn>=0.30.0"
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=5.0.0",
            "ruff>=0.6.0",
            "mypy>=1.11.0",
            "pre-commit>=3.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "khala=khala.interface.cli.main:cli",
        ],
    },
)
