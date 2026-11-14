---
name: auditor-api
description: Use para construir ou alterar a API FastAPI do Auditor de Preço Justo — rotas, schemas, leitura do contrato no banco, prever() ao vivo, plano B pelo lote, Laboratório (cenários), lote da carteira, parecer, decisões do analista, códigos de erro e testes da API.
---

# API (FastAPI)

> Leia antes: `regras_negocio/contratos_dados` (seções 4 a 6), `regras_negocio/governanca`, `ambiente-e-infra`. Dono: Yasmin. Código: `src/api/main.py` (rotas), `src/api/schemas.py` (formatos), `src/api/database.py` (PostgreSQL), `src/api/contract_analysis.py` (tela Análise), `src/api/scenario.py` (Laboratório), `src/api/portfolio.py` (lote da carteira); testes em `tests/api/`; conferência com dados reais em `scripts/conferir_analise.py`.

## Objetivo

Ser a **única porta** para o modelo, o parecer, o banco e o lote: tudo que calcula, lê arquivo ou grava passa pela API. O painel só pede e mostra.

## Rotas

| Rota | Entrada | Saída | Erros |
|---|---|---|---|
| `GET /` | — | `{status, modelo_carregavel, banco_disponivel, versao_modelo, pacote_modelo, pacote_hash, genai_configurada, busca_normas}` | — (healthcheck do Docker; responde logo ao subir, a busca nas normas carrega em segundo plano) |
| `POST /predict` | `LoanRequest` | `PredictionResponse` (saída do `prever()` + `parecer_ia`) | 422 · 503 sem `.joblib` |
| `POST /opinion` | `PredictionResponse` já calculada | `Parecer` | 422 |
| `GET /portfolio/overview?year_min=&year_max=&country=&band=` | filtros opcionais | `PortfolioOverview` (anos, países, faixas, resumo, por faixa, backtest, equidade) | 503 sem lote |
| `GET /contracts?situation=&offset=&limit=` | situação opcional, limit 1–200 | `ContractList` (`total`, `itens` do lote, do mais distante da margem) | 422 · 503 sem lote |
| `GET /contracts/ids?limit=` | até 20000 (padrão 5000) | lista de IDs | 503 |
| `GET /contracts/export?situation=` | situação opcional | CSV (UTF-8 com BOM) | 503 |
| `GET /contracts/{id}` | ID | linha do lote (usada pela busca) | 404 · 503 |
| `GET /contracts/{id}/analysis` | ID do contrato da base | `ContractAnalysis`: `resultado` (saída do `prever()` + parecer), `contrato`, `dados_considerados` (21 variáveis: 17 fornecidas, 4 derivadas), `precificacao`, `resultado_observado` (só 2009–2016 encerrados; `vw_desfecho_contrato`), `motivo_sem_desfecho` (quando não há desfecho), `procedencia` | 404 fora do banco e do lote · 503 (ver plano B) |
| `POST /contracts/{id}/scenario` | `ScenarioChanges` (só os campos trocados; `{}` = só o original) | `ScenarioResult`: `original`, `cenario`, `parcela_original`, `parcela_cenario`, `efeitos` (cada campo trocado sozinho), `campos` (formulário com valor atual e limites), `procedencia` | 404 · 422 fora dos limites ou campo desconhecido · 503 banco ou modelo fora (sem plano B) |
| `POST /decisions` | `NewDecision` | `RecordedDecision` (201) | 422 · 503 banco fora |
| `GET /decisions?contrato_id=&limit=` | limit 1–5000 (padrão 200) | lista de `RecordedDecision` | 503 |
| `GET /decisions/current` | — | lista de `CurrentDecision` | 503 |

As rotas fixas `/contracts/ids` e `/contracts/export` ficam declaradas **antes** de `/contracts/{id}`.

## Regras

