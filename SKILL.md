---
name: auditor-preco-justo
description: Use para construir (ou replicar) um "Auditor de Preço Justo" de crédito — sistema que estima o risco de inadimplência (PD) de cada contrato, calcula o juro justo por fluxo de caixa, compara com o juro cobrado, audita equidade por gênero/idade/país e gera um parecer em JSON com IA (RAG sobre normas brasileiras), sempre com decisão final humana. Segue a mesma arquitetura, contratos de dados, regras e parâmetros do projeto de referência.
---

# Auditor de Preço Justo — guia de estrutura e construção

Este documento descreve um projeto existente com precisão suficiente para que você (a IA) construa um projeto **equivalente**: mesma ideia, mesma arquitetura em camadas, mesmos contratos de dados, mesmas regras de governança e os mesmos parâmetros. Onde houver um número, um nome de campo ou uma regra, trate-o como requisito, não como sugestão. Onde o projeto original ainda tem pendências, o documento diz isso e indica a escolha padrão.

Idioma do projeto: **português do Brasil** em código (nomes de variáveis, funções, colunas), documentação, commits e textos ao usuário. Termos técnicos consagrados (PD, LGD, AUC, SHAP, RAG) ficam em inglês/sigla.

---

## 1. A ideia em uma frase

Para cada contrato de crédito, o sistema **estima o risco de inadimplência**, diz **se o juro cobrado é justo para esse risco** e verifica **se clientes com o mesmo risco pagam juros diferentes por gênero, idade ou país**. Um **parecer gerado por IA**, apoiado em normas brasileiras, explica o resultado ao **analista, que decide**.

### Enquadramento (obrigatório manter)

- Produto pensado para o **mercado brasileiro** (segmento BFSI). Como não há base pública brasileira de contratos individuais, usa-se a base real da plataforma estoniana **Bondora LoanData (2009–2021)** como substituta do comportamento de crédito.
- O motor de risco e preço usa o **contexto da época** de cada contrato (Euribor do mês de concessão).
- A análise jurídica é **hipotética**: "se este contrato fosse de um banco brasileiro" (LGPD, CDC, normas do Banco Central/CMN).
- O sistema **nunca decide sozinho**. O analista decide e pode encaminhar ao compliance (direito de revisão, LGPD art. 20).

---

## 2. Arquitetura (fluxo ponta a ponta)

```
Contrato
  → modelo de risco (PD + faixa A–E + motivos SHAP)
  → juro justo por fluxo de caixa (+ margem de incerteza)
  → comparação com o juro cobrado (situacao_preco)
  → busca das normas (RAG, pgvector)
  → parecer em JSON (LLM, ou template de reserva)
  → checagem dos números do parecer contra a API
  → painel do analista (Streamlit)
  → decisão humana (manter / revisar / encaminhar ao compliance)
```

Em paralelo, um processo **em lote**: calcular o juro justo de toda a carteira, estimar a diferença de preço por gênero, idade e país (com intervalo de confiança) e gravar os resultados no banco para o painel de auditoria por grupo.

| Camada | Tecnologias |
|---|---|
| Dados | pandas, pandera, PostgreSQL 16, SQLAlchemy 2, psycopg2 |
| Vetores | pgvector (extensão no **mesmo** PostgreSQL; imagem `pgvector/pgvector:pg16`) |
| Modelo | scikit-learn, XGBoost ≥ 2, SHAP, scipy (brentq), statsmodels, fairlearn |
| Parecer | API de LLM com saída estruturada, LangChain (opcional), sentence-transformers multilíngue |
| Serviço e app | FastAPI + uvicorn, Streamlit (+ streamlit-echarts) |
| Infra e qualidade | Docker + Docker Compose, pytest (+ pytest-cov, httpx), ruff/black/flake8, GitHub Actions |
| Linguagem | Python 3.11 |

---

## 3. Estrutura de pastas (reproduzir exatamente)

