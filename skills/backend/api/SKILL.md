---
name: auditor-api
description: Aplique ao criar, alterar ou revisar o back-end do Auditor de Preço Justo (API FastAPI em src/api) — rotas, schemas pydantic, conversão do formulário para o prever(), parecer, referência do BC, gravação e leitura de decisões no banco, códigos de erro e testes da API.
---

# Back-end: API (FastAPI)

Ao criar, alterar ou revisar código em `src/api/` ou em `tests/api/`, siga estas regras. A API é a **única porta** para o modelo, o parecer e o banco: tudo que calcula ou grava passa por ela. Siga também as skills `auditor-governanca` e `auditor-contratos-dados` (seções 4 e 6).

## Antes de começar

- Leia `src/api/main.py` (rotas), `src/api/schemas.py` (formatos) e `src/api/banco.py` (PostgreSQL) antes de mudar qualquer um deles.
- Confira em `genai/src/checagem.py` os modelos `EntradaPrever`, `Motivo` e `Parecer`, que a API reaproveita.

## Onde colocar cada coisa

- Rotas e orquestração em `src/api/main.py`: a rota valida, chama quem calcula e devolve o resultado. Não escreva cálculo de risco, juro ou parecer na API.
- Formatos de entrada e saída em `src/api/schemas.py`, como modelos pydantic.
- Todo SQL e toda conexão em `src/api/banco.py` (psycopg2, `DATABASE_URL`, `connect_timeout=3`). Nenhuma rota abre conexão direto.
- Testes em `tests/api/test_api.py`.

## Rotas existentes (não mude o formato sem nova versão do contrato)

| Rota | Entrada | Saída | Erros |
|---|---|---|---|
| `GET /` | — | `{status, modelo_carregavel, banco_disponivel}` | — (healthcheck do Docker) |
| `POST /prever` | `SolicitacaoEmprestimo` | `RespostaPrever` (saída do `prever()` + `parecer_ia`) | 422 · 503 sem `.joblib` |
| `POST /parecer` | `RespostaPrever` já calculada | `Parecer` | 422 |
| `POST /decisoes` | `NovaDecisao` | `DecisaoRegistrada` (201) | 422 inválida ou recusada pelo banco · 503 banco fora |
| `GET /decisoes?contrato_id=&limite=` | limite 1–5000 (padrão 200) | lista de `DecisaoRegistrada` | 503 |
| `GET /decisoes/atuais` | — | lista de `DecisaoAtual` | 503 |

## Schemas

- Não duplique campos da GenAI: faça `RespostaPrever` herdar de `EntradaPrever` e `MotivoPrever` de `Motivo`, e use `Parecer` pronto de `genai/src/checagem.py`.
- Em `SolicitacaoEmprestimo`, mantenha `amount > 0`, `loan_duration` de 1 a 120, `interest_cobrado` de 0 a 500 (%), `country` reduzido à sigla em maiúsculas e `data_emprestimo` com padrão hoje e nunca no futuro.
- Em `NovaDecisao`, recuse `analista` e `justificativa` em branco, aceite só `manter_preco`, `revisar_preco` e `encaminhar_compliance`, mantenha `taxa_proposta` em fração ao ano (0–10] e use o `requisicao_id` (UUID) para não gravar o mesmo clique duas vezes.

## Regras

- Em `montar_contrato`, converta o formulário para os **nomes do banco**, inclua todas as chaves que o `prever()` exige (`None` sem dado), mande `juro_aa` em % e deixe **gênero e idade de fora**.
- No `/prever`, chame `prever()`, busque a taxa do BC do mês (`banco.taxa_bc`) e anexe o parecer com `_parecer()` → `gerar_parecer()` da Maria, numa resposta só.
- Em `montar_registro`, grave como JSON só a saída do `prever()` e o parecer, **nunca a solicitação**. Em revisão manual, grave PD, faixa e juros justos como nulos, nunca zero. Grave `taxa_proposta` só quando a decisão for `revisar_preco`.
- Nunca deixe uma falha virar erro 500: sem `.joblib`, devolva 503 explicado; sem Gemini ou chave, deixe o parecer cair no template; sem banco, devolva 503 nas rotas de decisão, e faça `taxa_bc` devolver `None`.
- Busque a taxa do BC pelo contrato em `vw_custo_do_dinheiro` e, sem contrato, pelo mês em `bc_credito_pessoal_mensal`.
- Carregue o modelo de busca nas normas uma vez, na subida (`ciclo_de_vida`); se falhar, suba a API mesmo assim.
- Não pseudonimize nada na API: a pseudonimização existe só na carga.

## Ao criar uma rota nova

1. Defina entrada e saída em `schemas.py`.
2. Escreva a função em `main.py`, com SQL em `banco.py` se precisar.
3. Mapeie cada falha para 422 ou 503 com mensagem em português.
4. Escreva o teste em `tests/api/test_api.py`, trocando o banco e o `prever()` por `monkeypatch`.
5. Acrescente a rota na tabela desta skill e, se o painel usar, na skill `auditor-painel`.

## Testes

- Comece o arquivo com `pytest.importorskip("fastapi")` e `pytest.importorskip("xgboost")` e use `TestClient` (exige `httpx2`).
- Mantenha a fixture automática que desliga o LLM, a busca nas normas e a taxa do BC; troque o `prever()` por saídas de `docs/exemplos_prever.json`. Nenhum teste pode precisar do `.joblib`, do banco real ou de internet.

## Ao terminar

- Rode `pytest tests/api -v` e confirme que passa.
- Com o Docker no ar, confirme em `http://localhost:8000/` que `modelo_carregavel` e `banco_disponivel` estão `true` e rode `POST /prever` pelo `/docs`.
- Atualize a "Situação atual" abaixo se entregou algo.

## Situação atual (11/11/2026)

- Já existe (não refaça): todas as rotas acima, parecer da Maria integrado, referência do BC, decisões no banco do Marcos, testes.
- Decidido: não existe rota de busca por ID de contrato; o painel abre contratos pela fila da carteira e pelos exemplos.
