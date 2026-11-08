# DECISOES.md — Modelo de risco e juro justo

**Responsável:** Samuel · **Atualizado:** 05/11/2026

Registro das decisões da frente de modelos e do motivo de cada uma.

---

## 1. Alvo

- `default = 1` se `data_default` estiver preenchida; senão `0`.

## 2. Contratos usados

- **Coortes maduras:** 2009–2016, só contratos encerrados (`status = 'Repaid'` ou `default = 1`).
- **Total:** 29.916 contratos.
- **Fora da base:** Eslováquia (294 contratos, quase todos de 2014: insuficiente).
- **Reestruturados ficam no modelo** (7.941 contratos, default de 76%). Tirá-los seria escolher os dados por algo que aconteceu depois da concessão, e o modelo subestimaria o risco. Eles saem **só da auditoria de preço**, porque o juro mudou no meio do contrato (marca `fora_da_auditoria`).
- **Sem rebalanceamento**, porque os defaults já são maioria.

## 3. Colunas proibidas como variável

| Grupo                          | Origem                                         | Colunas                                                                                                                                              |
| ------------------------------ | ---------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Lista negra                    | `COLUNAS_LISTA_NEGRA` (`carga_bondora.py`) | pós-concessão, juro, `parcela_mensal`, saídas do modelo do Bondora                                                                              |
| Só auditoria                  | `COLUNAS_SO_AUDITORIA`                       | `genero`, `idade`, `estado_civil`, `n_dependentes`                                                                                           |
| Indisponíveis depois de ~2017 | `COLUNAS_INDISPONIVEIS_RECENTES`             | `situacao_emprego`, `finalidade`, `experiencia_trabalho`, `area_ocupacao`, `divida_renda`, `caixa_livre`, `renda_empregador_principal` |
| Identificadores                | `variaveis.py`                               | `loan_id`, `numero`, `cliente_id`                                                                                                              |

As três últimas indisponíveis vêm com zero no lugar de vazio a partir de 2018 (`DATA.md`, seção 7).

Garantido por teste automático (`tests/modelos/test_seguranca.py`).

## 4. Divisão treino / teste

| Conjunto             | Período                     | Contratos                                | Default |
| -------------------- | ---------------------------- | ---------------------------------------- | ------- |
| Treino e validação | 2009–2015                   | 20.011                                   | 52,4%   |
| Teste                | 2016, sem clientes do treino | 7.311 (EE 3.642 · ES 2.226 · FI 1.443) | 67,1%   |

- Validação cruzada por `GroupKFold` com `cliente_id` (5 partes).
- 1.874 clientes de 2016 que já estavam no treino foram tirados do teste.
- **Escolha de variáveis e parâmetros: só com validação temporal dentro do treino** (ajuste até 2014, validação em 2015, clientes novos). O teste de 2016 não é usado para ajustar nada.

## 5. Variáveis do modelo (21 variáveis desde 05/11; v3 tinha 23)

| Grupo                    | Variáveis                                                                                                                                  |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Pedido                   | `valor_concedido`, `prazo_meses`, `pais`                                                                                              |
| Renda e dívidas         | `renda_total`, `parcela_neutra_sobre_renda`, `valor_sobre_renda`, `divida_sobre_renda`, `renda_relativa`, `passivos_existentes` |
| Perfil                   | `novo_cliente`, `tempo_emprego_atual`, `escolaridade`, `tipo_moradia`, `tipo_verificacao`                                         |
| Histórico na plataforma | `n_emprestimos_anteriores`, `valor_emprestimos_anteriores`, `quitacoes_antecipadas_qtd`                                               |
| Scores de bureau         | `score_ee_mini`, `score_fi_asiakastieto`, `score_es_equifax`, `score_es_microl` (fora do próprio país: "sem_info")                |

- **Parcela neutra:** valor ÷ prazo, **sem o juro** (o juro é vazamento).
- **Renda zero** vira vazio, nunca infinito.
- **Renda relativa:** mediana por país e ano calculada só no treino.
- **Testadas e descartadas** (validação em 2015): `fracao_concedida` (piorava o AUC e reflete decisão do Bondora); orçamento (`caixa_livre_sobre_renda`, `divida_renda_bondora`, `refinanciamento_passivos`) e composição da renda (`renda_assistencial_sobre_renda`, `renda_pensao_sobre_renda`), que não melhoravam.
- **Retiradas em 05/11:** `pagamentos_anteriores` e `quitacoes_antecipadas_valor`. Mudam de regime em 2018–2019 (zeros de ~89% para 0%), justamente na carteira de 2017–2021 que será pontuada. O teste de 2016 não mostra o problema; sem elas, o AUC do teste cai pouco (0,727 → 0,721), e o modelo fica mais estável onde será usado.
- **Moeda:** renda e passivos da Estônia até 2010 vêm em coroas; o `ler_base()` converte para euros com `src/dados/moeda.py`, como a carga do banco (05/11).

