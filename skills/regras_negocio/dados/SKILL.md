---
name: auditor-dados
description: Use para trabalhar nos dados do Auditor de Preço Justo — fontes (Bondora, Euribor, Selic, BC), esquema PostgreSQL, carga, pseudonimização, conversão de moeda, alvo, recorte, divisão treino/teste, grupos de colunas proibidas e validação com pandera.
---

# Dados

> Leia antes: `regras_negocio/governanca`, `estrutura-projeto`. Dono: Marcos (Dados e processo). Documento do dono: `DATA.md` (v0.7, 05/11/2026).

## Objetivo

Um banco único, carregado sem filtros, de onde saem a base de modelagem, a carteira a pontuar e os resultados realizados, com regras de qualidade explícitas.

## Arquivos

`db/01…04*.sql`, `src/dados/carga_bondora.py`, `carga_macro.py`, `moeda.py`, `validacao.py`, `relatorio_qualidade.py`, `DATA.md`, `docs/qualidade_dados.md`, `docs/glossario.md`, `notebooks/dados/01_eda.ipynb`, `tests/dados/`.

## Fontes

| Fonte | Uso | Janela no banco |
|---|---|---|
| **Bondora LoanData** — 179.235 contratos, 112 colunas, concessões 2009–2021, corte 20/07/2021. `data/raw/LoanData_Bondora.csv`, SHA-256 no `DATA.md` | base de crédito | completa |
| **Euribor (BCE)**, média mensal: 12 meses `FM.M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA` (principal), 3 meses `…EURIBOR3MD_.HSTA` (sensibilidade) | custo do dinheiro | 01/2009–07/2021 (a carga aborta se faltar mês) |
| **Selic (SGS 4189)**, acumulada no mês anualizada base 252 | só "modo Brasil" | 01/2009–07/2021 |
| **BC SGS 20742**, crédito pessoal não consignado PF, **% a.a. efetiva** | só **contexto** de mercado no painel/parecer; não calibra preço nem entra no modelo | 03/2011–07/2021 |

O pacote do modelo guarda a sua própria série Euribor 12m (01/1994–09/2026), usada para contratos novos.

## Banco (PostgreSQL 16 + pgvector)

- Três tabelas, **uma linha por contrato**, ligadas por `loan_id` (GUID minúsculo, PK): `emprestimo` (pai: termos, saídas do Bondora, desfecho), `cliente` (perfil no pedido; `cliente_id` pseudonimizado), `historico_credito` (endividamento **antes** do contrato).
- Séries: `euribor_mensal(mes, euribor_3m, euribor_12m)`, `selic_mensal(mes, selic_aa, selic_meta_aa)`, `bc_credito_pessoal_mensal(mes, taxa_aa)`. `mes` é sempre o **1º dia do mês**.
- Views: `vw_custo_do_dinheiro` (taxas do mês da concessão; LEFT JOIN para não perder contrato; `bc_credito_pessoal_aa` efetiva, NULL antes de 03/2011), `vw_base_modelagem` (recorte, alvo, conjunto), `vw_retorno_realizado` (resultado em euros por contrato, para backtest e ROI).
- SQL **idempotente** (`IF NOT EXISTS`, `CREATE OR REPLACE`), numerado na ordem de execução, cabeçalho com o propósito e comentário `-- NomeNoCSV [LISTA NEGRA]` em cada coluna.
- Nomes **em português**, mapeados do CSV: `Interest → juro_aa`, `LoanDuration → prazo_meses`, `Amount → valor_concedido`, `UserName → cliente_id`, `Gender → genero`, `Age → idade`, `Country → pais`, `DefaultDate → data_default`, `ProbabilityOfDefault → pd_bondora`.

## Carga

- Mapeamento declarativo `Col(csv, db, tipo, uso, dominio)`; tipos `id | hash | texto | upper | int | cod | dep | num | bool | data`; `uso ∈ lista_negra | so_auditoria | indisponivel`. Dicionário `TABELAS` na ordem (pai primeiro). Exporta `COLUNAS_LISTA_NEGRA`, `COLUNAS_SO_AUDITORIA`, `COLUNAS_INDISPONIVEIS_RECENTES`.
- Carga via `COPY`. **A carga não filtra nada**; recortes ficam em views.
- Limpezas: `-1` em código → NULL; datas antes de 2000 → NULL; `n_dependentes` "10Plus" → 10; código fora do domínio barrado.
- **Moeda:** renda e passivos da Estônia antes de 01/01/2011 em coroas → ÷ **15,6466** (`moeda.py`). Valores de empréstimo já em euro. O `ler_base()` do modelo aplica a mesma conversão.
- **Pseudonimização:** ver `governanca`, regra 7. A carga falha sem `CLIENTE_ID_SAL`.
- Conferências: 179.235 contratos e 85.087 clientes; nenhum contrato da janela sem taxa (BC só de 03/2011).

