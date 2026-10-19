"""Catálogo de habilidades e classificação de nível pelo título da vaga.

Cada habilidade é uma expressão regular aplicada ao título + descrição (em minúsculas, sem HTML).
É contagem por palavra-chave: rápida, auditável e sem modelo, mas aproximada (veja "Limites" no README).
"""

from __future__ import annotations

import html
import re

SKILLS: dict[str, str] = {
    "Python": r"\bpython\b",
    "SQL": r"\bsql\b",
    "JavaScript/TypeScript": r"\b(javascript|typescript|node\.?js)\b",
    "Java": r"\bjava\b(?!script)",
    "C#/.NET": r"c#|\.net\b",
    "React": r"\breact\b",
    "AWS": r"\baws\b|amazon web services",
    "Azure": r"\bazure\b",
    "GCP": r"\bgcp\b|google cloud",
    "Docker": r"\bdocker\b",
    "Kubernetes": r"\bkubernetes\b|\bk8s\b",
    "CI/CD": r"ci\s*/\s*cd|github actions|gitlab ci|jenkins",
    "Git": r"\bgit\b|github|gitlab",
    "APIs REST": r"\bapis?\b|\brest(ful)?\b|fastapi|flask|django|spring boot",
    "LLM / IA generativa": r"\bllms?\b|ia generativa|genai|generative ai|large language",
    "RAG": r"\brag\b|retrieval[- ]augmented",
    "Agentes de IA": r"\bagentes?\b.{0,25}(\bia\b|intelig|aut[oô]nom)|ai agents?|multiagente|multi-agent|\ba2a\b",
    "LangChain/LangGraph": r"langchain|langgraph|llamaindex",
    "MCP": r"\bmcp\b|model context protocol",
    "Embeddings / banco vetorial": r"vetoria|\bvector|embeddings?|pinecone|faiss|pgvector|weaviate|chroma",
    "Avaliação de LLM": r"avalia[cç][aã]o de (modelos|llms?|ia)|\bevals?\b|guardrails?|alucina",
    "Prompt engineering": r"\bprompts?\b",
    "APIs de LLM (OpenAI/Anthropic/Gemini)": r"openai|anthropic|claude|gemini|bedrock",
    "Machine Learning": r"machine learning|aprendizado de m[aá]quina|scikit|xgboost",
    "Deep Learning": r"pytorch|tensorflow|deep learning|redes neurais",
    "MLOps": r"mlops|mlflow|sagemaker|vertex ai",
    "Pandas / NumPy": r"\bpandas\b|\bnumpy\b|jupyter",
    "Power BI / BI": r"power ?bi|tableau|looker|quicksight",
    "Spark / dbt / Airflow": r"\bspark\b|pyspark|databricks|airflow|\bdbt\b",
    "RPA / Power Automate": r"\brpa\b|power automate|uipath|automation anywhere",
    "n8n / Make / Zapier": r"\bn8n\b|make\.com|zapier",
    "Testes automatizados": r"testes? (automatizad|unit[aá]ri)|pytest|\bjest\b|\btdd\b",
    "Linux": r"\blinux\b",
    "Inglês": r"ingl[eê]s|\benglish\b",
    "Métodos ágeis": r"\bscrum\b|kanban|metodologias? [aá]geis|\bagile\b",
    "LGPD / segurança": r"\blgpd\b|seguran[cç]a da informa|privacidade",
}
_COMPILADAS = {nome: re.compile(rx) for nome, rx in SKILLS.items()}

NIVEIS = ["estágio", "júnior/trainee", "pleno", "sênior+", "não informado"]
_NIVEL = [
    ("estágio", re.compile(r"est[aá]gi|\bintern(ship)?\b")),
    ("júnior/trainee", re.compile(r"j[uú]nior|\bjr\b|trainee|\bentry\b")),
    ("pleno", re.compile(r"\bpleno\b|\bpl\b|\bmid\b")),
    ("sênior+", re.compile(r"s[eê]nior|\bsr\b|especialista|\blead\b|l[ií]der|coordenador|gerente|\bhead\b|staff|principal")),
]


def limpar(texto: str) -> str:
    """Tira HTML e entidades, junta espaços e passa para minúsculas."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", texto or ""))).strip().lower()


def extrair(texto: str) -> set[str]:
    """Habilidades citadas num texto já limpo."""
    return {nome for nome, rx in _COMPILADAS.items() if rx.search(texto)}


def nivel(titulo: str) -> str:
    """Nível da vaga pelo título. O primeiro que casar vence (estágio antes de júnior, júnior antes de sênior)."""
    t = (titulo or "").lower()
    for nome, rx in _NIVEL:
        if rx.search(t):
            return nome
    return "não informado"