```
.
├── README.md                 visão geral, arquitetura, como rodar, governança, equipe, uso de IA
├── DATA.md                   regras dos dados (versão, alvo, recorte, divisão, colunas, privacidade, limitações)
├── Dockerfile                python:3.11-slim + build-essential + libpq-dev; CMD uvicorn src.api.main:app :8000
├── docker-compose.yml        serviços: postgres (pgvector), api (8000), streamlit (8501)
├── requirements.txt          dependências da aplicação
├── requirements-dev.txt      -r requirements.txt + pytest, pytest-cov, httpx, linters, matplotlib, seaborn
├── requirements-genai.txt    -r requirements.txt + sentence-transformers, torch (CPU)
├── pytest.ini                [pytest] pythonpath = .
├── .gitignore / .dockerignore  (.env, data/raw/*, modelos_salvos/, .venv etc. fora)
├── .streamlit/config.toml    tema escuro (ver seção 10)
├── .github/workflows/ci.yml  CI com serviço pgvector e pytest
├── data/
│   ├── .gitkeep
│   └── raw/                  CSVs (FORA do Git) + diretorio.md
├── db/                       SQL que roda sozinho na 1ª criação do banco (docker-entrypoint-initdb.d)
│   ├── 01_schema_bondora.sql   tabelas emprestimo, cliente, historico_credito + CREATE EXTENSION vector
│   ├── 02_schema_macro.sql     euribor_mensal, selic_mensal, bc_credito_pessoal_mensal + vw_custo_do_dinheiro
│   └── 03_view_modelagem.sql   vw_base_modelagem (recorte + alvo + conjunto treino/teste)
├── docs/
│   ├── DECISOES.md             decisões de modelagem numeradas, com o porquê de cada uma
│   ├── glossario.md            siglas e termos (crédito, preço, dados, modelo, GenAI, governança)
│   ├── qualidade_dados.md      relatório de qualidade gerado por script (erros x alertas)
│   ├── exemplos_prever.json    exemplos reais da saída do prever()
│   ├── bpmn/                   processo em BPMN (.bpmn + imagem)
│   ├── figuras/                gráficos da EDA (PNG numerados 01_, 02_ ...)
│   └── resultados/             métricas versionadas em JSON (baseline_logistica_v1.json, xgboost_v2.json ...)
├── genai/
│   ├── FORMATO_JSON.md         contrato de entrada/saída do parecer (versionado)
│   ├── REGRAS_PARECER.md       regras de linguagem, ética, números, normas, recomendação (versionado)
│   ├── normas/                 textos limpos das normas em .md + FONTES.md
│   │   cdc.md, lgpd.md, cet.md, credito_oferta.md, ref.md, FONTES.md
│   ├── prompts/                parecer_v1.md, parecer_v2.md ...
│   ├── avaliacao/              CRITERIOS.md + resultados da busca (resultado_busca_v1.txt ...)
│   └── src/
│       ├── dividir.py          quebra as normas em trechos com trecho_id
│       ├── indexar.py          gera embeddings e grava no pgvector (tabela trechos_normas)
│       ├── testar_busca.py     perguntas de teste da recuperação (top 3)
│       ├── checagem.py         modelos pydantic (fonte da verdade) + conferência do parecer
│       └── template.py         parecer de reserva sem IA + escolha da recomendação
├── notebooks/
│   ├── dados/01_eda.ipynb
│   └── modelos/01_coortes, 02_variaveis, 03_baseline, 05_taxas, 06_xgboost, 07_lgd (.ipynb)
├── src/
│   ├── api/      main.py (FastAPI), schemas.py (pydantic), security.py
│   ├── app/      main.py (painel Streamlit)
│   ├── dados/    carga_bondora.py, carga_macro.py, validacao.py, relatorio_qualidade.py, moeda.py
│   ├── db/       database.py (engine/SessionLocal/get_db), models.py (SQLAlchemy)
│   └── modelos/  dados.py, variaveis.py, treino.py, xgb.py, prever.py, segmentacao.py
├── infra/        (reservado)
├── modelos_salvos/  pacote_prever_v1.joblib (FORA do Git)
└── tests/
    ├── dados/    test_validacao, test_relatorio, test_moeda, test_esquema_sql, _dados_exemplo.py
    ├── modelos/  test_seguranca, test_contrato_prever, test_xgb, test_segmentacao, test_treino
    └── genai/    test_checagem, test_conferencia, test_regras, test_template
```

Cada subpasta de `tests/` e `src/modelos` tem `__init__.py`. Pastas vazias levam `.gitkeep`.

---

## 4. Dados

### 4.1 Fontes e versão

- **Bondora LoanData:** 179.235 contratos, 112 colunas, concessões 2009–2021, data de corte 20/07/2021. Arquivo `data/raw/LoanData_Bondora.csv`; registrar o **SHA-256** no `DATA.md` e conferir antes de usar. O CSV nunca entra no Git (repositório público); é compartilhado por fora.
- **Euribor (BCE)**, série mensal (média do mês): 12 meses `FM.M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA` (principal) e 3 meses `FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA` (sensibilidade).
- **Selic (BCB, SGS 4189)**, "acumulada no mês anualizada base 252": só no cenário "modo Brasil". Meta Selic só para conferência.
- **BCB SGS 20742** (taxa média do crédito pessoal não consignado, PF): só **contexto** no painel/parecer, de 03/2011 em diante. Não calibra preço, não entra no modelo, e o parecer não conclui "justo/injusto" a partir dela.
- Janela das séries: 01/2009 a 07/2021.

### 4.2 Banco (PostgreSQL + pgvector)

Três tabelas com **uma linha por contrato**, ligadas por `loan_id` (GUID minúsculo, PK):

- `emprestimo` (pai): termos na concessão, saídas do modelo do Bondora, desfecho e pós-concessão.
- `cliente`: perfil do tomador **no momento do pedido**; inclui `cliente_id` (pseudonimizado, repete entre contratos).
- `historico_credito`: endividamento e histórico **antes** do contrato.

Séries: `euribor_mensal(mes, euribor_3m, euribor_12m)`, `selic_mensal(mes, selic_aa, selic_meta_aa)`, `bc_credito_pessoal_mensal(mes, taxa_aa)`. `mes` é sempre o **1º dia do mês** (converter o último dia do arquivo do BCE).

Views:
- `vw_custo_do_dinheiro`: cada contrato com as taxas do mês da concessão (LEFT JOIN, para não sumir contrato).
- `vw_base_modelagem`: aplica recorte, alvo e conjunto (seção 4.4).

Regras dos SQL: idempotentes (`IF NOT EXISTS`, `CREATE OR REPLACE`), numerados na ordem de execução, cabeçalho explicando o propósito e comentários `-- NomeNoCSV [LISTA NEGRA]` em cada coluna. Montados em `/docker-entrypoint-initdb.d` para rodar sozinhos na 1ª criação; as cargas aceitam `--ddl` para aplicar em banco já existente.

Nomes de colunas **em português**, mapeados do CSV (ex.: `Interest → juro_aa`, `LoanDuration → prazo_meses`, `Amount → valor_concedido`, `UserName → cliente_id`, `Gender → genero`, `Age → idade`, `Country → pais`, `DefaultDate → data_default`, `ProbabilityOfDefault → pd_bondora`).

### 4.3 Carga (`src/dados/carga_bondora.py`, `carga_macro.py`)