## Alvo, recorte e divisão (números a reproduzir)

- **Alvo:** `inadimplente = 1` se `data_default` preenchida (atraso > 60 dias); senão 0. **Não usar `status`.** Quem atrasou e depois quitou conta como inadimplente.
- **Recorte:** concessão 2009–2016, encerrado (`status = 'Repaid'` ou `data_default` preenchida), sem Eslováquia → **29.916 contratos, 56,0% de default**.
- **Reestruturados (7.941, 76% de default) ficam no modelo**; saem só da auditoria de preço (`fora_da_auditoria`).
- **Sem rebalanceamento.**

| Conjunto | Regra | Contratos | Default |
|---|---|---|---|
| treino (e validação) | 2009–2015 | 20.011 (13.972 clientes) | 52,4% |
| teste | 2016, só clientes que **não** estão no treino | 7.311 (EE 3.642 · ES 2.226 · FI 1.443) | 67,1% |
| fora_cliente_repetido | 2016 de clientes do treino | 2.594 | — |
| carteira a pontuar | 2017 em diante | 147.978 (82,6%) | — |

## Grupos de colunas

| Grupo | Colunas | Regra |
|---|---|---|
| **Lista negra (26)** | `juro_aa`, `parcela_mensal`, `rating`, `versao_modelo_bondora`, `pd_bondora`, `perda_esperada_bondora`, `lgd_bondora`, `retorno_esperado_bondora`, `status`, `data_default`, `dias_atraso`, `pior_categoria_atraso`, `reestruturado`, `data_vencimento_atual`, `data_fim_contrato`, `data_ultimo_pagamento`, `principal_pago`, `juros_multas_pagos`, `principal_baixado`, `juros_baixados`, `saldo_principal`, `recuperacao_principal`, `recuperacao_juros`, `ead1`, `ead2`, `estagio_recuperacao` | Nunca variável do modelo. `juro_aa` é o preço auditado; `parcela_mensal` embute o juro. |
| **Só auditoria (4)** | `genero`, `idade`, `estado_civil`, `n_dependentes` | Só auditoria de equidade. |
| **Indisponíveis após 2017 (7)** | `finalidade`, `situacao_emprego`, `area_ocupacao`, `experiencia_trabalho`, `divida_renda`, `caixa_livre`, `renda_empregador_principal` | Fora do modelo (somem ou vêm com zero no lugar de vazio na carteira). |
| **Identificadores e datas** | `loan_id`, `cliente_id`, `numero`, datas | Só dividir/agrupar. O ano não é variável. |

## Validação e qualidade

- Um esquema **pandera** por tabela; **erros** falham o teste, **alertas** só registram. Meta: **0 erros**; alertas conhecidos documentados em `docs/qualidade_dados.md`.
- Erros típicos: GUID inválido; data fora da janela; `mes` fora do dia 1; contagem ≠ 179.235; view ≠ `{"treino": 20011, "teste": 7311, "fora_cliente_repetido": 2594}`.
- Alertas típicos: juro > 100% a.a. (**legítimo**, máx. 264%); idade < 18 e renda zero (**marcar, não excluir**; fora da auditoria de equidade); `valor_concedido > valor_solicitado`; prazo < 3; `Current` com `data_default`; `caixa_livre` negativo; zeros no lugar de vazio a partir de 2018; `pagamentos_anteriores` e `quitacoes_antecipadas_valor` mudam de regime em 2018–2019; gênero 2 (quase só Espanha) → ausente; codificação de gênero suspeita em 2017–2019.

## Pronto quando

`tests/dados/` passa: `test_validacao` (pandera com `_dados_exemplo.py`), `test_moeda` (EEK só para EE antes de 2011), `test_esquema_sql` (tabelas e views esperadas), `test_view_retorno`, `test_relatorio`. Contagens da carga e da view conferem.

## Estado em 06/11/2026

- **[PRONTO]** carga, validação, relatório, EDA, views 01–04, DATA.md sem itens [A CONFIRMAR].
- **[EM ANDAMENTO] (Marcos)** tabela das decisões do analista (ver `regras_negocio/api` e `painel`).
- **[PENDENTE]** atualizar o comentário do `03_view_modelagem.sql` sobre os reestruturados (texto antigo) e a lista de variáveis do DATA.md (o modelo atual tem 21; ver `modelo_risco`).
- **[A CONFIRMAR]** rótulos dos códigos de `escolaridade`, `tipo_moradia` e `tipo_verificacao`: o painel já usa os do dicionário do Bondora (`CODIGOS` em `src/app/componentes.py`); conferir e registrar no glossário.
- **[A DECIDIR]** estender as séries Euribor e BC no banco além de 07/2021 (o modelo já usa a série própria do pacote).