## 6. Modelo

- **Baseline:** regressão logística (`treino.py`), com log nas variáveis assimétricas, padronização e one-hot.
- **Principal (03/11):** XGBoost regularizado + early stopping.
- **Calibração** no final (isotônica ou sigmoide), ajustada sem usar 2016.
- **Comparação** com a `pd_bondora`: **só o AUC**. A PD do Bondora usa outro horizonte/definição (prevê 34% de default contra 67% real), então Brier e default previsto não são comparáveis.

## 7. Métricas

- **Ordenação:** AUC e KS.
- **Preço (prioridade):** Brier e curva de calibração.
- Sempre também **por país**.

## 8. Juro justo

- **Método:** fluxo de caixa (PD convertida em taxa mensal, amortização, desconto).
- **Custo do dinheiro:** Euribor do mês de concessão, com piso em zero.
- **LGD:** realizada por país, com defaults de 2014–2015 (cobrança madura, mesma época do treino):
  EE 0,34 · ES 0,76 · FI 0,55 (notebook 07). Outros países: 0,60.
  Defaults de 2016–2017 ainda em cobrança em 2021 (LGD subindo na EE e na FI);
  2009–2013 é outra época da plataforma. A do Bondora (0,75) é estimativa prévia, mais conservadora.
- **Horizonte mínimo de 12 meses** para converter a PD em risco mensal
  (o default pode ocorrer depois do fim do contrato).
- **Custos e margem:** calibrados para a média do juro justo igualar a média do juro cobrado.
- **Sensibilidade:** margem ±1 pp e LGD ±10 pp.
- `juro_aa` vem em porcentagem: dividir por 100.
- **Convenção da taxa (05/11):** o juro do Bondora é **nominal** (taxa mensal = juro ÷ 12; conferido na parcela). O juro justo usa a mesma convenção, para comparar na mesma base. Para comparar com o BC (efetiva): (1 + i/12)^12 − 1.
- Reestruturados ficam fora da comparação de preço.
- Taxas: CSVs do Marcos em data/raw/ (Euribor 3m e 12m do BCE; Selic SGS 4189).
  Em % ao ano → dividir por 100. A série guardada no pacote vai de 01/1994 a 09/2026.
- **Contratos novos (API):** sem data, usa a data de hoje; mês além da série usa o último disponível; ano além do treino usa o último ano do país na renda relativa e a última safra na margem.
- Custo do dinheiro: Euribor 12 meses (a mais próxima do prazo dos contratos);
  3 meses só na sensibilidade. Piso em zero (mínimo −0,08% em 2016).
- Euribor média de 0,9% contra juros de 20–30%: o custo do dinheiro pesa pouco;
  o juro justo depende sobretudo da perda esperada e de custos e margem.

### 8.1 Custos + margem por safra (recalibrada em 05/11)

- Custos + margem calibrados por safra (média do justo = média do cobrado, sem default real), com taxa nominal (i/12) e o modelo de 05/11: 2009 13,5% · 2010 19,7% · 2011 19,2% · 2012 19,3% · 2013 20,8% · 2014 10,8% · 2015 15,3% · 2016 31,7% (trocada em 08/11, abaixo). Ano sem safra usa 2016.
- A margem de 2016 é alta porque absorve a subestimação do default nesse ano (previsto 55% × real 67%).
- **08/11: 2016–2021 calibradas pela MEDIANA** (`calibrar_margem_mediana` em `src/modelos/carteira.py`; valores em `docs/resultados/margem_por_safra.json`, que o `prever()` lê). Em cada safra, metade dos contratos fica acima do justo e metade abaixo: o juro justo passa a ser **relativo à safra** ("dentro da safra, quem paga mais do que o risco justifica?"). Usa só o juro cobrado, nunca o desfecho, então vale para 2017–2021.
  - Por quê: o modelo erra o **nível** de risco de 2016 (previsto 55% × real 67%), e qualquer margem fixa empurrava a carteira toda para um lado. Com 31,7% (média): 65% de 2016 "abaixo do justo", mas as faixas A e B "abaixo" deram lucro (+5,7% e +2,5%). Com 15,6% (média 2013–2015): 60% "acima do justo", numa safra que deu prejuízo nas faixas C a E.
