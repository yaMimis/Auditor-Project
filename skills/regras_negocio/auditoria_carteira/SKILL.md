---
name: auditor-auditoria-carteira
description: Use para o processo em lote do Auditor de Preço Justo — pontuar a carteira, estimar diferença de preço entre grupos de mesmo risco (gênero, idade) com intervalo de confiança, backtest do retorno realizado, ROI e gerar os arquivos que o painel da carteira lê.
---

# Auditoria da carteira (lote)

> Leia antes: `regras_negocio/governanca`, `regras_negocio/juro_justo`, `regras_negocio/contratos_dados` (seção 5). Dono: Samuel (lote, equidade, backtest); Marcos (view de retorno). Consumidor: `regras_negocio/painel`.

## Objetivo

Responder para a carteira inteira: **o preço acompanha o risco?**, **clientes de mesmo risco pagam diferente por gênero ou idade?** e **os contratos "abaixo do justo" deram mais prejuízo?**

## Etapas

1. **Pontuar:** rodar o `prever()` nos contratos de **2016 (teste, encerrados)** e de **2017–2021**, depois de recalibrar a margem com a taxa nominal. Reestruturados com `fora_da_auditoria = true` ficam fora da comparação de preço.
2. **Gravar** `docs/resultados/carteira_auditoria.csv` no formato de `contratos_dados`, seção 5, incluindo, quando possível:
   - `excesso_eur` (só acima do justo): `prazo × (parcela no juro cobrado − parcela no juro_justo_max)`, com i/12;
   - `perda_nao_coberta_eur` (só encerrados): `max(0, −resultado_eur)` da `vw_retorno_realizado`;
   - `rentabilidade_realizada` (só encerrados): `retorno_realizado` da mesma view.
   No painel, "Pago a mais" soma `excesso_eur` dos acima do justo e "Perda não coberta" soma `perda_nao_coberta_eur` dos abaixo do justo; por isso a perda só aparece para contratos com desfecho (2016).
3. **Equidade:** estimar a diferença de juro **entre clientes de mesmo risco** (auditoria de resíduos: `juro cobrado − juro justo`, controlando por risco, país, ano, valor e prazo), com IC 95%:
   - **Gênero:** só 0 × 1 (gênero 2 = ausente), **dentro de cada país**, janela 2013–2016 (codificação suspeita em 2017–2019).
   - **Idade:** 18–25 × 35–44 anos; contratos com idade < 18 ficam fora.
   - **País não é grupo comparado.**
   - Gravar `docs/resultados/equidade.json`.
4. **Backtest:** comparar a rentabilidade realizada **dentro de cada faixa** por situação. Se a auditoria funciona, em cada faixa "abaixo do justo" rende menos e "acima do justo" rende mais.
5. **ROI** em euros na carteira real (base: `vw_retorno_realizado`).

## Regras

- Resultado de equidade é **indício**, nunca conclusão; apresentar com as ressalvas (`governanca`, limitações): proxies, controle por renda pode mascarar efeito de gênero, qualidade do dado de gênero.
- A `vw_retorno_realizado` usa colunas pós-concessão **só para medir resultado**; nunca viram variável. `recebido_total = principal_pago + juros_multas_pagos` (as recuperações já estão dentro; somar de novo conta duas vezes).
- O painel **não calcula** nada disso: só lê e resume os arquivos.

## Segmentação (apoio à descrição)

K-Means de perfis (`regras_negocio/modelo_risco`), só para descrever a carteira na EDA e nos slides.

## Pronto quando

- Os dois arquivos existem em `docs/resultados/`, passam nas colunas obrigatórias e são servidos pela API ao painel (`tests/api/test_portfolio.py` cobre a leitura e o resumo; `test_portfolio_routes.py`, as rotas).
- O backtest e as diferenças de equidade estão registrados no `DECISOES.md` com as ressalvas.

## Estado em 06/11/2026

- **[PRONTO]** `vw_retorno_realizado` e `test_view_retorno` (Marcos); leitura, filtros, resumo, lista e backtest servidos pela API (`src/api/portfolio.py`, rotas `/portfolio/overview` e `/contracts`).
- **[EM ANDAMENTO] (Samuel)** `carteira_auditoria.csv` até **08/11** (formato aprovado em 06/11); `equidade.json` e backtest até **09/11**.
- **[A DECIDIR]** conferir a distribuição acima/dentro/abaixo com a margem de 2016 aplicada à carteira de 2017–2021 (ver `juro_justo`).
