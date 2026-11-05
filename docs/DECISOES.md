# DECISOES.md — Modelo de risco e juro justo

**Responsável:** Samuel · **Atualizado:** 31/10/2026

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

| Grupo                          | Origem                                         | Colunas                                                                           |
| ------------------------------ | ---------------------------------------------- | --------------------------------------------------------------------------------- |
| Lista negra                    | `COLUNAS_LISTA_NEGRA` (`carga_bondora.py`) | pós-concessão, juro, `parcela_mensal`, saídas do modelo do Bondora           |
| Só auditoria                  | `COLUNAS_SO_AUDITORIA`                       | `genero`, `idade`, `estado_civil`, `n_dependentes`                        |
| Indisponíveis depois de ~2017 | `COLUNAS_INDISPONIVEIS_RECENTES`             | `situacao_emprego`, `finalidade`, `experiencia_trabalho`, `area_ocupacao` |
| Identificadores                | `variaveis.py`                               | `loan_id`, `numero`, `cliente_id`                                           |

Garantido por teste automático (`tests/modelos/test_seguranca.py`).

## 4. Divisão treino / teste

| Conjunto             | Período                     | Contratos                                | Default |
| -------------------- | ---------------------------- | ---------------------------------------- | ------- |
| Treino e validação | 2009–2015                   | 20.011                                   | 52,4%   |
| Teste                | 2016, sem clientes do treino | 7.311 (EE 3.642 · ES 2.226 · FI 1.443) | 67,1%   |

- Validação cruzada por `GroupKFold` com `cliente_id` (5 partes).
- 1.874 clientes de 2016 que já estavam no treino foram tirados do teste.
- **Escolha de variáveis e parâmetros: só com validação temporal dentro do treino** (ajuste até 2014, validação em 2015, clientes novos). O teste de 2016 não é usado para ajustar nada.

## 5. Variáveis do modelo (v3: 23 variáveis)

| Grupo                    | Variáveis                                                                                                                                                |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Pedido                   | `valor_concedido`, `prazo_meses`, `pais`                                                                                                            |
| Renda e dívidas         | `renda_total`, `parcela_neutra_sobre_renda`, `valor_sobre_renda`, `divida_sobre_renda`, `renda_relativa`, `passivos_existentes`               |
| Perfil                   | `novo_cliente`, `tempo_emprego_atual`, `escolaridade`, `tipo_moradia`, `tipo_verificacao`                                                       |
| Histórico na plataforma | `n_emprestimos_anteriores`, `valor_emprestimos_anteriores`, `pagamentos_anteriores`, `quitacoes_antecipadas_qtd`, `quitacoes_antecipadas_valor` |
| Scores de bureau         | `score_ee_mini`, `score_fi_asiakastieto`, `score_es_equifax`, `score_es_microl` (fora do próprio país: "sem_info")                              |

- **Parcela neutra:** valor ÷ prazo, **sem o juro** (o juro é vazamento).
- **Renda zero** vira vazio, nunca infinito.
- **Renda relativa:** mediana por país e ano calculada só no treino.
- **Testadas e descartadas** (validação em 2015): `fracao_concedida` (piorava o AUC e reflete decisão do Bondora); orçamento (`caixa_livre_sobre_renda`, `divida_renda_bondora`, `refinanciamento_passivos`) e composição da renda (`renda_assistencial_sobre_renda`, `renda_pensao_sobre_renda`), que não melhoravam.

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
  EE ~0,34 · ES ~0,76 · FI ~0,55 (troque pelos valores do notebook 07).
  Defaults de 2016–2017 ainda em cobrança em 2021 (LGD subindo na EE e na FI);
  2009–2013 é outra época da plataforma. A do Bondora (0,75) é estimativa prévia, mais conservadora.
- **Horizonte mínimo de 12 meses** para converter a PD em risco mensal
  (o default pode ocorrer depois do fim do contrato).
- **Custos e margem:** calibrados para a média do juro justo igualar a média do juro cobrado.
- **Sensibilidade:** margem ±1 pp e LGD ±10 pp.
- `juro_aa` vem em porcentagem: dividir por 100.
- Reestruturados ficam fora da comparação de preço.
- Taxas: CSVs do Marcos em data/raw/ (Euribor 3m e 12m do BCE; Selic SGS 4189).
  Completas de 2009 a 2016 (96 meses), em % ao ano → dividir por 100.
- Custo do dinheiro: Euribor 12 meses (a mais próxima do prazo dos contratos);
  3 meses só na sensibilidade. Piso em zero (mínimo −0,08% em 2016).
- Euribor média de 0,9% contra juros de 20–30%: o custo do dinheiro pesa pouco;
  o juro justo depende sobretudo da perda esperada e de custos e margem.

### 8.1 Custos + margem por safra (03/11)

- Custos + margem calibrados por safra (média do justo = média do cobrado, sem default real): 2009 8,7% · 2010 14,3% · 2011 15,8% · 2012 16,8% · 2013 17,4% · 2014 5,0% · 2015 9,0% · 2016 20,5%. Ano sem safra usa 2016.
- LGD por país (defaults 2014–2015): EE 0,34 · ES 0,76 · FI 0,55.
- Distribuição com ±2pp: acima 34–67%, abaixo 28–55%, dentro 4–27% por safra.
- Pendente: avaliar calibração pela mediana junto com o bootstrap.

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

## 13. Observações dos dados

- 2009–2012: só Estônia. Espanha e Finlândia entram em 2013–2014.
- Default por país: Estônia 42%, Espanha 78%, Finlândia 73%.
- O salto de inadimplência a partir de 2014 vem em boa parte da entrada de Espanha e Finlândia.
- O teste é mais arriscado que o treino (só clientes novos e mais Espanha e Finlândia).
- Valores extremos (renda de até 133 mil, empréstimo de €6, prazo de 1 mês) são poucos; a logística usa log e o XGBoost não é afetado.

## 14. Pendências

- [X] Anos das coortes maduras
- [X] Formato do `prever()` aprovado pela Maria (30/10)
- [X] Marcos: `parcela_mensal` na lista negra, chave obrigatória no hash
- [X] `estado_civil` e `n_dependentes` só para auditoria (decidido no script do Marcos)
- [X] Baseline (adiantado de 01/11 para 31/10)
- [ ] Preencher os resultados da v3
- [ ] Maria: responder a proposta da v1.2 (acima do justo → `revisar_preco`)
- [ ] Yasmin: aprovar o formato para as telas
- [ ] Marcos: Euribor e taxas do BC até 01/11; view das coortes
- [ ] 03/11: XGBoost + calibração + SHAP
- [ ] **04/11: entregar o `prever()`**