- Mapeamento declarativo CSV → banco com um dataclass `Col(csv, db, tipo, uso, dominio)`; tipos `id | hash | texto | upper | int | cod | dep | num | bool | data`; `uso` ∈ `lista_negra | so_auditoria | indisponivel`. Um dicionário `TABELAS` na ordem de carga (pai primeiro).
- Exportar os conjuntos `COLUNAS_LISTA_NEGRA`, `COLUNAS_SO_AUDITORIA`, `COLUNAS_INDISPONIVEIS_RECENTES` (derivados do `uso`), usados pelo modelo e pelos testes.
- Carga via `COPY`. **A carga não filtra nada** (inclui contratos ativos); recortes são feitos em view/consulta.
- Limpezas: `-1` em colunas de código → NULL; datas anteriores a 2000 (ex.: `0001-01-01`) → NULL; `n_dependentes` "10Plus" → 10; códigos fora do domínio barrados.
- **Moeda (`moeda.py`):** renda e passivos da Estônia antes de 01/01/2011 estão em coroas (EEK) → dividir por **15,6466**. Os valores dos empréstimos já estão em euro.
- **Pseudonimização:** `cliente_id = HMAC-SHA256(UserName, chave)` truncado em **16 caracteres**. Chave `CLIENTE_ID_SAL` (mínimo 16 caracteres) obrigatória, no `.env`, igual para todo o grupo; a carga falha sem ela. Trocar a chave exige recarregar o banco.
- Conferências após a carga: 179.235 contratos e 85.087 clientes distintos; nenhum contrato da janela sem taxa (a do BC só de 03/2011).

### 4.4 Alvo, recorte e divisão (números a reproduzir)

- **Alvo:** `inadimplente = 1` se `data_default` preenchida (atraso > 60 dias no Bondora); senão 0. **Não** usar `status`. Contratos que atrasaram e depois quitaram contam como inadimplentes.
- **Recorte (base de modelagem):** concessão 2009–2016 **e** encerrado (`status = 'Repaid'` ou `data_default` preenchida), **sem a Eslováquia** (`pais <> 'SK'`) → **29.916 contratos, 56,0% de default**.
- **Reestruturados ficam no modelo** (7.941, 76% de default; tirá-los seria selecionar por algo posterior à concessão). Saem **só da auditoria de preço** (flag `fora_da_auditoria`).
- **Sem rebalanceamento** (default já é maioria).
- **Divisão por tempo e por cliente:**

| Conjunto | Regra | Contratos | Default |
|---|---|---|---|
| treino (e validação) | 2009–2015 | 20.011 | 52,4% |
| teste | 2016, só clientes que **não** aparecem no treino | 7.311 (EE 3.642, ES 2.226, FI 1.443) | 67,1% |
| fora_cliente_repetido | 2016 de clientes do treino | 2.594 | — |
| carteira a pontuar | 2017 em diante (sem desfecho suficiente) | 147.978 (82,6%) | — |

- Validação dentro do treino: `GroupKFold(5)` por `cliente_id`. **Escolha de variáveis e hiperparâmetros só com validação temporal** (ajuste até 2014, validação em 2015). **O teste de 2016 não ajusta nada.**

### 4.5 Grupos de colunas

| Grupo | Colunas | Regra |
|---|---|---|
| **Lista negra (26)** | `juro_aa`, `parcela_mensal`, `rating`, `versao_modelo_bondora`, `pd_bondora`, `perda_esperada_bondora`, `lgd_bondora`, `retorno_esperado_bondora`, `status`, `data_default`, `dias_atraso`, `pior_categoria_atraso`, `reestruturado`, `data_vencimento_atual`, `data_fim_contrato`, `data_ultimo_pagamento`, `principal_pago`, `juros_multas_pagos`, `principal_baixado`, `juros_baixados`, `saldo_principal`, `recuperacao_principal`, `recuperacao_juros`, `ead1`, `ead2`, `estagio_recuperacao` | Nunca variável do modelo. `juro_aa` é o preço auditado (usá-lo seria auditoria circular); `parcela_mensal` embute o juro. |
| **Só auditoria (4)** | `genero`, `idade`, `estado_civil`, `n_dependentes` | Apenas auditoria de equidade, nunca para decidir/prever. |
| **Indisponíveis após 2017 (7)** | `finalidade`, `situacao_emprego`, `area_ocupacao`, `experiencia_trabalho`, `divida_renda`, `caixa_livre`, `renda_empregador_principal` | Fora do modelo (somem ou vêm com zero no lugar de vazio na carteira a pontuar). |
| **Identificadores e datas** | `loan_id`, `cliente_id`, `numero`, datas | Só para dividir/agrupar. O ano não é variável (o efeito de época vem da Euribor). |

### 4.6 Validação e qualidade (`validacao.py`, `relatorio_qualidade.py`)

- Um **esquema pandera por tabela**, separando **erros** (quebram o contrato dos dados e falham o teste) de **alertas** (ocorrências conhecidas, registradas sem falhar). Meta do original: **0 erros e 12 alertas**.
- Exemplos de regras: GUID válido em `loan_id`; datas na janela; `mes` no dia 1; contagem total = 179.235; contagens da view = `{"treino": 20011, "teste": 7311, "fora_cliente_repetido": 2594}`.
- Alertas típicos: juros > 100% a.a. (**legítimos**, não remover; máx. 264%), idade < 18, renda zero, `valor_concedido > valor_solicitado`, prazo < 3, `Current` com `data_default`, `caixa_livre` negativo, zeros no lugar de vazio a partir de 2018, gênero 2 ("indefinido", quase só Espanha → tratar como ausente), indício de erro de codificação de gênero em 2017–2019.
- O relatório gera `docs/qualidade_dados.md` (tabelas em Markdown, ação recomendada por regra).

---

## 5. Modelo de risco (`src/modelos/`)

### 5.1 Módulos

