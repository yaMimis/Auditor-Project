---
name: auditor-visao-geral
description: Use para entender o Auditor de Preço Justo antes de mexer em qualquer setor — a ideia, o enquadramento (Bondora como substituto, análise jurídica hipotética, decisão humana), o fluxo ponta a ponta, as camadas de tecnologia e as quatro frentes da equipe.
---

# Visão geral do projeto

> Leia antes: nada (este é o ponto de partida). Depois: `regras_negocio/governanca` e `regras_negocio/contratos_dados`.

## Objetivo

Para cada contrato de crédito, o sistema **estima o risco de inadimplência**, diz **se o juro cobrado é justo para esse risco** e verifica **se clientes com o mesmo risco pagam juros diferentes por gênero ou idade**. Um **parecer gerado por IA**, apoiado em normas brasileiras, explica o resultado ao **analista, que decide**.

## Enquadramento (obrigatório manter)

- Produto pensado para o **mercado brasileiro** (segmento BFSI). Como não existe base pública brasileira de contratos individuais, usa-se a base real da plataforma estoniana **Bondora LoanData (2009–2021)** como substituta do comportamento de crédito.
- O motor de risco e preço usa o **contexto da época** de cada contrato (Euribor 12 meses do mês da concessão).
- A análise jurídica é **hipotética**: "se este contrato fosse de um banco brasileiro" (LGPD, CDC, normas do CMN e do Banco Central).
- O sistema **nunca decide sozinho**. O analista decide e pode encaminhar ao compliance (direito de revisão, LGPD art. 20).
- **País é variável de controle, não grupo auditado**: entra no modelo de risco (o default varia muito entre EE, ES e FI), mas a auditoria de equidade compara só gênero e idade.

## Fluxo ponta a ponta

```
Contrato (formulário do painel ou carteira)
  → API converte para os nomes do banco
  → modelo de risco: PD + faixa A–E + motivos SHAP          (regras_negocio/modelo_risco)
  → juro justo por fluxo de caixa + margem de incerteza      (regras_negocio/juro_justo)
  → situação do preço: acima / abaixo / dentro / revisão manual
  → busca das normas (RAG, pgvector)                         (regras_negocio/normas_rag)
  → parecer em JSON (LLM; ou template de reserva)            (regras_negocio/parecer_genai)
  → checagem dos números e das regras do parecer por código
  → painel do analista (Streamlit)                           (regras_negocio/painel)
  → decisão humana registrada: manter / revisar / compliance
```

Em paralelo, um **processo em lote** pontua a carteira inteira, estima a diferença de preço entre grupos de mesmo risco (gênero, idade) com intervalo de confiança, faz o backtest e grava arquivos que o painel lê (`regras_negocio/auditoria_carteira`).

## Camadas

| Camada | Tecnologias |
|---|---|
| Dados | pandas, pandera, PostgreSQL 16, SQLAlchemy 2, psycopg2 |
| Vetores | pgvector, extensão no **mesmo** PostgreSQL (imagem `pgvector/pgvector:pg16`) |
| Modelo | scikit-learn, XGBoost, SHAP, scipy (brentq), joblib |
| Parecer | LangChain (chain LCEL), Gemini (`langchain-google-genai`), sentence-transformers multilíngue, prompts versionados em Markdown |
| Serviço e app | FastAPI + uvicorn, Streamlit |
| Infra e qualidade | Docker + Docker Compose, pytest, GitHub Actions |
| Linguagem | Python 3.14 (ver `ambiente-e-infra`) |

## Frentes da equipe (donos de cada setor)

| Frente | Responsável | Setores |
|---|---|---|
| Dados e processo | Marcos | `dados`, BPMN, `docs/qualidade_dados.md`, glossário, tabela de decisões |
| Modelo e juro justo | Samuel | `modelo_risco`, `juro_justo`, `auditoria_carteira` (lote), `DECISOES.md` |
| GenAI | Maria | `normas_rag`, `parecer_genai`, `avaliacao_parecer`, `FORMATO_JSON.md`, `REGRAS_PARECER.md` |
| App e infraestrutura | Yasmin | `api`, `painel`, `ambiente-e-infra`, vídeo da demo |

**Contratos entre frentes só mudam com aviso a todas** (ver `regras_negocio/contratos_dados`).

## Documentos de referência no repositório

- `README.md`: visão geral, como rodar, governança, equipe e uso de IA.
- `DATA.md`: regras dos dados (Marcos).
- `docs/DECISOES.md`: decisões de modelagem numeradas, sempre com o porquê (Samuel).
- `genai/FORMATO_JSON.md` e `genai/REGRAS_PARECER.md`: contrato e regras do parecer (Maria).
- `docs/glossario.md`: siglas e termos.

Quando um `SKILL.md` e um desses documentos divergirem, **o documento do dono do setor vale**, e o `SKILL.md` deve ser corrigido.