- **Limitação (backtest 2016, 08/11):** dentro da faixa, "acima do justo" **não** rendeu mais que "abaixo" (E: −54% × −29%). Quando o Bondora cobra mais que o nosso justo, em geral o cliente era mesmo mais arriscado: o rating dele vê risco que o modelo não vê. Por isso "acima do justo" é indício para revisão, nunca conclusão.
- LGD por país (defaults 2014–2015): EE 0,34 · ES 0,76 · FI 0,55.
- Pendente: **08/11: margem de incerteza por bootstrap** (20 reamostras por cliente, IC 95%): a dispersão das reamostras em logit, centrada na PD do modelo final; `juro_justo_min`/`max` = juro justo nas pontas do IC da PD. Largura na carteira: mediana 5,2 p.p. (p10 2,8; p90 17,6), contra 4,0 p.p. fixos antes. “Dentro da margem”: 11–18% por ano. Limite: só mede a incerteza da PD, não a da LGD nem a da margem.

## 9. Regra de achado

| Situação           | Quando                                                            |
| -------------------- | ----------------------------------------------------------------- |
| `dentro_da_margem` | Diferença menor que a incerteza do modelo (IC 95% por bootstrap) |
| `acima_do_justo`   | Juro cobrado acima da margem do juro justo                        |
| `abaixo_do_justo`  | Juro cobrado abaixo da margem do juro justo                       |
| `revisao_manual`   | Dados fora da faixa de treino                                     |

## 10. Formato do `prever()`

- Segue o `FORMATO_JSON.md` da Maria (v1.1 aprovada em 30/10; v1.2 proposta em 31/10).
- **Campos:** `contrato_id`, `versao_modelo`, `pd`, `faixa`, `juro_cobrado`, `juro_justo`, `juro_justo_min`, `juro_justo_max`, `situacao_preco`, `motivos[{variavel, rotulo, efeito}]`, `alerta_dados`.
- **Extras (a GenAI ignora):** `pd_ic95`, `diferenca_pp`, e `valor` e `peso` nos motivos.
- **Unidades:** juros e PD sempre em fração (0.249 = 24,9%).
- **Revisão manual:** `alerta_dados = true` ⇔ `situacao_preco = "revisao_manual"`, com os números em `null`.
- **Motivos:** sem `pais`; gênero e idade nunca aparecem, porque não entram no modelo. Rótulos legíveis em `ROTULOS` (`variaveis.py`).
- **Exemplos:** `docs/exemplos_prever.json`.
- **Teste de contrato:** `tests/modelos/test_contrato_prever.py` valida os exemplos com o pydantic da Maria e liga sozinho quando o `prever.py` existir (precisa das funções `prever()` e `casos_de_teste()`).
- Mudança só com aviso ao grupo.

## 11. Segmentação de clientes (K-Means)

- `src/modelos/segmentacao.py`: agrupa clientes por perfil (valor, prazo, renda relativa, dívidas, parcela, histórico).
- **Não entra no modelo de risco.** Serve para descrever a carteira e mostrar risco e preço por perfil (EDA e slides).
- Sem juro, default, gênero, idade ou país nas variáveis do agrupamento; ajustado no treino.
- Fica para depois do `prever()` (semana 3).

## 12. Resultados

### Baseline: regressão logística

| Versão                     | Variáveis | AUC validação cruzada | AUC teste 2016 | Brier teste | Default previsto × real (teste) |
| --------------------------- | ---------- | ----------------------- | -------------- | ----------- | -------------------------------- |
| v1                          | 16         | 0,758                   | 0,704          | 0,194       | 66,5% x 67,1%                    |
| v2                          | 29         | 0,772                   | 0,716          | 0,2015      | 57,4% x 67,1%                    |
| v3                          | 23         | 0,770                   | 0,716          | 0,192       | 62,5% x 67,1%                   |
| PD do Bondora (mesmo teste) | —         | —                      | 0,670          | —          | não comparável                 |

**AUC dentro de cada país (teste):**

| Versão | Estônia | Espanha | Finlândia |
| ------- | -------- | ------- | ---------- |
| v1      | 0,667    | 0,611   | 0,556      |
| v2      | 0,702    | 0,625   | 0,567      |
| v3      | 0,705    | 0,623   | 0,562      |

