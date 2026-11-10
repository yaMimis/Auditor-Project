# syntax=docker/dockerfile:1
# Imagem única do Auditor de Preço Justo: a mesma serve a API (padrão) e o painel
# (o docker-compose troca o comando). Ordem pensada para o cache: o que muda pouco
# (sistema e bibliotecas) vem antes do código, que muda sempre.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Pacotes do sistema para compilar o psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Bibliotecas: requirements-genai.txt inclui o requirements.txt + busca nas normas
# (sentence-transformers, torch CPU, pgvector), Gemini e LangChain.
# O cache do pip fica guardado entre builds (BuildKit): se um requirement mudar,
# só ele é baixado de novo, e não o PyTorch inteiro (~1 GB).
COPY requirements.txt requirements-genai.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-genai.txt

# Código do projeto (o .dockerignore deixa de fora dados, notebooks, testes e segredos)
COPY . .

EXPOSE 8000 8501

# Padrão: API FastAPI na porta 8000, aceitando conexões de fora do container
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