- `dados.py`: `ler_base()` (lê o CSV com os **mesmos nomes e tipos do banco**, reaproveitando o mapeamento da carga — trocável por SQL sem mudar o resto), `preparar()` (alvo, ano, recorte, `fora_da_auditoria`), `dividir()` (treino/teste). Constantes `ANOS_TREINO = range(2009, 2016)`, `ANO_TESTE = 2016`, `PAISES_FORA = {"SK"}`.
- `variaveis.py`: `PROIBIDAS = LISTA_NEGRA | SO_AUDITORIA | INDISPONIVEIS | IDENTIFICADORES`; listas `NUMERICAS`, `CATEGORICAS`, `TESTADAS_E_DESCARTADAS`; dicionário `ROTULOS` (nome legível de cada variável, vai no campo `rotulo`); `criar_variaveis(df, referencia=treino)`; `matriz(df)`.
- `treino.py`: `ks()`, `metricas()` (AUC, KS, Brier, default previsto × real), `metricas_por_grupo(df, p, "pais")`, `calibracao_por_faixa()`, `montar_baseline()` (logística), `validar_cruzado()`, `treinar_e_avaliar()`, `comparar_com_bondora()`, `divisao_temporal(treino, ano_validacao=2015)`, `comparar_grupos()`, `salvar()` (modelo em `modelos_salvos/`, métricas em `docs/resultados/<nome>_vN.json`). `SEMENTE = 42`, `N_FOLDS = 5`.
- `xgb.py`: classe `ModeloXGB` (pré-processamento + XGBoost + calibração Platt, com `predict_proba` estilo sklearn) e `motivos()` via SHAP.
- `prever.py`: `prever(contrato) -> dict` no formato do contrato (seção 7), `juro_justo()`, `montar_pacote()`, `salvar_pacote()`, `casos_de_teste()`.
- `segmentacao.py`: K-Means de perfis de cliente (seção 5.6).

### 5.2 Variáveis (v3 — 23 variáveis)

| Grupo | Variáveis |
|---|---|
| Pedido | `valor_concedido`, `prazo_meses`, `pais` |
| Renda e dívidas | `renda_total`, `parcela_neutra_sobre_renda`, `valor_sobre_renda`, `divida_sobre_renda`, `renda_relativa`, `passivos_existentes` |
| Perfil | `novo_cliente`, `tempo_emprego_atual`, `escolaridade`, `tipo_moradia`, `tipo_verificacao` |
| Histórico na plataforma | `n_emprestimos_anteriores`, `valor_emprestimos_anteriores`, `pagamentos_anteriores`, `quitacoes_antecipadas_qtd`, `quitacoes_antecipadas_valor` |
| Scores de bureau | `score_ee_mini` (numérica), `score_fi_asiakastieto`, `score_es_equifax`, `score_es_microl` (categóricas; fora do próprio país = `"sem_info"`) |

Regras de construção:
- **Parcela neutra** = `valor_concedido / prazo_meses` (**sem o juro**, que é vazamento), dividida pela renda.
- Divisão segura: **renda zero ou vazia vira NaN, nunca infinito**.
- `renda_relativa` = renda ÷ mediana por país e ano **calculada só no treino** (passar `referencia=treino`).
- Categóricas: vazio → `"sem_info"`; categorias com < 1% no treino ou desconhecidas → `"outros"`.
- `pais` **entra no modelo** (default EE 42%, ES 78%, FI 73%; sem ele, diferença de risco seria lida como discriminação), mas **não aparece nos motivos**.
- Testadas e descartadas (validação 2015): `fracao_concedida`, `caixa_livre_sobre_renda`, `divida_renda_bondora`, `refinanciamento_passivos`, `renda_assistencial_sobre_renda`, `renda_pensao_sobre_renda`.

### 5.3 Modelos

- **Baseline:** regressão logística com `log1p` nas variáveis assimétricas, padronização e one-hot.
- **Principal:** XGBoost regularizado com early stopping (50 rodadas). Fixos: `learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, n_estimators=2000, eval_metric="logloss", random_state=42`. Grade: `max_depth ∈ {3,4,5}`, `min_child_weight ∈ {5,20}`, `reg_lambda ∈ {1,10}`. One-hot com `handle_unknown="ignore", min_frequency=0.01`. Converter Int64/pd.NA para float64/np.nan antes do XGBoost.
- **Calibração** (Platt: logística sobre o logit) ajustada em 2015, **nunca em 2016**.
- **Comparação com `pd_bondora`: só AUC** (outro horizonte/definição; Brier não comparável).

### 5.4 Métricas e metas de referência

- Ordenação: AUC e KS. Preço (prioridade): Brier e curva de calibração. **Sempre também por país.**
- Referências do original no teste 2016: logística v3 AUC 0,716 / Brier 0,192; **XGBoost v2 AUC 0,727 (EE 0,709 · ES 0,647 · FI 0,572), KS 0,337, Brier 0,199**, default previsto 56,6% × real 67,1%; PD do Bondora AUC 0,670. Um projeto equivalente deve chegar à mesma ordem de grandeza e documentar o desvio de nível de 2016.
- Salvar métricas versionadas em JSON: `{"modelo", "data", "params", "teste": {"contratos", "default_real", "default_previsto", "auc", "ks", "brier"}}`.

### 5.5 Juro justo (`juro_justo(prazo, pd_total, lgd, custo_anual)`)

- **Método:** taxa anual em que o **valor presente esperado dos recebimentos = valor emprestado (1,0)**, resolvida com `scipy.optimize.brentq` em [1e-6, 5,0] (se não houver raiz, devolve 5,0).
- Risco mensal: `h = 1 − (1 − PD)^(1 / max(prazo, 12))` (**horizonte mínimo de 12 meses**: o default pode ocorrer após o fim do contrato).
- Desconto mensal `d = (1 + custo_anual)^(1/12) − 1`; amortização Price com `i = (1 + taxa)^(1/12) − 1`.
- Em cada mês: recebe a parcela com prob. `(1 − h)` e recupera `(1 − LGD) × saldo` com prob. `h`.
- **Custo do dinheiro:** Euribor 12m do mês de concessão, **piso em zero**, em fração; 3m só na sensibilidade.
- **LGD** realizada por país com defaults de 2014–2015: EE ≈ 0,34 · ES ≈ 0,76 · FI ≈ 0,55 (Bondora 0,75 é mais conservadora). Provisório no original: `LGD_PADRAO = 0.60`.
- **Custos + margem:** calibrados para a média do juro justo igualar a média do juro cobrado (por safra). Provisório: `MARGEM_PADRAO = 0.05` a.a.
- **Margem de incerteza:** IC 95% por bootstrap (provisório: ±2,0 pp).
- Sensibilidade: margem ±1 pp e LGD ±10 pp.
- `juro_aa` vem em % → **dividir por 100**. Reestruturados fora da comparação de preço.