**Leituras:**

- Parte do AUC geral vem da diferença entre países; o desafio é ordenar **dentro** de cada país (a Finlândia é a mais fraca).
- Na v2, a calibração piorou só em 2016 (em 2015 continuou boa): algumas variáveis mudaram de comportamento em 2016 (`fracao_concedida`, `divida_renda_bondora`, `refinanciamento_passivos`, `score_es_microl`).
- v3 é o baseline oficial: mesmo AUC da v2 com menos variáveis e o melhor Brier.
- Em 2016 subestima o risco nas faixas do meio (50–68% previsto × 58–75% real);
  em 2015 a calibração é boa → mudança de 2016, tratada na calibração do XGBoost
  (ajustada em 2015, sem usar 2016).
- XGBoost v2 (árvores 2009–2015, calibração Platt fora da amostra): modelo principal.
  Teste: AUC 0,727 (EE 0,709 · ES 0,647 · FI 0,572), Brier 0,199, previsto 56,6% × real 67,1%.
- Desvio de nível em 2016 (safra mais arriscada que o treino): tratado no juro justo,
  calibrando custos e margem por safra.
- **05/11, retreino do XGBoost:**

  | Versão                                         | AUC validação 2015 | AUC teste       | EE · ES · FI          | KS    | Brier | Previsto × real |
  | ----------------------------------------------- | -------------------- | --------------- | ----------------------- | ----- | ----- | ---------------- |
  | Coroas corrigidas, com as 2 variáveis          | 0,722                | 0,727           | 0,710 · 0,643 · 0,573 | 0,341 | 0,200 | 55,9% × 67,1%   |
  | **Coroas corrigidas, sem as 2 (oficial)** | 0,716                | **0,721** | 0,700 · 0,638 · 0,564 | 0,330 | 0,204 | 55,2% × 67,1%   |
  | PD do Bondora (mesmo teste)                     | —                   | 0,670           | —                      | 0,249 | —    | não comparável |


  - A correção das coroas não mudou o resultado (os contratos afetados são de 2009–2010 e pesam pouco nas árvores).
  - A retirada das 2 variáveis custa 0,006 de AUC, de forma consistente na validação e no teste. O modelo continua 0,05 acima da PD do Bondora.
  - O modelo subestima o default do teste em todas as faixas (55% × 67%): o juro justo tende a sair baixo. A calibração da margem por safra compensa em parte; registrar como limitação.

### Escolha das variáveis v3 (validação em 2015, 5.943 contratos, default real 66,6%)

| Cenário                    | AUC             | Brier           | Default previsto |
| --------------------------- | --------------- | --------------- | ---------------- |
| v1 (sem as novas)           | 0,700           | 0,197           | 68,0%            |
| v2 completo                 | 0,714           | 0,193           | 67,4%            |
| v2 sem histórico           | 0,710           | 0,195           | 67,1%            |
| v2 sem `fracao_concedida` | **0,718** | **0,191** | 66,1%            |
| v2 sem orçamento           | 0,714           | 0,192           | 68,0%            |
| v2 sem renda                | 0,714           | 0,193           | 67,5%            |
| v2 sem scores de bureau     | 0,704           | 0,196           | 68,9%            |

### Equidade e backtest (08/11, `python -m src.modelos.equidade`)

Resíduo = juro cobrado − juro justo, controlando por PD, faixa, país × ano, valor e prazo; IC 95% robusto (HC1). Resultado é **indício, nunca conclusão**.

| Comparação                                           | Diferença           | IC 95%          | n                |
| ------------------------------------------------------ | -------------------- | --------------- | ---------------- |
| Gênero: mulher × homem (2013–2016, dentro do país) | −0,53 p.p.          | −0,91 a −0,15 | 7.435 × 10.821  |
| Idade: 18–25 × 35–44 (2013–2021)                   | **+5,45 p.p.** | +5,06 a +5,84   | 13.682 × 31.987 |

