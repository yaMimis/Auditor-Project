# Skills do Auditor de Preço Justo

Esta pasta descreve o projeto **por setor**, para que uma IA (ou uma pessoa nova no grupo) consiga construir, manter ou replicar cada parte sem ler tudo de uma vez. Cada pasta tem um `SKILL.md` com o mesmo formato:

1. **Objetivo**: o que o setor entrega.
2. **Leia antes**: de quais outros setores ele depende.
3. **Arquivos**: onde fica no repositório.
4. **Regras**: requisitos. Número, nome de campo ou regra escrita aqui **é requisito, não sugestão**.
5. **Como construir**: ordem dos passos.
6. **Pronto quando**: testes e conferências que provam que está certo.
7. **Estado atual e pendências**: o que já existe e o que falta (com a escolha padrão até a decisão).
8. **Armadilhas**: erros que já aconteceram no projeto e não devem se repetir.

Marcadores usados: **[PRONTO]** já existe e funciona · **[EM ANDAMENTO]** alguém está fazendo (nome entre parênteses) · **[PENDENTE]** ainda não começou · **[A DECIDIR]** depende de decisão do grupo (o texto diz a escolha padrão).

Atualizado em **06/11/2026**, a partir do repositório nessa data.

## Mapa

```
skills/
├── README.md                     este índice
├── visao-geral/                  a ideia, o enquadramento, o fluxo e as frentes da equipe
├── estrutura-projeto/            pastas, arquivos e onde cada coisa mora
├── boas-praticas-python/         idioma, estilo, testes, documentação, versionamento de contratos
├── ambiente-e-infra/             venv, .env, Docker, Compose, CI e ordem de execução
└── regras_negocio/
    ├── governanca/               regras éticas e de LGPD que valem para todos os setores
    ├── dados/                    fontes, banco, carga, alvo, recorte, divisão, grupos de colunas
    ├── modelo_risco/             variáveis, XGBoost, calibração, métricas, faixas, revisão manual, SHAP
    ├── juro_justo/               fluxo de caixa, convenção nominal, LGD, margem, incerteza, situação do preço
    ├── contratos_dados/          formatos JSON entre as frentes (prever, parecer, API, carteira)
    ├── parecer_genai/            regras do parecer, RAG, prompt, LLM, checagem e template
    ├── auditoria_carteira/       lote da carteira, equidade, backtest, ROI e segmentação
    ├── api/                      FastAPI: rotas, schemas e conversões
    └── painel/                   Streamlit: telas, blocos, design e decisão do analista
```

## Ordem de leitura

- **Para entender o projeto:** `visao-geral` → `regras_negocio/governanca` → `regras_negocio/contratos_dados`.
- **Para construir do zero:** `estrutura-projeto` → `boas-praticas-python` → `ambiente-e-infra` → `dados` → `modelo_risco` → `juro_justo` → `contratos_dados` → `parecer_genai` → `api` → `painel` → `auditoria_carteira`.
- **Para mexer em um setor:** leia o `SKILL.md` dele, os setores em "Leia antes" e, sempre, `governanca` e `contratos_dados`.

## Como usar com uma IA

Envie à IA o `SKILL.md` do setor que ela vai trabalhar **junto** com `governanca` e `contratos_dados`. Peça que ela:

1. siga os números, nomes de campos e regras como requisitos;
2. não mude contratos de dados sem dizer explicitamente que é uma mudança de versão;
3. respeite os marcadores: em **[A DECIDIR]**, usar a escolha padrão e avisar; em **[EM ANDAMENTO]**, não reescrever o trabalho de outra frente;
4. só dê o setor por pronto quando a seção "Pronto quando" passar.
