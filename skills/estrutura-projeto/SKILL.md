---
name: auditor-estrutura-projeto
description: Use para criar, reorganizar ou localizar arquivos no Auditor de Preço Justo — árvore de pastas oficial, o que mora em cada pasta, o que fica fora do Git e onde cada setor guarda código, documentos, testes e resultados.
---

# Estrutura do projeto

> Leia antes: `visao-geral`. Depois: `boas-praticas-python` e `ambiente-e-infra`.

## Objetivo

Manter **uma única árvore de pastas**, igual para todos, para que cada arquivo tenha um lugar previsível e os imports funcionem a partir da raiz.

## Árvore oficial

```
.
├── README.md                  visão geral, como rodar, governança, equipe, uso de IA
├── DATA.md                    regras dos dados (versão, alvo, recorte, divisão, colunas, privacidade, limitações)
├── Dockerfile                 imagem única da API e do painel
├── docker-compose.yml         serviços: postgres (pgvector), api (8000), streamlit (8501)
├── requirements.txt           dependências da aplicação (versões fixas, ver ambiente-e-infra)
├── requirements-dev.txt       -r requirements.txt + pytest, pytest-cov, httpx, httpx2, linters
├── requirements-genai.txt     -r requirements.txt + sentence-transformers, torch (CPU)
├── pytest.ini                 [pytest] pythonpath = .
├── .gitignore / .dockerignore .env, data/raw/*, *.joblib, .venv etc. fora
├── .streamlit/config.toml     tema escuro do painel
├── .github/workflows/ci.yml   CI com serviço pgvector e pytest
├── data/raw/                  CSVs (FORA do Git) + diretorio.md
├── db/                        SQL que roda sozinho na 1ª criação do banco
│   ├── 01_schema_bondora.sql     emprestimo, cliente, historico_credito + CREATE EXTENSION vector
│   ├── 02_schema_macro.sql       euribor_mensal, selic_mensal, bc_credito_pessoal_mensal + vw_custo_do_dinheiro
│   ├── 03_view_modelagem.sql     vw_base_modelagem (recorte + alvo + conjunto)
│   ├── 04_view_retorno_realizado.sql  vw_retorno_realizado (backtest e ROI)
│   └── 05_…sql                   [EM ANDAMENTO] (Marcos) tabela das decisões do analista; nome do arquivo a confirmar
├── docs/
│   ├── DECISOES.md              decisões de modelagem numeradas, com o porquê
│   ├── glossario.md             siglas e termos
│   ├── qualidade_dados.md       relatório gerado por script (erros × alertas)
│   ├── exemplos_prever.json     exemplos ilustrativos da saída do prever(), um por situação
│   ├── casos_de_teste.json      casos REAIS da saída do prever(), 2 por situação (casos_de_teste())
│   ├── bpmn/                    processo em BPMN: auditor_preco_justo_v2 (.bpmn + .jpeg)
│   ├── figuras/                 gráficos da EDA (PNG numerados 01_, 02_ ...)
│   └── resultados/              métricas versionadas (JSON) + arquivos do lote da carteira
├── genai/
│   ├── FORMATO_JSON.md          contrato de entrada/saída do parecer (versionado)
│   ├── REGRAS_PARECER.md        regras de linguagem, ética, números, normas, recomendação
│   ├── normas/                  textos limpos das normas (.md) + FONTES.md
│   ├── prompts/                 parecer_v1.md, parecer_v2.md ...
│   ├── avaliacao/               CRITERIOS.md + resultados da avaliação
│   └── src/                     dividir, indexar, testar_busca, checagem, template, prompt, testar_llm
├── notebooks/
│   ├── dados/01_eda.ipynb
│   └── modelos/01_coortes … 10_bootstrap.ipynb   (numerados por etapa)
├── src/
│   ├── api/       main.py (FastAPI), schemas.py (pydantic)
│   ├── app/       main.py (tela Streamlit), componentes.py (formatação e HTML), carteira.py (leitura do lote)
│   ├── dados/     carga_bondora, carga_macro, validacao, relatorio_qualidade, moeda
│   └── modelos/   dados, variaveis, treino, xgb, prever, incerteza, segmentacao
├── modelos_salvos/              pacote_prever_v1.joblib (FORA do Git) + .gitkeep
├── infra/                       (reservado)
├── skills/                      guia do projeto por setor (este conjunto)
└── tests/
    ├── api/       test_api
    ├── app/       test_componentes, test_carteira
    ├── dados/     test_validacao, test_relatorio, test_moeda, test_esquema_sql, test_view_retorno, _dados_exemplo.py
    ├── modelos/   test_seguranca, test_contrato_prever, test_xgb, test_segmentacao, test_treino
    └── genai/     test_checagem, test_conferencia, test_regras, test_template, test_prompt
```

## Regras

1. Toda pasta de `tests/` e `src/dados`, `src/modelos` tem `__init__.py`. Pastas vazias levam `.gitkeep`.
2. **Imports sempre a partir da raiz** (`from src.modelos.prever import prever`, `from genai.src.checagem import ...`). O `pytest.ini` põe a raiz no caminho; o `src/app/main.py` acrescenta a raiz ao `sys.path`, porque `streamlit run` não faz isso.
3. **Fora do Git:** `.env`, `data/raw/*` (exceto `diretorio.md`), `*.joblib`, `.venv`. O repositório é público.
4. **Uma fonte da verdade por assunto:**
   - formatos JSON → `genai/src/checagem.py` (pydantic), documentados em `genai/FORMATO_JSON.md`;
   - colunas proibidas → `src/dados/carga_bondora.py` (`COLUNAS_*`), usadas por `src/modelos/variaveis.py`;
   - decisões de modelagem → `docs/DECISOES.md`;
   - regras dos dados → `DATA.md`.
   Os outros arquivos **importam** ou **citam**; não copiam.
5. Notebooks numerados por etapa; figuras da EDA numeradas em `docs/figuras/`; métricas em `docs/resultados/<nome>_vN.json`.
6. **Uma versão vigente por artefato.** Versão antiga sai do repositório (o Git guarda o histórico); nada de `_v1` e `_v2` lado a lado sem dizer qual vale.
7. **Nada sem uso.** Arquivo, função, constante ou dependência que ninguém usa sai no mesmo PR que a tornou inútil. A pseudonimização existe só na carga; a conexão da API com o banco volta junto com a tabela de decisões.

## Pronto quando

- `pytest tests/` coleta todos os testes sem erro de import.
- `streamlit run src/app/main.py` e `uvicorn src.api.main:app` sobem a partir da raiz.
- `git status` não mostra `.env`, CSVs nem `.joblib`.
