---
name: auditor-infra
description: Aplique ao preparar o ambiente do Auditor de Preço Justo, mexer em requirements, .env, Dockerfile, docker-compose.yml, iniciar.ps1 ou na CI do GitHub Actions, ou ao resolver erro de versão, porta, build ou dependência. Para a nuvem (Terraform), siga infra/README.md.
---

# Infra: ambiente, Docker e CI

Ao criar, alterar ou revisar `Dockerfile`, `docker-compose.yml`, `iniciar.ps1`, `requirements*.txt`, `.dockerignore` ou `.github/workflows/ci.yml`, siga estas regras. O objetivo é que qualquer pessoa suba banco, API e painel com os mesmos comandos e as mesmas versões. Siga também a skill `auditor-estrutura`. O Terraform (`infra/`) é do Marcos: não o altere sem combinar.

## Versões e dependências

- Use **Python 3.14** em tudo (Dockerfile `python:3.14-slim`, CI e `.venv`): é a versão em que o `.joblib` foi gerado.
- Não mude estas versões do `requirements.txt` sem gerar o `.joblib` de novo (o modelo não abre com outras):
  ```
  joblib==1.6.0  numpy==2.5.4  pandas==3.1.0  scikit-learn==1.9.1
  scipy==1.18.1  shap==0.54.1  xgboost==3.4.1
  ```
- Ponha bibliotecas da busca nas normas, do Gemini e do LangChain em `requirements-genai.txt` (é o que a imagem instala).
- Ponha ferramentas de teste e lint em `requirements-dev.txt` (é o que a CI instala; inclui `httpx2`, exigido pelo `TestClient`).
- Não deixe biblioteca citada no README fora dos requirements, nem requirement que nada usa.

## `.env`

- Nunca faça commit do `.env`. As variáveis são:
  ```
  CLIENTE_ID_SAL=<chave do grupo, ≥ 16 caracteres>
  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/auditor_db
  GOOGLE_API_KEY=<chave do Gemini>
  ```
- Lembre que, dentro do Docker, a `DATABASE_URL` do compose (`postgres:5432`) vence a do `.env`.

## Docker

- Mantenha **uma imagem única** (`auditor-preco-justo:latest`) para API e painel: o `CMD` padrão é a API e o compose troca o comando do painel. Não crie uma segunda imagem.
- Mantenha no `Dockerfile` a ordem pensada para o cache: sistema → requirements (com `--mount=type=cache` do pip) → código.
- Mantenha fora da imagem (`.dockerignore`): `.env`, dados, notebooks, testes, skills, infra e `*.joblib`.
- Mantenha os serviços do `docker-compose.yml`:

| Serviço | Container | Porta | Depende de | Volumes |
|---|---|---|---|---|
| `postgres` (pgvector pg16) | `auditor_postgres` | 5432 | — | `postgres_data`; `./db` roda na 1ª criação do volume |
| `api` | `auditor_api` | 8000 | postgres saudável | `./modelos_salvos`, cache do modelo de embeddings |
| `streamlit` | `auditor_streamlit` | 8501 | api saudável | `./docs/resultados` |

- Mantenha os healthchecks (`pg_isready`; `GET /` na API com `start_period` de 180 s, porque a 1ª subida baixa o modelo das normas) e `restart: unless-stopped`.
- Faça os containers se acharem pelo nome do serviço (`API_URL=http://api:8000`), nunca por IP.
- Lembre que `db/*.sql` só roda sozinho na 1ª criação do volume; em banco existente, aplique à mão (o `iniciar.ps1` reaplica o `05`).

## `iniciar.ps1`

- Escreva só em ASCII (sem acento) e confira cada passo pelo `$LASTEXITCODE`.
- Mantenha a ordem: Docker ligado → portas 8000 e 8501 livres (a 5432 só gera aviso) → `.env` e `.joblib` → banco saudável e `db/05` reaplicado → imagem (só se faltar ou com `-Build`) → normas e séries do BC (só se faltarem; avise se faltar o `bcdata.sgs.20742.csv`) → API e painel → status e navegador.
- Mostre erros com a próxima ação em português ("Feche o programa X com: ...").

## CI (`.github/workflows/ci.yml`)

- Mantenha os dois jobs em push e PR para `main`:
  1. testes: serviço `pgvector/pgvector:pg16`, Python 3.14 com cache, `pip install -r requirements-dev.txt`, `db/0*.sql` em ordem, `db/testes/05_teste_decisoes.sql`, `pytest tests/ -v` com a `DATABASE_URL` do banco temporário;
  2. build da imagem com `docker/build-push-action`, sem publicar, com cache do GitHub.
- Faça testes que precisam de CSV real ou `.joblib` se pularem sozinhos; a CI não tem esses arquivos.

## Ao terminar

- Rode `pytest tests/ -v` e confirme que passa.
- Rode `.\iniciar.ps1 -Build` (ou `docker compose up -d --build`) e confirme o "Pronto"; em `http://localhost:8000/`, `modelo_carregavel` e `banco_disponivel` devem estar `true`.
- Depois do push, confirme a CI verde nos dois jobs (aba Actions do GitHub).
- Atualize a "Situação atual" abaixo se entregou algo.

## Situação atual (11/11/2026)

- Já existe (não refaça): imagem única com GenAI, compose com healthchecks, `iniciar.ps1` com checagem de portas e carga do BC, CI com banco, teste SQL e build.
- Em andamento (Marcos, não altere): Terraform na Google Cloud (`infra/`).
- A decidir: black e flake8 estão nos requirements e no README, mas não rodam na CI. Padrão até decidir: não falhar a CI por estilo.
