---
name: auditor-ambiente-e-infra
description: Use para preparar o ambiente local (venv, .env), subir banco, API e painel com Docker Compose, configurar a CI do GitHub Actions ou resolver problemas de versão de Python e dependências no Auditor de Preço Justo.
---

# Ambiente e infraestrutura

> Leia antes: `estrutura-projeto`, `boas-praticas-python`. Dono: Yasmin (App e infraestrutura).

## Objetivo

Qualquer pessoa do grupo sobe banco, API e painel com os mesmos comandos e as mesmas versões, e a CI prova que o projeto continua funcionando.

## Versão do Python e dependências

- **[A DECIDIR]** Versão do Python. Hoje: Dockerfile e CI em **3.11**, Yasmin em **3.12.10**, notebooks do Samuel em **3.14.5**. As versões abaixo exigem **Python ≥ 3.12** (o NumPy 2.5 não instala em 3.11).
  - Escolha padrão: **3.12** no Dockerfile, na CI e no README, desde que o `.joblib` abra no 3.12 com as versões fixas. Se não abrir, usar a versão do Samuel (3.14).
- Versões **fixas** no `requirements.txt` (as mesmas com que o `.joblib` foi gerado; sem elas o modelo pode não carregar):
  ```
  joblib==1.6.0
  numpy==2.5.4
  pandas==3.1.0
  scikit-learn==1.9.1
  scipy==1.18.1
  shap==0.54.1
  xgboost==3.4.1
  ```
- `requirements-dev.txt`: `-r requirements.txt` + pytest, pytest-cov, `httpx` **e `httpx2`** (o TestClient do Starlette atual exige o `httpx2`), linters.
- `requirements-genai.txt`: `-r requirements.txt` + sentence-transformers e torch CPU (`--extra-index-url https://download.pytorch.org/whl/cpu`). **[PENDENTE]** acrescentar `google-genai` (cliente do Gemini).
- Toda mudança de versão de biblioteca usada pelo modelo exige gerar o `.joblib` de novo.

## Ambiente local

```
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows (Mac/Linux: source .venv/bin/activate)
pip install -r requirements-dev.txt
```

`.env` na raiz (nunca no Git):
```
CLIENTE_ID_SAL=<chave de pelo menos 16 caracteres, igual para todo o grupo>
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/auditor_db
GOOGLE_API_KEY=<chave do Gemini>
```
Porta 5432 ocupada → `docker-compose.override.yml` local com 5433 e ajustar a URL.

## Docker

- `Dockerfile`: `python:<versão decidida>-slim` + `build-essential` + `libpq-dev`; instala `requirements.txt`; `COPY . .`; `CMD uvicorn src.api.main:app --host 0.0.0.0 --port 8000`.
- **[PENDENTE]** Para o parecer com IA, a imagem da API precisa também de `requirements-genai.txt` (busca nas normas + Gemini). Sem isso, o `gerar_parecer()` sempre cai para o template.
- `.dockerignore`: `.env`, `.venv`, `data/raw/*`, `*.joblib`, caches.

`docker-compose.yml`, com **um único nome para o serviço do banco: `postgres`** (no compose, no README e nas URLs):

| Serviço | Imagem / build | Porta | Ambiente | Volumes |
|---|---|---|---|---|
| `postgres` | `pgvector/pgvector:pg16`, banco `auditor_db` | 5432 | usuário/senha `postgres` | volume persistente + `./db:/docker-entrypoint-initdb.d` |
| `api` | `build: .` | 8000 | `DATABASE_URL=postgresql://postgres:postgres@postgres:5432/auditor_db`; **[PENDENTE]** `env_file: .env` para a chave do Gemini | `./modelos_salvos:/app/modelos_salvos` |
| `streamlit` | mesma imagem; `streamlit run src/app/main.py --server.port=8501 --server.address=0.0.0.0` | 8501 | `API_URL=http://api:8000` | `./docs/resultados:/app/docs/resultados` |

Os SQL de `db/` só rodam sozinhos na **primeira criação** do volume. Em banco já existente, aplicar à mão ou usar `--ddl` nas cargas.

## Ordem de execução

1. `docker compose up -d postgres`
2. `python src/dados/carga_bondora.py --csv data/raw/LoanData_Bondora.csv` (esperado: 179.235 contratos, 85.087 clientes)
3. `python src/dados/carga_macro.py`
4. Modelo: notebooks de `notebooks/modelos/` geram `modelos_salvos/pacote_prever_v1.joblib` (ou receber o arquivo do Samuel)
5. Normas: `python -m genai.src.dividir` e `python -m genai.src.indexar`
6. `docker compose up --build api streamlit`
   - painel: http://localhost:8501 · API: http://localhost:8000/docs · `GET /` mostra `"modelo_carregavel": true`

## CI (`.github/workflows/ci.yml`)

- Em push e PR para `main`.
- Serviço `pgvector/pgvector:pg16` com healthcheck `pg_isready`.
- Python na versão decidida, com cache de pip; instala `requirements.txt` + `requirements-dev.txt`.
- `pytest tests/ -v` com `DATABASE_URL` do banco temporário.
- Testes que exigem CSV ou `.joblib` se pulam sozinhos.

## Pronto quando

- `pytest tests/ -v` passa localmente e na CI.
- `docker compose up --build api streamlit` sobe sem erro; `GET /` mostra `modelo_carregavel: true`; o painel roda uma auditoria pelo formulário.
- O README descreve exatamente esses comandos.

## Armadilhas

- README mandando subir `db` enquanto o compose chama o serviço de `postgres`.
- Versões soltas (`>=`) no `requirements.txt`: o Docker instala versões mais novas que as do `.joblib` e o modelo não abre.
- Dependência citada na documentação e ausente nos requirements (aconteceu com LangChain e ruff).
- Esquecer `httpx2`: o teste da API passa num computador e quebra em outro.
