"""Skill extraction from job description text.

Uses a two-pass approach:
1. Fast keyword dictionary matching (~200 common tech/professional skills)
2. Optionally, LLM-based extraction for richer results (uses existing gateway)
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Expanded known skill dictionary — case-insensitive matching
_KNOWN_SKILLS: set[str] = {
    # Programming languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab",
    "perl", "lua", "dart", "elixir", "haskell", "clojure",
    # Web frameworks
    "react", "angular", "vue", "next.js", "nuxt", "svelte", "django",
    "flask", "fastapi", "express", "spring", "spring boot", "rails",
    "asp.net", "laravel", "nest.js",
    # Data & ML
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "tensorflow", "pytorch", "scikit-learn", "pandas",
    "numpy", "spark", "hadoop", "airflow", "dbt", "etl",
    "data engineering", "data science", "data analysis", "data visualization",
    "power bi", "tableau", "looker",
    # AI & LLM
    "llm", "large language models", "openai", "gpt", "langchain", "rag",
    "agentic ai", "prompt engineering", "fine-tuning", "transformers",
    "generative ai",
    # Databases
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "dynamodb", "cassandra", "sqlite", "oracle", "snowflake", "bigquery",
    "databricks", "supabase",
    # Cloud & DevOps
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
    "terraform", "ansible", "jenkins", "github actions", "gitlab ci",
    "circleci", "ci/cd", "linux", "bash", "shell scripting",
    "nginx", "cloudflare", "vercel", "netlify", "heroku",
    # Infrastructure
    "microservices", "rest api", "graphql", "grpc", "websockets",
    "message queues", "rabbitmq", "kafka", "celery", "redis queue",
    "serverless", "lambda", "api gateway",
    # Testing
    "unit testing", "integration testing", "playwright", "selenium",
    "cypress", "jest", "pytest", "mocha", "test automation",
    # Security
    "oauth", "jwt", "authentication", "authorization", "encryption",
    "penetration testing", "soc2", "hipaa", "gdpr",
    # Mobile
    "ios", "android", "react native", "flutter", "mobile development",
    # Tools & Practices
    "git", "github", "gitlab", "bitbucket", "jira", "confluence",
    "agile", "scrum", "kanban", "devops", "sre",
    "observability", "monitoring", "grafana", "prometheus", "datadog",
    "logging", "sentry",
    # Soft skills / domains
    "communication", "leadership", "project management", "product management",
    "technical writing", "mentoring", "cross-functional",
    "fintech", "healthcare", "e-commerce", "saas", "b2b", "b2c",
    # Node/JS ecosystem
    "node", "node.js", "npm", "webpack", "vite", "babel",
    # Version control
    "version control", "code review", "pull requests",
}

# Multi-word skills sorted by length (longest first) for greedy matching
_MULTIWORD_SKILLS = sorted(
    [skill for skill in _KNOWN_SKILLS if " " in skill or "." in skill],
    key=len,
    reverse=True,
)


def extract_skills_from_text(text: str) -> list[str]:
    """Extract known skills from text via dictionary matching.

    Returns deduplicated, title-cased skill names.
    """
    if not text:
        return []

    lowered = text.lower()
    found: dict[str, str] = {}  # lowercase → display form

    # First pass: multi-word/dotted skills (greedy, longest first)
    for skill in _MULTIWORD_SKILLS:
        if skill in lowered:
            found[skill] = _display_form(skill)

    # Second pass: single-word skills with word boundary check
    for skill in _KNOWN_SKILLS:
        if skill in found:
            continue
        if " " in skill or "." in skill:
            continue
        # Word boundary: ensure skill is not part of a larger word
        pattern = rf"\b{re.escape(skill)}\b"
        if re.search(pattern, lowered):
            found[skill] = _display_form(skill)

    return sorted(found.values())


def extract_skills_with_llm(text: str, model_name: str | None = None) -> list[str]:
    """Optionally extract skills using the LLM gateway for richer results.

    Falls back to keyword matching if LLM is unavailable.
    """
    try:
        from app.services.llm_gateway import LLMGenerateRequest, generate_text

        response = generate_text(
            LLMGenerateRequest(
                model_name=model_name,
                system_prompt=(
                    "You are a skill extraction engine. Given a job description, "
                    "extract technical and professional skills. Return ONLY a JSON "
                    "array of skill strings, nothing else. Example: [\"Python\", \"AWS\", \"SQL\"]"
                ),
                prompt=f"Extract skills from this job description:\n\n{text[:2000]}",
                temperature=0.0,
                max_tokens=300,
            )
        )
        import json
        skills = json.loads(response.output_text)
        if isinstance(skills, list):
            return [str(s).strip() for s in skills if s]
    except Exception as exc:
        logger.debug("LLM skill extraction failed, using keyword fallback: %s", exc)

    return extract_skills_from_text(text)


def _display_form(skill: str) -> str:
    """Convert a lowercase skill to its display form."""
    # Known acronyms and special forms
    special = {
        "aws": "AWS", "gcp": "GCP", "sql": "SQL", "api": "API",
        "ci/cd": "CI/CD", "rest api": "REST API", "graphql": "GraphQL",
        "grpc": "gRPC", "jwt": "JWT", "oauth": "OAuth", "sre": "SRE",
        "llm": "LLM", "nlp": "NLP", "etl": "ETL", "dbt": "dbt",
        "rag": "RAG", "gpt": "GPT", "k8s": "K8s", "ios": "iOS",
        "devops": "DevOps", "github": "GitHub", "gitlab": "GitLab",
        "bitbucket": "Bitbucket", "jira": "Jira", "saas": "SaaS",
        "b2b": "B2B", "b2c": "B2C", "soc2": "SOC2", "hipaa": "HIPAA",
        "gdpr": "GDPR", "npm": "npm", "html": "HTML", "css": "CSS",
        "node.js": "Node.js", "next.js": "Next.js", "nest.js": "Nest.js",
        "asp.net": "ASP.NET", "c++": "C++", "c#": "C#", "r": "R",
        "golang": "Go", "react native": "React Native",
        "spring boot": "Spring Boot", "github actions": "GitHub Actions",
        "gitlab ci": "GitLab CI", "google cloud": "Google Cloud",
        "scikit-learn": "scikit-learn", "power bi": "Power BI",
        "redis queue": "Redis Queue",
    }
    if skill in special:
        return special[skill]
    return skill.title()