- **Gênero:** mulheres pagaram meio ponto a menos que homens de mesmo risco. Pequeno e a favor delas: sem sinal de discriminação contra mulheres. Ressalvas: codificação de gênero suspeita em 2017–2019 (por isso a janela 2013–2016) e gênero 2 (ausente) quase só da Espanha.
- **Idade:** jovens pagaram 5,5 p.p. a mais que clientes de 35–44 com a mesma PD. Duas leituras possíveis: (a) cobrança maior só pela idade; (b) risco que o modelo não vê (o rating do Bondora usa idade; o nosso não, por decisão). Teste "default realizado − PD" por grupo (encerrados 2013–2016): jovens deram **+3,56 p.p.** mais default do que a PD previa (IC +1,42 a +5,70; n 2.596 × 5.325). Parte do prêmio tem base em risco, mas pela conta aproximada (3,6 p.p. × LGD ~0,6 em ~3 anos ≈ 1 p.p. ao ano) a perda extra explica cerca de 1 dos 5,5 p.p. Os ~4 p.p. restantes são  **indício de cobrança pela idade além do risco** , a investigar à luz do CDC. Gênero: mulheres deram **−3,34 p.p.** menos default que o previsto (IC −4,62 a −2,07): a diferença de preço vai na direção do risco, sem indício contra mulheres. Ressalva: o teste de default usa só encerrados 2013–2016.
- **Backtest 2016** (margem pela mediana; rentabilidade realizada média):

| Faixa | Abaixo do justo | Dentro  | Acima do justo |
| ----- | --------------- | ------- | -------------- |
| A     | +6,8%           | +3,4%   | +1,5%          |
| B     | +3,2%           | −1,8%  | +1,2%          |
| C     | −10,0%         | −6,0%  | −1,7%         |
| D     | −25,7%         | −17,0% | −23,2%        |
| E     | −26,2%         | −32,5% | −50,8%        |

  O esperado era abaixo < dentro < acima em cada faixa. Só a faixa C segue o esperado; em A, B e E acontece o contrário. Confirma a limitação da seção 8.1: quando o Bondora cobra mais que o nosso justo, em geral o cliente era mesmo mais arriscado.

## 13. Observações dos dados

- 2009–2012: só Estônia. Espanha e Finlândia entram em 2013–2014.
- Default por país: Estônia 42%, Espanha 78%, Finlândia 73%.
- O salto de inadimplência a partir de 2014 vem em boa parte da entrada de Espanha e Finlândia.
- O teste é mais arriscado que o treino (só clientes novos e mais Espanha e Finlândia).
- Valores extremos (renda de até 133 mil, empréstimo de €6, prazo de 1 mês) são poucos; a logística usa log e o XGBoost não é afetado.
- Renda e passivos da Estônia até 2010 estavam em coroas (1.822 contratos, 9% do treino; achado do Marcos). Corrigido no treino em 05/11.
- `pagamentos_anteriores` e `quitacoes_antecipadas_valor` mudam de regime em 2018–2019 (`docs/qualidade_dados.md`); retiradas do modelo em 05/11.

## 14. Pendências

- [X] Anos das coortes maduras
- [X] Formato do `prever()` aprovado pela Maria (30/10)
- [X] Marcos: `parcela_mensal` na lista negra, chave obrigatória no hash
- [X] `estado_civil` e `n_dependentes` só para auditoria (decidido no script do Marcos)
- [X] Baseline (adiantado de 01/11 para 31/10)
- [X] Preencher os resultados da v3
- [X] Maria: proposta da v1.2 aceita (acima do justo → `revisar_preco`; `REGRAS_PARECER.md` v1.2)
- [ ] Yasmin: aprovar o formato para as telas
- [X] Marcos: Euribor e taxas do BC até 01/11; view das coortes
- [X] 03/11: XGBoost + calibração + SHAP
- [X] **04/11: entregar o `prever()`**
- [X] 05/11: correção das coroas, retirada das 2 variáveis com mudança de regime, taxa nominal, contratos novos
- [X] Recalibrar a margem por safra com a taxa nominal e o modelo de 05/11 (notebook 08) e regenerar os casos de teste (notebook 09)
- [X] Margem de incerteza por bootstrap no lugar do ±2 pp fixo (`incerteza.py`)
- [ ] `juro_pares_mediana` (pares = faixa × país × ano, mínimo de 30) como segunda opinião
- [ ] Teste do `prever()` com modelo pequeno treinado no próprio teste, cobrindo as 4 situações
- [X] 08/11: `carteira_auditoria.csv` (`src/modelos/carteira.py`, `python -m src.modelos.carteira`)
- [X] 09/11 (adiantado para 08/11): `equidade.json` e backtest (seção 12)
- [X] Preencher o teste "default realizado − PD" da idade (seção 12) e decidir a leitura do achado de idade