### 5.6 Faixas, situação e revisão manual

- Faixas por PD: `< 0,30 → A`, `< 0,45 → B`, `< 0,60 → C`, `< 0,75 → D`, senão `E`.
- `situacao_preco`: `acima_do_justo` se cobrado > `juro_justo_max`; `abaixo_do_justo` se cobrado < `juro_justo_min`; senão `dentro_da_margem`.
- **`revisao_manual`** quando os dados estão fora da faixa de treino: país não visto no treino, ou `valor_concedido`, `prazo_meses`, `renda_total` vazios ou fora dos quantis 0,5%–99,5% do treino. Nesse caso PD, faixa e juros justos vêm `null`, `motivos = []` e `alerta_dados = true` (sempre juntos).
- **Motivos:** top fatores SHAP como `{variavel, rotulo, efeito ∈ {aumenta_risco, reduz_risco}}` (+ extras `valor`, `peso`); nunca país, gênero ou idade.
- O pacote salvo (`joblib`) contém: modelo, referência do treino (para `renda_relativa` e categorias), faixas do treino, países conhecidos e série Euribor 12m.

### 5.7 Segmentação (K-Means)

Agrupa clientes por perfil (valor, prazo, renda relativa, dívidas, parcela, histórico), ajustado no treino, `escolher_k` entre 2 e 8 com amostra de 5.000. **Não entra no modelo de risco**; sem juro, default, gênero, idade ou país nas variáveis. Serve para descrever a carteira (EDA e slides).

### 5.8 Auditoria de equidade (lote)

Estimar a diferença de juro cobrado **entre clientes de mesmo risco** por gênero (só 0 × 1, de preferência dentro de cada país), idade e país, com intervalo de confiança (auditoria de resíduos: juro cobrado − juro justo explicado pelo atributo). Registrar que excluir atributos do modelo não elimina proxies e que controlar por renda pode mascarar efeito de gênero. Resultado apresentado como **indício**, com as ressalvas de qualidade do dado.

---

## 6. Regras de achado (resumo)

| `situacao_preco` | Quando |
|---|---|
| `dentro_da_margem` | Diferença menor que a incerteza do modelo |
| `acima_do_justo` | Juro cobrado acima da margem do juro justo |
| `abaixo_do_justo` | Juro cobrado abaixo da margem do juro justo |
| `revisao_manual` | Dados fora da faixa de treino |

Backtest: os contratos "abaixo do justo" deram mais prejuízo? Se sim, a auditoria funciona. ROI calculado em euros na carteira real.

---

## 7. Contrato de dados `prever()` → `gerar_parecer()` (fonte da verdade: pydantic)

**Unidades:** PD e juros **sempre em fração** (0.249 = 24,9% a.a.). Datas ISO 8601 com fuso −03:00. A conversão para texto ("24,9% ao ano", "18,4%") é feita **pelo código**, com vírgula e uma casa.

### 7.1 Entrada (saída do `prever()`)

```json
{
  "contrato_id": "BO-483449",
  "versao_modelo": "xgboost_v2",
  "pd": 0.184,
  "faixa": "C",
  "juro_cobrado": 0.249,
  "juro_justo": 0.162,
  "juro_justo_min": 0.141,
  "juro_justo_max": 0.183,
  "situacao_preco": "acima_do_justo",
  "motivos": [
    {"variavel": "divida_sobre_renda", "rotulo": "dívidas em relação à renda", "efeito": "aumenta_risco"},
    {"variavel": "tempo_emprego_atual", "rotulo": "tempo no emprego atual", "efeito": "reduz_risco"}
  ],
  "alerta_dados": false,
  "pd_ic95": null,
  "diferenca_pp": 8.7
}
```

Extras (`pd_ic95`, `diferenca_pp`, `valor` e `peso` nos motivos) são **ignorados** pela GenAI (`extra="ignore"`).

### 7.2 Modelos pydantic (em `genai/src/checagem.py`)

```python
ChaveNumero = Literal["pd", "juro_cobrado", "juro_justo", "juro_justo_min", "juro_justo_max"]

class Motivo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    variavel: str
    rotulo: str
    efeito: Literal["aumenta_risco", "reduz_risco"]

class EntradaPrever(BaseModel):
    model_config = ConfigDict(extra="ignore")
    contrato_id: str
    versao_modelo: str
    pd: float | None = Field(default=None, ge=0, le=1)
    faixa: Literal["A", "B", "C", "D", "E"] | None = None
    juro_cobrado: float
    juro_justo: float | None = None
    juro_justo_min: float | None = None
    juro_justo_max: float | None = None
    situacao_preco: Literal["acima_do_justo", "abaixo_do_justo", "dentro_da_margem", "revisao_manual"]
    motivos: list[Motivo] = []
    alerta_dados: bool = False
    # validador: fora de revisao_manual, pd, faixa e juros justos são obrigatórios
    # propriedade vai_para_revisao_manual = situacao_preco == "revisao_manual" or alerta_dados

class Fonte(BaseModel):
    norma: str
    artigo: str
    trecho_id: str

class RespostaLLM(BaseModel):          # o que o LLM devolve (saída estruturada)
    resumo: str
    pontos_de_atencao: list[str] = Field(max_length=3)
    recomendacao_texto: str
    fontes: list[Fonte]
    numeros_citados: dict[ChaveNumero, float]

class Parecer(RespostaLLM):            # o que gerar_parecer() devolve à tela
    contrato_id: str
    recomendacao: Literal["manter_preco", "revisar_preco", "encaminhar_compliance", "revisao_manual"]
    origem: Literal["llm", "template"]
    versao_prompt: str                 # parecer_v1, parecer_v2 ... ou template_v1
    gerado_em: datetime
```

