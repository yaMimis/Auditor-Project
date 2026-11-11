---
name: auditor-estrutura
description: Aplique ao criar, mover, renomear ou procurar arquivos e pastas no Auditor de Preço Justo. Traz a árvore oficial, a fronteira entre back-end (src/api) e front-end (src/app), o que fica fora do Git e onde cada frente guarda código, testes e documentos.
---

# Estrutura do projeto

Ao criar, mover ou procurar arquivos neste projeto, siga a árvore e as regras abaixo. Não crie pastas novas na raiz sem necessidade; encaixe o arquivo na pasta que já existe para aquele tipo de conteúdo. Siga também a skill `auditor-boas-praticas-python`.

## Árvore oficial (coloque cada arquivo no lugar dela)

```
.
├── README.md                  visão geral, como rodar, governança, equipe, uso de IA
├── DATA.md                    regras dos dados (versão, alvo, recorte, divisão, colunas, privacidade, limitações)
├── Dockerfile                 imagem única da API e do painel (Python 3.14)
├── docker-compose.yml         serviços: postgres (pgvector, 5432), api (8000), streamlit (8501)
├── iniciar.ps1                atalho do Windows para subir, reconstruir e parar
├── requirements.txt           bibliotecas do modelo (versões fixas)
├── requirements-genai.txt     + busca nas normas, Gemini e LangChain (é o que a imagem instala)
├── requirements-dev.txt       + pytest, httpx2, LangChain e linters (é o que a CI instala)
├── pytest.ini                 [pytest] pythonpath = .
├── .gitignore / .dockerignore .env, data/raw/*, *.joblib, .venv etc. fora
├── .streamlit/config.toml     tema escuro do painel
├── .github/workflows/ci.yml   testes com banco temporário + build da imagem
├── src/
│   ├── api/                   BACK-END (FastAPI): main.py rotas · schemas.py formatos · banco.py PostgreSQL
│   ├── app/                   FRONT-END (Streamlit): main.py telas · estilo.css visual · componentes.py blocos HTML · carteira.py lote
│   ├── modelos/               modelo de risco e juro justo: prever(), treino, xgb, incerteza, carteira (lote), equidade
│   └── dados/                 cargas do Bondora e das séries de juros, validação, relatório de qualidade
├── genai/
│   ├── FORMATO_JSON.md        contrato de entrada e saída do parecer (versionado)
│   ├── REGRAS_PARECER.md      regras de linguagem, ética, números, normas e recomendação
│   ├── normas/                textos das normas (.md) + FONTES.md
│   ├── prompts/               parecer_v1.md … parecer_v4.md
│   ├── avaliacao/             CRITERIOS.md, casos, avaliar.py e resultados por versão do prompt
│   └── src/                   checagem, template, prompt, cadeia (gerar_parecer), dividir, indexar, testes manuais
├── db/                        SQL que roda na 1ª criação do banco
│   ├── 01_schema_bondora.sql     emprestimo, cliente, historico_credito + extensão vector
│   ├── 02_schema_macro.sql       Euribor, Selic, taxa do BC + vw_custo_do_dinheiro
│   ├── 03_view_modelagem.sql     vw_base_modelagem (recorte + alvo + conjunto)
│   ├── 04_view_retorno_realizado.sql  vw_retorno_realizado (backtest e ROI)
│   ├── 05_decisoes_analista.sql  decisões do analista (só inserção) + vw_decisao_atual
│   └── testes/05_teste_decisoes.sql  teste das regras da tabela de decisões (roda na CI)
├── infra/                     Terraform: VM na Google Cloud com o mesmo Docker Compose (README próprio)
├── docs/
│   ├── DECISOES.md            decisões de modelagem numeradas, com o porquê
│   ├── ROTEIRO_DEMO.md        roteiro da apresentação, plano B e perguntas prováveis
│   ├── glossario.md, qualidade_dados.md
│   ├── exemplos_prever.json   um exemplo ilustrativo por situação
│   ├── casos_de_teste.json    casos REAIS da saída do prever(), 2 por situação
│   ├── bpmn/, figuras/
│   └── resultados/            métricas versionadas + arquivos do lote da carteira (lidos pelo painel)
├── notebooks/
│   ├── dados/01_eda.ipynb
│   └── modelos/01_coortes … 10_bootstrap.ipynb   (numerados por etapa)
├── data/raw/                  CSVs (FORA do Git) + diretorio.md
├── modelos_salvos/            pacote_prever_v1.joblib (FORA do Git) + .gitkeep
├── skills/                    guia do projeto por frente (este conjunto)
└── tests/                     mesma divisão do src/: api, app, dados, modelos, genai
```

## Back-end e front-end

- Coloque rotas, validação e acesso ao banco em `src/api/` (back-end). Coloque telas, visual e formatação em `src/app/` (front-end).
- Nunca importe `src.api`, `src.modelos` ou `genai.src` dentro de `src/app/`; o front fala com o back só por HTTP. Nunca importe `src.app` no back-end.
- Mantenha os dois no mesmo repositório: eles compartilham o contrato de dados (`genai/src/checagem.py`), a imagem, o `docker-compose.yml` e a CI.

## Regras

- Crie `__init__.py` em toda pasta de `src/` e de `tests/`; use `.gitkeep` em pasta vazia.
- Escreva imports sempre a partir da raiz (`from src.modelos.prever import prever`, `from genai.src.checagem import ...`). O `pytest.ini` põe a raiz no caminho; o `src/app/main.py` acrescenta a raiz ao `sys.path`, porque `streamlit run` não faz isso.
- Espelhe o `src/` nos testes: código de `src/<parte>/` testado em `tests/<parte>/`.
- Mantenha fora do Git: `.env`, `data/raw/*` (exceto `diretorio.md`), `*.joblib`, `.venv`. O repositório é público.
- Use uma fonte da verdade por assunto e importe ou cite, nunca copie:
  - formatos JSON → `genai/src/checagem.py` (documentados em `genai/FORMATO_JSON.md`);
  - colunas proibidas → `src/dados/carga_bondora.py` (`COLUNAS_*`), usadas por `src/modelos/variaveis.py`;
  - decisões de modelagem → `docs/DECISOES.md`;
  - regras dos dados → `DATA.md`.
- Numere notebooks e figuras por etapa; grave métricas em `docs/resultados/<nome>_vN.json`.
- Mantenha uma versão vigente por artefato: a antiga sai do repositório (o Git guarda o histórico).
- Remova no mesmo PR o arquivo, a função ou a dependência que ficar sem uso.

## Ao terminar

- Rode `pytest tests/` e confirme que todos os testes são coletados sem erro de import.
- Confirme que `streamlit run src/app/main.py` e `uvicorn src.api.main:app` sobem a partir da raiz.
- Confirme que `git status` não mostra `.env`, CSVs nem `.joblib`.
