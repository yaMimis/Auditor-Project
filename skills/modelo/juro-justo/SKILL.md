---
name: auditor-juro-justo
description: Aplique ao calcular ou alterar o juro justo do Auditor de Preço Justo — fluxo de caixa com brentq, convenção nominal, custo do dinheiro (Euribor), LGD por país, margem por safra, incerteza por bootstrap, mediana dos pares e situação do preço.
---

# Juro justo e situação do preço

Ao criar, alterar ou revisar o cálculo do juro justo (`src/modelos/prever.py`, funções `juro_justo` e `prever`, `src/modelos/incerteza.py`; notebooks `05_taxas`, `07_lgd`, `08_margem`, `09_casos_de_teste`, `10_bootstrap`), siga estas regras. Siga também as skills `auditor-governanca`, `auditor-modelo-risco` e `auditor-contratos-dados`. Dono: Samuel. Não altere sem combinar com ele.

## Contexto

Para cada contrato com PD, calcular **o juro que cobre o custo do dinheiro, a perda esperada e os custos com margem**, com uma **margem de incerteza**, e dizer se o juro cobrado está acima, abaixo ou dentro dela.

## Fórmula — `juro_justo(prazo, pd_total, lgd, custo_anual)`

1. Taxa anual em que o **valor presente esperado dos recebimentos = valor emprestado (1,0)**, resolvida com `scipy.optimize.brentq` em `[1e-6, 5,0]`. Sem raiz → devolve 5,0.
2. Risco mensal: `h = 1 − (1 − PD)^(1 / max(prazo, 12))` (horizonte mínimo de 12 meses: o default pode ocorrer após o fim do contrato).
3. Desconto mensal: `d = (1 + custo_anual)^(1/12) − 1`.
4. **Convenção nominal (05/11):** amortização Price com `i = taxa / 12`, a mesma do juro do Bondora (conferida na parcela). Para comparar com o BC (efetiva): `(1 + i/12)^12 − 1`.
5. Em cada mês: recebe a parcela com probabilidade `(1 − h)` e recupera `(1 − LGD) × saldo` com probabilidade `h`.

## Parâmetros

| Parâmetro | Valor | Origem |
|---|---|---|
| Custo do dinheiro | Euribor 12m do **mês da concessão**, em fração, **piso em zero**; mês além da série → último disponível (`asof`). 3m só na sensibilidade | série do pacote (01/1994–09/2026) |
| LGD por país | EE 0,34 · ES 0,76 · FI 0,55; outros 0,60 | LGD realizada, defaults 2014–2015 (notebook 07) |
| Custos + margem por safra (a.a.) | 2009 13,47% · 2010 19,68% · 2011 19,15% · 2012 19,27% · 2013 20,78% · 2014 10,76% · 2015 15,27% · 2016 31,66%; ano sem safra → 2016 | média do justo = média do cobrado na safra (notebook 08) |
| Margem de incerteza | ±2,0 pp (**provisório**) | será o IC 95% por bootstrap |
| Juro cobrado | `juro_aa` ÷ 100 | banco / API em % |

Custo total no fluxo: `euribor + margem_da_safra`. Sensibilidade documentada: margem ±1 pp e LGD ±10 pp.

## Situação do preço (regra de achado)

| `situacao_preco` | Quando |
|---|---|
| `acima_do_justo` | juro cobrado > `juro_justo_max` |
| `abaixo_do_justo` | juro cobrado < `juro_justo_min` |
| `dentro_da_margem` | entre `juro_justo_min` e `juro_justo_max` (diferença menor que a incerteza) |
| `revisao_manual` | dados fora da faixa de treino (`auditor-modelo-risco`); sem PD nem juro justo |

`juro_justo_min = max(justo − margem, 0)`, `juro_justo_max = justo + margem`, `diferenca_pp = (cobrado − justo) × 100` com 1 casa. Reestruturados (`fora_da_auditoria`) ficam fora da comparação de preço.

## Contratos novos (vindos da API)

- Sem `data_emprestimo` → data de hoje. A API sempre envia a data do formulário.
- Mês além da série → último Euribor disponível.
- Ano além do treino → último ano do país para a renda relativa e a **última safra** (2016) para a margem.

## Ao terminar

Confirme, antes de dar a tarefa por pronta:

- `juro_justo` devolve taxa em fração, cresce com a PD e com a LGD, e devolve 5,0 quando não há raiz.
- As quatro situações aparecem em `docs/casos_de_teste.json` e passam no `EntradaPrever`.
- Toda mudança de parâmetro registrada no `DECISOES.md` (seção 8) com o motivo, e os casos de teste regenerados (notebook 09).

## Situação atual (11/11/2026)

Não refaça o que está **[PRONTO]**; não altere o que está **[EM ANDAMENTO]** por outra pessoa; em **[A DECIDIR]** ou **[A CONFIRMAR]**, use a escolha padrão e avise.

- **[PRONTO]** convenção nominal, LGD por país, margem por safra, contratos sem data.
- **[PRONTO]** margem de incerteza por **bootstrap por cliente** (`incerteza.py`: 20 reamostras, IC 95% da PD e do juro justo) no lugar do ±2 pp; preencher `pd_ic95`.
- **[PRONTO]** `juro_pares_mediana` (`docs/resultados/pares_mediana.csv`): mediana do juro cobrado **no treino** dos pares (mesma faixa A–E × país × ano, mínimo de 30 contratos por grupo); ano mais novo que o treino → último disponível; em fração; `null` sem grupo. É **segunda opinião**: não muda a `situacao_preco`.
- **[A DECIDIR]** a margem de 2016 (31,66%) é alta porque absorve a subestimação do default nesse ano. Aplicá-la a 2017–2021 e aos contratos novos pode empurrar quase toda a carteira para "abaixo do justo". Padrão até a decisão: manter e declarar como limitação; conferir a distribuição acima/dentro/abaixo da carteira antes da demo.