### 7.3 Saída (exemplo)

```json
{
  "contrato_id": "BO-483449",
  "resumo": "Cliente de risco moderado (faixa C, chance de não pagar de 18,4%). Se este contrato fosse de um banco brasileiro, o juro cobrado estaria acima do juro justo estimado para esse risco, mesmo considerando a margem de incerteza.",
  "pontos_de_atencao": [
    "O juro cobrado (24,9% ao ano) está acima da margem do juro justo estimado (14,1% a 18,3% ao ano; valor central 16,2% ao ano).",
    "A diferença não é explicada pelo risco estimado pelo modelo. É um indício a investigar, não uma conclusão."
  ],
  "recomendacao": "revisar_preco",
  "recomendacao_texto": "Recomenda-se revisar o preço deste contrato. Se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.",
  "fontes": [{"norma": "CDC", "artigo": "art. 6º, III", "trecho_id": "cdc-art6-1"}],
  "numeros_citados": {"pd": 0.184, "juro_cobrado": 0.249, "juro_justo": 0.162, "juro_justo_min": 0.141, "juro_justo_max": 0.183},
  "origem": "llm",
  "versao_prompt": "parecer_v1",
  "gerado_em": "2026-11-05T14:30:00-03:00"
}
```

Mantenha `docs/exemplos_prever.json` com casos reais (acima, abaixo, dentro, revisão manual) e um teste que os valide contra o pydantic. **Qualquer mudança de formato = nova versão do documento + aviso a todas as frentes.**

---

## 8. GenAI: regras do parecer (`REGRAS_PARECER.md`)

### 8.1 Quem decide o quê
- `prever()`: calcula todos os números e marca revisão manual.
- Código da cadeia: escolhe a recomendação, decide LLM × template, formata números, busca normas, confere o resultado.
- **LLM: só escreve** (resumo, pontos de atenção, texto da recomendação, escolha das fontes entre os trechos recebidos). Nunca calcula, nunca escolhe a recomendação, nunca decide.
- Analista: decisão final; só ele encaminha ao compliance.

### 8.2 Linguagem
- PT-BR, frases curtas, sem jargão jurídico. Resumo ≤ 2 frases; ≤ 3 pontos de atenção.
- **Modo hipotético:** "se este contrato fosse de um banco brasileiro".
- Usar: "indício", "ponto de atenção", "recomenda-se revisar", "recomenda-se encaminhar ao compliance".
- **Palavras proibidas:** ilegal, ilegalidade, crime, fraude, violação, viola, abusivo, abusiva, discriminação, irregular.
- Fatores pelo `rotulo`, nunca pelo nome técnico. A recomendação sempre termina com "A decisão final é do analista."

### 8.3 Ética e privacidade
- Nenhum identificador vai ao LLM (nem `contrato_id`, nem `versao_modelo`); o código reinsere depois.
- **Gênero, idade e país nunca aparecem no parecer de um contrato** (LGPD art. 6º, IX). Motivos ligados a esses atributos são filtrados (`motivos_permitidos()`).
- Nunca culpar o cliente; "abaixo do justo" é risco para o banco.

### 8.4 Números
- Todo número vem do `prever()`; o LLM copia os números já formatados, sem recalcular nem arredondar.
- Só podem aparecer: PD, juro cobrado, juro justo, mínimo e máximo da margem (e a faixa). Campo `null` nunca é citado. Todo número do texto entra em `numeros_citados` com o valor exato.
- Não falar de CET, tarifas ou encargos (não existem na base). Números do REF descrevem o mercado brasileiro e **nunca** aparecem no parecer.

### 8.5 Recomendação (escolhida pelo código, nesta ordem)

| # | Condição | Recomendação | Quem escreve |
|---|---|---|---|
| 1 | `revisao_manual` **ou** `alerta_dados` | `revisao_manual` | template (LLM **não** é chamado) |
| 2 | `acima_do_justo` | `revisar_preco` | LLM (indício; se a política não justificar, encaminhar ao compliance) |
| 3 | `abaixo_do_justo` | `revisar_preco` | LLM (preço pode não cobrir a perda esperada) |
| 4 | `dentro_da_margem` | `manter_preco` | LLM (não inventar problema) |

`encaminhar_compliance` existe no formato, mas **nunca é escolhida automaticamente**.

### 8.6 Template de reserva (`template.py`)
Usado em revisão manual, falha da API do LLM, **timeout > 20 s**, JSON inválido ou checagem reprovada. Monta o texto só com faixa, situação, números formatados e até 3 rótulos de motivos. `origem: "template"`, `versao_prompt: "template_v1"`, `fontes: []`, mesma recomendação da tabela. Fuso fixo −03:00.

### 8.7 Checagem (`conferir_parecer()` em `checagem.py`)
Confere: entrada válida (`EntradaPrever`; se inválida → revisão manual); resposta válida (`RespostaLLM`); cada valor de `numeros_citados` igual ao da entrada e cada número do texto correspondente a um valor recebido (tolerância 0,051 pp, por causa da 1 casa decimal); todo `trecho_id` está entre os recuperados; nenhuma palavra proibida (regex); nenhum atributo sensível (regex de gênero/idade/país); tamanho do resumo e dos pontos. Qualquer falha → template.

### 8.8 RAG
- Normas em `genai/normas/*.md`, copiadas das fontes oficiais e limpas (sem anotações, trechos revogados/vetados), com `FONTES.md` (arquivo, norma, artigos, URL oficial, data de acesso):
  - `lgpd.md` — Lei 13.709/2018, arts. 5º, 6º, 7º, 11, 12, 20
  - `cdc.md` — Lei 8.078/1990, arts. 2º, 3º, 4º, 6º, 30, 31, 39, 42, 42-A, 46, 47, 52, 54, 54-A a 54-D, 54-F, 54-G, 104-A a 104-C
  - `cet.md` — Res. CMN 4.881/2020, arts. 1º a 9º
  - `credito_oferta.md` — Res. CMN 5.004/2022, arts. 1º a 9º
  - `ref.md` — Relatório de Estabilidade Financeira do BC (decomposição do custo do crédito), dividido por parágrafo