1. **A API não calcula por fora do modelo.** A Análise usa `preparar_contrato()`, `parametros_preco()` e `juro_justo()` de `src/modelos/prever.py` (as mesmas do `prever()`); a parcela do Laboratório usa `_parcela()` de `src/modelos/carteira.py`. Se a precificação não reproduzir o juro justo do `prever()`, ela vai como `null`.
2. **Gênero, idade, estado civil e dependentes nunca entram**: a consulta do contrato tem lista explícita de colunas (`database.CONTRACT_COLUMNS`), o `ScenarioChanges` recusa campos fora da lista (`extra="forbid"`) e o registro da decisão grava só a saída do `prever()` e o parecer.
3. **Procedência honesta** em toda resposta de contrato: `modo` (`ao_vivo` ou `lote`), `calculado_em` (null no lote), arquivo, hash (12 caracteres do SHA-256) e data do pacote, `incerteza` (`bootstrap` quando o `prever()` devolveu `pd_ic95`; `margem_padrao` quando o pacote não tem bootstrap e a margem é ±2 p.p. do juro justo, **não** um intervalo da PD; `nao_calculada` em revisão manual) e o número de reamostragens.
4. **Plano B na rota de análise (decidido em 13/11):** banco fora, modelo ausente ou contrato fora do banco → números do lote com `modo: "lote"` e `motivo_lote`, sem motivos, parâmetros e dados considerados. Nunca marcar número do lote como calculado agora. O Laboratório **não** tem plano B: cenário sem modelo ao vivo é 503.
5. **Laboratório:** limites de valor, prazo e renda vêm do pacote (`faixas_treino`, 0,5% a 99,5% do treino); dívidas (valor e número) e empréstimos anteriores usam limites **provisórios** (`scenario.PROVISIONAL_LIMITS`) até o Samuel passar os do treino. Fora dos limites = 422, sem rodar o modelo. O juro cobrado é controle à parte: muda situação e parcela, nunca a PD. O "O que mudou o risco" roda o `prever()` com cada campo trocado sozinho.
6. **Decisões:** recuse analista e justificativa em branco; `taxa_proposta` só em `revisar_preco` (fração ao ano); `requisicao_id` (UUID) impede gravar o mesmo clique duas vezes; em revisão manual PD, faixa e juros justos vão nulos, nunca zero.
7. Nenhuma falha vira 500: sem `.joblib` → 503 explicado; sem Gemini ou chave → template; sem banco → 503 nas decisões e `bc_rate()` devolve `None`.
8. Todo SQL e conexão em `database.py` (`connect_timeout=3`); o lote só em `portfolio.py` (cache pela data do arquivo).
9. **Combinado do `loan_id` (13/11, com Marcos e Samuel):** o banco guarda em minúsculas; o ID digitado é normalizado no Python (`database.normalize_id`: `strip().lower()`), nunca com `lower(loan_id)` na coluna (desligaria o índice). Depois da busca, o fluxo inteiro (prever, parecer, taxa do BC, desfecho e decisão) usa o `loan_id` que voltou do banco. O gatilho do `db/07` é a segunda barreira, nas decisões.

## Testes

- `tests/api/test_api.py`, `test_contract_analysis.py`, `test_scenario.py`, `test_portfolio.py`, `test_portfolio_routes.py`: começam com `pytest.importorskip("fastapi")` e `("xgboost")`; banco, `prever()` e LLM trocados por `monkeypatch`. Nenhum precisa do `.joblib`, do banco real ou de internet.
- `tests/api/test_integracao_analise.py`: só roda com banco, pacote e lote reais (pulado no CI). Abre contratos reais e compara com o lote.

## Pronto quando

- `pytest -q` passa sem falhas com o banco, o pacote oficial e o lote no lugar.
- `python -m scripts.conferir_analise` termina com **20/20** (PD, juro justo, margem, situação, motivos presentes, nada de gênero ou idade).
- `GET /` com `modelo_carregavel` e `banco_disponivel` `true` e o `pacote_hash` igual ao do Samuel.

## Estado em 13/11/2026

- **[EM ANDAMENTO] (Yasmin)** Etapa 1 (análise ao vivo por ID, lote pela API, plano B na rota) e Etapa 2 (Laboratório): implementadas e com testes locais; **não concluídas** até o `conferir_analise` dar 20/20 com o pacote oficial (o `.joblib` usado no teste não tinha o bootstrap).
- **[DECIDIDO] (13/11)** removido `POST /simulate` (a simulação de juro agora é o Laboratório).
- **[PENDENTE] (Samuel)** limites do treino para dívidas e empréstimos anteriores (trocar os provisórios em `scenario.PROVISIONAL_LIMITS`).
- **[PENDENTE] (Yasmin)** Etapa 3: teste de invariância (rodar o `prever()` com gênero e idade trocados, sem mostrar os valores reais). Precisa de uma consulta separada só para esse teste.
