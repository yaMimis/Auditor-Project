---
name: auditor-modelo-risco
description: Use para construir, treinar, avaliar ou alterar o modelo de risco de inadimplência (PD) do Auditor de Preço Justo — variáveis, regras antivazamento, baseline logística, XGBoost calibrado, métricas por país, faixas A–E, revisão manual e motivos SHAP.
---
# Modelo de risco (PD)

> Leia antes: `regras_negocio/governanca`, `regras_negocio/dados`. Depois: `regras_negocio/juro_justo`. Dono: Samuel (Modelo e juro justo). Documento do dono: `docs/DECISOES.md`.

## Objetivo

Estimar, para cada contrato, a **probabilidade de inadimplência (PD)** calibrada, a **faixa de risco** e os **motivos** legíveis, sem usar o preço nem atributos sensíveis.

## Arquivos

`src/modelos/dados.py` (`ler_base`, `preparar`, `dividir`), `variaveis.py`, `treino.py`, `xgb.py`, `prever.py`, `incerteza.py`, `segmentacao.py`; notebooks `notebooks/modelos/01_coortes … 06_xgboost`; métricas em `docs/resultados/`; testes `tests/modelos/`.

## Regras antivazamento

1. `PROIBIDAS = LISTA_NEGRA | SO_AUDITORIA | INDISPONIVEIS | IDENTIFICADORES` nunca entram no modelo.
2. `juro_aa` e `parcela_mensal` fora (seria auditoria circular).
3. Divisão **por tempo e por cliente** (`regras_negocio/dados`). Validação no treino: `GroupKFold(5)` por `cliente_id`.
4. **Escolha de variáveis e hiperparâmetros só com validação temporal** (ajuste até 2014, validação em 2015). **O teste de 2016 não ajusta nada.**
5. `ler_base()` lê o CSV com os **mesmos nomes e tipos do banco** (reaproveita o mapeamento da carga) e converte coroas para euro. Constantes: `ANOS_TREINO = range(2009, 2016)`, `ANO_TESTE = 2016`, `PAISES_FORA = {"SK"}`, `SEMENTE = 42`, `N_FOLDS = 5`.

## Variáveis (21, desde 05/11/2026)

| Grupo                    | Variáveis                                                                                                                                                  |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Pedido                   | `valor_concedido`, `prazo_meses`, `pais`                                                                                                              |
| Renda e dívidas         | `renda_total`, `parcela_neutra_sobre_renda`, `valor_sobre_renda`, `divida_sobre_renda`, `renda_relativa`, `passivos_existentes`                 |
| Perfil                   | `novo_cliente`, `tempo_emprego_atual`, `escolaridade`, `tipo_moradia`, `tipo_verificacao`                                                         |
| Histórico na plataforma | `n_emprestimos_anteriores`, `valor_emprestimos_anteriores`, `quitacoes_antecipadas_qtd`                                                               |
| Scores de bureau         | `score_ee_mini` (numérica); `score_fi_asiakastieto`, `score_es_equifax`, `score_es_microl` (categóricas; fora do próprio país = `"sem_info"`) |

Regras de construção:

- **Parcela neutra** = `valor_concedido / prazo_meses / renda_total` (**sem o juro**).
- `divida_sobre_renda` = `passivos_total / renda_total`. `passivos_existentes` é a **quantidade** de dívidas.
- Divisão segura: renda zero ou vazia → NaN, **nunca infinito**.
- `renda_relativa` = renda ÷ mediana por país e ano **calculada só no treino** (`referencia=treino`). Ano além do treino → último ano do país.
- Categóricas: vazio → `"sem_info"`; < 1% no treino ou desconhecida → `"outros"`.
- `pais` entra no modelo (default EE 42% · ES 78% · FI 73%), mas **não aparece nos motivos**.
- Testadas e descartadas: `fracao_concedida`, `caixa_livre_sobre_renda`, `divida_renda_bondora`, `refinanciamento_passivos`, `renda_assistencial_sobre_renda`, `renda_pensao_sobre_renda`; **retiradas em 05/11** `pagamentos_anteriores` e `quitacoes_antecipadas_valor` (mudam de regime em 2018–2019, justo na carteira a pontuar).
- Dicionário `ROTULOS`: nome legível de cada variável (vai no campo `rotulo` dos motivos).

## Modelos

- **Baseline:** regressão logística com `log1p` nas assimétricas, padronização e one-hot.
- **Principal:** XGBoost regularizado com early stopping (50 rodadas). Fixos: `learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, n_estimators=2000, eval_metric="logloss", random_state=42`. Grade: `max_depth ∈ {3,4,5}`, `min_child_weight ∈ {5,20}`, `reg_lambda ∈ {1,10}`. One-hot com `handle_unknown="ignore", min_frequency=0.01`. Converter `Int64`/`pd.NA` para `float64`/`np.nan` antes do XGBoost.
- **Calibração Platt** (logística sobre o logit) ajustada em 2015, **nunca em 2016**. Classe `ModeloXGB` com `predict_proba` estilo sklearn.
- Comparação com `pd_bondora`: **só AUC** (outro horizonte e definição).