- **Divisão (`dividir.py`):** um trecho por artigo; artigos longos quebrados em partes entre incisos/parágrafos (`TAMANHO_MAXIMO = 1000` caracteres, sobra < 300 junta à anterior, repete 150 caracteres do caput nas partes seguintes).
- **`trecho_id`:** `<arquivo>-art<número>-<parte>` (ex.: `cdc-art6-1`, `cdc-art54b-1`, `lgpd-art20-1`); REF: `ref-p<parágrafo>-1`. O inciso vai no campo `artigo` da fonte ("art. 6º, III").
- **Indexação (`indexar.py`):** embeddings `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensões) na tabela `trechos_normas` do pgvector.
- Busca: top 3–5 trechos entregues ao LLM com `norma`, `artigo`, `trecho_id`. O LLM só cita o que recebeu, nunca de memória. Sem trecho pertinente → `fontes: []` e a tela mostra "Não encontrei base normativa para este caso."

### 8.9 Avaliação (`genai/avaliacao/CRITERIOS.md`, definidos **antes** dos resultados)
20 casos: 5 acima, 4 abaixo, 4 dentro, 2 revisão manual, 5 difíceis (motivo com gênero, número extremo, trecho irrelevante). Critérios: recuperação no top 3 (meta ≥ 80%), fidelidade, consistência numérica (por código), citação correta, alucinação (meta zero na demo), regras, clareza (1–5). Cada caso rodado 2 vezes.

---

## 9. API (FastAPI, `src/api/`)

- `main.py`: `app = FastAPI(title="Auditor de Juros - API", version="1.0.0")`; `GET /` (status) e `POST /prever` que chama `prever()` e, em seguida, `gerar_parecer()`, devolvendo a saída do `prever()` + chave `parecer_ia` (objeto `Parecer`).
- `schemas.py`: pydantic de entrada e saída **idênticos ao contrato da seção 7** (importe os modelos de `genai/src/checagem.py` em vez de duplicá-los). A entrada usa os nomes de colunas do banco e `juro_aa` em %; a API converte para fração.
- Gênero e idade podem chegar na requisição para auditoria, mas **não** são passados ao modelo nem ao LLM.
- `security.py`: pseudonimização **HMAC-SHA256 com a chave `CLIENTE_ID_SAL`, truncada em 16 caracteres** — a mesma função da carga.
- `src/db/database.py`: `engine` a partir de `DATABASE_URL`, `SessionLocal`, `Base`, dependência `get_db()`. `models.py`: ORM das tabelas com relação 1:1 por `loan_id`.
- Documentação automática em `http://localhost:8000/docs`.

---

## 10. Painel do analista (Streamlit, `src/app/main.py`)

- Lê `API_URL` (padrão `http://localhost:8000`) e chama `POST {API_URL}/prever` com timeout de 15 s; trata erro de conexão com mensagem amigável.
- Formulário em etapas com checagem de revisão: **01 Dados pessoais · 02 Dados do empréstimo · 03 Score & histórico**, barra de progresso "REVISADO/PENDENTE" e botão principal "⚖️ EXECUTAR AUDITORIA DE PREÇO".
- Resultado: PD e faixa, juro cobrado × faixa do juro justo, situação do preço, motivos, referência de mercado do BC do mês (quando houver), e a seção **"📜 Parecer técnico automatizado (GenAI)"** com fontes clicáveis e origem (LLM/template).
- Ações do analista: manter preço (com justificativa), registrar recomendação de nova taxa, encaminhar ao compliance.
- Tela de auditoria de equidade da carteira por grupo.
- Tema (`.streamlit/config.toml`): `base="dark"`, `primaryColor="#D4AD70"`, `backgroundColor="#080D16"`, `secondaryBackgroundColor="#101A2A"`, `textColor="#F1F0EB"`, `font="sans serif"`; `headless=true`; `gatherUsageStats=false`. Sidebar recolhida; estado em `st.session_state`.

---

## 11. Infra, configuração e CI

- `.env` na raiz (nunca no Git):
  ```
  CLIENTE_ID_SAL=<chave de pelo menos 16 caracteres, igual para todo o grupo>
  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/auditor_db
  ```
  (chave do LLM também aqui). Porta ocupada → `docker-compose.override.yml` local com 5433.
- `docker-compose.yml`: `postgres` (`pgvector/pgvector:pg16`, banco `auditor_db`, volume persistente, `./db` em `/docker-entrypoint-initdb.d`), `api` (build `.`, porta 8000, `DATABASE_URL` apontando para o serviço do banco) e `streamlit` (mesma imagem, porta 8501, `API_URL=http://api:8000`). Use **um único nome** para o serviço do banco no compose, no README e nas URLs.
- Ordem de execução:
  1. `docker compose up -d postgres`
  2. `python src/dados/carga_bondora.py --csv data/raw/LoanData_Bondora.csv`
  3. `python src/dados/carga_macro.py`
  4. treinar e salvar o pacote do `prever()`
  5. `python -m genai.src.dividir` / `indexar`
  6. `docker compose up --build api streamlit`
- CI (`.github/workflows/ci.yml`): em push/PR para `main`, serviço `pgvector/pgvector:pg16` com healthcheck `pg_isready`, Python 3.11 com cache de pip, instala `requirements.txt` + `requirements-dev.txt`, roda `pytest tests/ -v` com `DATABASE_URL` do banco temporário. Testes que exigem o CSV ou o pacote salvo devem se pular sozinhos (`pytest.skip`) quando o arquivo não existir.

---

## 12. Testes obrigatórios

