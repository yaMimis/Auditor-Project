---
name: auditor-visao-geral
description: Aplique antes de qualquer tarefa nova no Auditor de Preço Justo ou ao explicar o projeto. Traz a ideia, o enquadramento obrigatório (Bondora como substituto, análise jurídica hipotética, decisão humana), o fluxo ponta a ponta, as tecnologias e quem é dono de cada parte.
---

# Visão geral do projeto

Ao começar uma tarefa ou explicar o projeto, use este contexto e mantenha o enquadramento abaixo em qualquer texto, código ou tela. Depois, siga as skills `auditor-governanca` e `auditor-contratos-dados` e a skill da parte em que vai trabalhar.

## O que o sistema faz

Para cada contrato de crédito, o sistema **estima o risco de inadimplência (PD)**, diz **se o juro cobrado é justo para esse risco** e verifica **se clientes com o mesmo risco pagam juros diferentes por gênero ou idade**. Um **parecer gerado por IA**, apoiado em normas brasileiras, explica o resultado ao **analista, que decide**.

## Enquadramento (mantenha sempre)

- Apresente o produto como pensado para o **mercado brasileiro** (BFSI), usando a base real **Bondora LoanData (2009–2021)** como substituta, porque não existe base pública brasileira de contratos individuais.
- Use o **contexto da época** de cada contrato no motor de preço (Euribor 12 meses do mês da concessão).
- Escreva a análise jurídica como **hipotética**: "se este contrato fosse de um banco brasileiro" (LGPD, CDC, CMN, Banco Central).
- Nunca faça o sistema decidir: o analista decide e pode encaminhar ao compliance (LGPD art. 20).
- Trate país como variável de controle, não como grupo auditado.

## Fluxo ponta a ponta

```
Contrato (formulário do painel ou carteira)
  → painel envia à API por HTTP/JSON                          (auditor-painel → auditor-api)
  → API converte para os nomes do banco e tira gênero e idade
  → modelo de risco: PD + faixa A–E + motivos SHAP          (auditor-modelo-risco)
  → juro justo por fluxo de caixa + margem de incerteza      (auditor-juro-justo)
  → situação do preço: acima / abaixo / dentro / revisão manual
  → busca das normas (RAG, pgvector)                         (auditor-normas-rag)
  → parecer em JSON (Gemini; ou template de reserva)         (auditor-parecer)
  → checagem dos números e das regras do parecer por código
  → painel mostra; o analista decide e a API grava           (auditor-painel, auditor-api)
```

Em paralelo, um **processo em lote** pontua a carteira, mede a diferença de preço entre grupos de mesmo risco (gênero, idade), faz o backtest e grava arquivos que o painel lê (`auditor-auditoria-carteira`).

## Tecnologias

| Camada | Tecnologias |
|---|---|
| Dados | pandas, pandera, PostgreSQL 16, psycopg2 |
| Vetores | pgvector no **mesmo** PostgreSQL (`pgvector/pgvector:pg16`) |
| Modelo | scikit-learn, XGBoost, SHAP, scipy, joblib |
| Parecer | LangChain (LCEL), Gemini, sentence-transformers multilíngue, prompts versionados |
| Back-end e front-end | FastAPI + uvicorn (porta 8000) e Streamlit (porta 8501) |
| Infra e qualidade | Docker Compose, Terraform (Google Cloud), pytest, GitHub Actions |
| Linguagem | Python 3.14 |

## Donos de cada parte

| Frente | Responsável | Skills e documentos |
|---|---|---|
| Dados e processo | Marcos | `auditor-base-de-dados`, `DATA.md`, BPMN, glossário, tabela de decisões, Terraform |
| Modelo e juro justo | Samuel | `auditor-modelo-risco`, `auditor-juro-justo`, `auditor-auditoria-carteira`, `docs/DECISOES.md` |
| GenAI | Maria | `auditor-normas-rag`, `auditor-parecer`, `auditor-avaliacao-parecer`, `genai/FORMATO_JSON.md`, `genai/REGRAS_PARECER.md` |
| App e infraestrutura | Yasmin | `auditor-api`, `auditor-painel`, `auditor-infra`, `auditor-estrutura` |

- Não mude o trabalho de outra frente sem avisar o dono.
- Não mude um contrato entre frentes sem aviso a todas.
- Quando uma skill divergir do documento do dono, siga o documento e aponte a skill a corrigir.