## Métricas (sempre também por país)

| Modelo (teste 2016)                              | AUC                                       | EE · ES · FI          | KS    | Brier            | Previsto × real |
| ------------------------------------------------ | ----------------------------------------- | ----------------------- | ----- | ---------------- | ---------------- |
| **XGBoost oficial (05/11, 21 variáveis)** | **0,721** (validação 2015: 0,716) | 0,700 · 0,638 · 0,564 | 0,330 | 0,204            | 55,2% × 67,1%   |
| XGBoost com as 2 variáveis retiradas            | 0,727                                     | 0,710 · 0,643 · 0,573 | 0,341 | 0,200            | 55,9% × 67,1%   |
| Logística v3                                    | 0,716                                     | —                      | —    | 0,192            | —               |
| PD do Bondora                                    | 0,670                                     | —                      | 0,249 | não comparável | —               |

O modelo **subestima o default de 2016 em todas as faixas**: registrar como limitação. Métricas salvas em `docs/resultados/<nome>_vN.json`: `{"modelo", "data", "params", "teste": {"contratos", "default_real", "default_previsto", "auc", "ks", "brier"}}`.

## Faixas, revisão manual e motivos

- Faixas por PD: `< 0,30 → A`, `< 0,45 → B`, `< 0,60 → C`, `< 0,75 → D`, senão `E`.
- **Revisão manual** quando os dados estão fora da faixa de treino: país não visto, ou `valor_concedido`, `prazo_meses`, `renda_total` vazios ou fora dos quantis 0,5%–99,5% do treino. Aí `pd`, `faixa` e juros justos vêm `null`, `motivos = []`, `alerta_dados = true` (sempre juntos).
- **Motivos:** top 5 fatores SHAP `{variavel, rotulo, efeito ∈ {aumenta_risco, reduz_risco}, valor, peso}`; **nunca** país, gênero ou idade.
- Pacote salvo (`modelos_salvos/pacote_prever_v1.joblib`): modelo, referência do treino (renda relativa e categorias), faixas do treino, países conhecidos, série Euribor 12m e os modelos do bootstrap. **LGD, margem por safra e a convenção i/12 ficam no código do `prever.py`, não no pacote.** O pacote só muda quando o modelo é retreinado ou a Euribor é atualizada; o Samuel avisa o grupo.

## Segmentação (K-Means, descritiva)

`segmentacao.py`: perfis de cliente (valor, prazo, renda relativa, dívidas, parcela, histórico), ajustado no treino, `escolher_k` entre 2 e 8 com amostra de 5.000. **Não entra no modelo**; sem juro, default, gênero, idade ou país. Serve para EDA e slides.

## Pronto quando

- `test_seguranca`: nenhuma coluna proibida; `juro_aa`/`parcela_mensal` fora; sem cliente em treino e teste; teste só 2016; renda zero sem infinito; descartadas fora.
- `test_xgb`: `predict_proba` em [0, 1]; calibração aplicada. `test_treino`, `test_segmentacao` passam.
- `test_contrato_prever`: saídas passam no `EntradaPrever`; revisão manual ⇔ `alerta_dados` com números nulos; motivos sem atributos sensíveis.
- Métricas novas salvas em JSON e registradas no `DECISOES.md` com o motivo.

## Estado em 06/11/2026

- **[PRONTO]** XGBoost oficial de 05/11, `prever()` v2, `casos_de_teste()` (`docs/casos_de_teste.json`, 2 casos reais por situação).
- **[EM ANDAMENTO] (Samuel, próximo PR)** teste do `prever()` real com um modelo pequeno treinado no próprio teste, rodando `casos_de_teste()` e cobrindo as 4 situações (a CI não tem o `.joblib`). No mesmo PR: a tabela do `DECISOES.md` passa a listar as 7 colunas indisponíveis.
- `prever()` v2 no PR #41.
- **[DEFINIDO] (13/11)** nome da versão: `VERSAO = "xgboost_v3"` (retreino de 05/11 + bootstrap de 08/11). Pacote oficial conferido: `pacote_prever_v1.joblib` (depth 3, mcw 5, lambda 1, 161 árvores, 20 reamostras). Métricas em `docs/resultados/xgboost_v3.json`; o `xgboost_v2.json` é o modelo de 01/11 (23 variáveis, AUC 0,727). Regra: nova versão a cada retrein