- **Segurança/antivazamento (`test_seguranca.py`):** nenhuma coluna de `PROIBIDAS` no modelo; `juro_aa` e `parcela_mensal` fora; nenhum cliente em treino e teste ao mesmo tempo; teste só 2016 e treino até 2015; renda zero não gera infinito; variáveis v2 calculadas; descartadas fora do modelo.
- **Contrato (`test_contrato_prever.py`):** os exemplos e `casos_de_teste()` do `prever()` passam no `EntradaPrever`; revisão manual ⇔ `alerta_dados` com números nulos; motivos sem país/gênero/idade.
- **Modelos:** `test_treino`, `test_xgb` (predict_proba em [0,1], calibração), `test_segmentacao`.
- **Dados:** `test_validacao` (esquemas pandera com dados de exemplo em `_dados_exemplo.py`), `test_moeda` (conversão EEK só para EE antes de 2011), `test_esquema_sql` (SQL cria as colunas e views esperadas), `test_relatorio`.
- **GenAI:** `test_checagem` (pydantic), `test_conferencia` (números, fontes, tamanho), `test_regras` (palavras proibidas e atributos sensíveis rejeitados), `test_template` (recomendação certa por situação, sem LLM em revisão manual).
- Dados de teste **sintéticos**; nenhum teste depende do CSV real para passar no CI.

---

## 13. Documentação (padrão de escrita)

- Cada documento começa com: título, **versão, data, responsável, revisor e status**; termina com **Pendências** (checkbox) e **Histórico** (versão, data, mudança).
- Itens não decididos marcados como **[A CONFIRMAR]**, com a escolha padrão adotada até a decisão.
- `DATA.md`: 1 Fonte e versão · 2 Unidade de análise · 3 Alvo · 4 Recorte · 5 Divisão treino/teste · 6 Colunas · 7 Valores especiais e qualidade · 8 Moeda e unidades · 9 Fontes externas · 10 Privacidade e LGPD · 11 Limitações · 12 Pendências.
- `docs/DECISOES.md`: seções numeradas (alvo, contratos usados, colunas proibidas, divisão, variáveis, modelo, métricas, juro justo, regra de achado, formato do `prever()`, segmentação, resultados com tabelas por versão e por país, observações, pendências), sempre com **o motivo** de cada decisão.
- `docs/glossario.md`: índice de siglas + tabelas "Termo | O que é | No projeto" por tema.
- `README.md`: descrição, status e datas, enquadramento, arquitetura, tabela de camadas, estrutura, como rodar, documentação, governança e ética, equipe por frente, **seção "Uso de IA no desenvolvimento"** (como cada frente usou assistentes e revisou o resultado).
- BPMN do processo com raias: Analista de crédito (Streamlit), Sistema e motor de regras (FastAPI), Motor de IA e RAG (LangChain, pgvector), Compliance; gateways "Juro fora da margem de incerteza?" e "Os números conferem?".
- Notebooks numerados por etapa; figuras da EDA numeradas e salvas em `docs/figuras/`.
- Equipe organizada em 4 frentes: **Dados e processo · Modelo e juro justo · GenAI · App e infraestrutura**. Contratos entre frentes só mudam com aviso a todas.

---

## 14. Governança e ética (não negociável)

1. Atributos sensíveis (gênero, idade, estado civil, dependentes) **só auditam, nunca decidem**.
2. O sistema **nunca decide sozinho**; o analista decide (LGPD art. 20).
3. O parecer fala em **indício e ponto de atenção**, nunca em ilegalidade; seus números são **checados contra a API**.
4. Identificadores não vão ao LLM nem a slides; `cliente_id` pseudonimizado com HMAC.
5. Dados brutos e segredos fora do Git.
6. Limitações declaradas: dados europeus de 2009–2021, só empréstimos aprovados, modelo usado fora da época de treino (2017–2021), teste mais arriscado que o treino, análise jurídica hipotética, possível erro de codificação de gênero em 2017–2019, proxies.

---

## 15. Como você deve trabalhar ao replicar o projeto

1. Crie a estrutura de pastas da seção 3 e os arquivos de configuração (seção 11).
2. Escreva `DATA.md`, `docs/DECISOES.md`, `genai/FORMATO_JSON.md` e `genai/REGRAS_PARECER.md` **antes** do código — eles são os contratos entre as frentes.
3. Dados: SQL → carga → validação → relatório de qualidade → EDA. Confira as contagens da seção 4.4.
4. Modelo: variáveis → baseline → XGBoost + calibração + SHAP → `juro_justo()` → `prever()` → testes de segurança e de contrato.
5. GenAI: normas → divisão → indexação → busca + avaliação → `checagem.py` → `template.py` → prompt → `gerar_parecer()`.
6. API e painel consumindo exatamente o contrato da seção 7.
7. Rode todos os testes; nada é dado como pronto com teste falhando.

Se adaptar para outra base de dados ou outro país, mantenha: a separação de colunas (lista negra / só auditoria / indisponíveis), a divisão por tempo **e** por cliente, o juro justo por fluxo de caixa com margem de incerteza, o contrato JSON, o LLM que só escreve e a checagem por código, e a decisão final humana.

### Armadilhas encontradas no projeto original (não repetir)

- O mock do `POST /prever` e o `schemas.py` da API divergiam do `FORMATO_JSON.md` (motivos sem `rotulo`, sem `revisao_manual`, campos não nulos, números inconsistentes entre `juro_cobrado` e `numeros_citados`). A API deve importar os modelos da GenAI e chamar o `prever()` real.
- `security.py` usava `sha256(username + sal)` em vez de HMAC truncado em 16 caracteres, o que gera `cliente_id` diferente do banco. Use uma única função compartilhada.
- O README mandava subir o serviço `db`, mas o compose o chamava `postgres`. Mantenha um nome só.
- LangChain e ruff aparecem na documentação, mas não nos requirements (lá estão black e flake8). Alinhe documentação e dependências.
- O texto e o notebook divergiam sobre excluir reestruturados; registre a decisão final num lugar só (`DECISOES.md`) e faça a view seguir esse lugar.
