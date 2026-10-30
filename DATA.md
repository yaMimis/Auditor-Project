# DATA.md · Regras dos dados · Auditor de Preço Justo

> Versão 0.2 (rascunho) · 28/10/2026 · Responsável: Marcos (Dados e processo) · Revisão: Samuel (Modelo e juro justo)
> Itens marcados **[A CONFIRMAR]** dependem de decisão do Samuel. As regras das seções 3, 4 e 5 (alvo, coorte madura e divisão) são propostas ainda sem confirmação explícita dele. As colunas citadas usam os nomes do banco (`01_schema_bondora.sql`).

## 1. Fonte e versão

- Bondora LoanData: 179.235 contratos, 112 colunas, concessões de 2009 a 2021, data de corte 20/07/2021 (`ReportAsOfEOD`).
- Arquivo: `data/raw/LoanData_Bondora.csv`. SHA-256 (impressão digital do arquivo):`<4728fc5ecf6d1f42246d97780a827d43b133dfa09b9f2f363ad91eee588663b5>`. Conferir com `Get-FileHash data\raw\LoanData_Bondora.csv -Algorithm SHA256`.
- Dicionário de dados: Public Reports do Bondora, consultado em `<28/10/2026>`.
- O CSV nunca entra no Git.

## 2. Unidade de análise

Uma linha por contrato, nas três tabelas ligadas por `loan_id`: `emprestimo`, `cliente` e `historico_credito`. O mesmo cliente tem vários contratos (85.087 clientes; 36.185 deles com mais de um) e é identificado por `cliente_id`.

## 3. Alvo (o que é inadimplente)

`inadimplente = 1` quando `data_default` está preenchida; não se usa `status`. O Bondora registra essa data quando o atraso passa de 60 dias (segundo o dicionário; anotar a data da consulta).

Há 7.031 contratos maduros com status `Repaid` e data de default, ou seja, atrasaram e depois quitaram. Contam como inadimplentes; a recuperação entra na LGD (Loss Given Default, perda dado o default).

A PD (Probability of Default) é a de "default em qualquer momento do contrato" **[A CONFIRMAR]**.

## 4. Recorte (coorte madura)

Entra o contrato com `data_vencimento_original` até 20/07/2021 e `status` diferente de `Current`.

- Contratos com vencimento original até a data de corte: 49.869 (51,7% de default).
- Saem os 2.791 que seguem `Current` depois do vencimento original (provavelmente reagendados; o desfecho é desconhecido). Sobram **47.078 contratos, com 54,7% de default**.
- Cuidado com a composição por ano: os contratos maduros de 2019 e 2020 são só os curtos, e o default deles é 13,8% e 6,3%, contra cerca de 58% em 2015–2017. Não comparar essas épocas diretamente.

## 5. Divisão treino e teste

Por tempo (`data_emprestimo`) e por cliente:

| Conjunto | Concessões                                 | Contratos                          | Default |
| -------- | ------------------------------------------- | ---------------------------------- | ------- |
| Treino   | 2013 a 2016                                 | 26.269 (19.030 clientes)           | 57,5%   |
| Teste    | 2017 e 2018                                 | 10.805 (após a regra por cliente) | 64,6%   |
| Fora     | 2009–2012 (2.729) e 2019 em diante (2.076) | n/a                                | n/a     |

- Fora: 2009–2012 tem poucos contratos e é de outra época; de 2019 em diante só restam contratos curtos.
- Regra por cliente: se o `cliente_id` aparece no treino, seus contratos saem do teste. São 2.660 clientes e 5.199 contratos (32,5% do teste bruto de 16.004).
- Limitação conhecida: o preço mudou entre 2017 e 2018 (juro médio de 53,7% para 28,2% ao ano nos contratos maduros).

## 6. Colunas

**Lista negra (26): nunca entram como variável do modelo.** São pós-concessão ou saídas do próprio Bondora. Ficam no banco para montar o alvo, o preço cobrado, a comparação com a PD do Bondora e o backtest.

`juro_aa`, `parcela_mensal`, `rating`, `versao_modelo_bondora`, `pd_bondora`, `perda_esperada_bondora`, `lgd_bondora`, `retorno_esperado_bondora`, `status`, `data_default`, `dias_atraso`, `pior_categoria_atraso`, `reestruturado`, `data_vencimento_atual`, `data_fim_contrato`, `data_ultimo_pagamento`, `principal_pago`, `juros_multas_pagos`, `principal_baixado`, `juros_baixados`, `saldo_principal`, `recuperacao_principal`, `recuperacao_juros`, `ead1`, `ead2`, `estagio_recuperacao`

- `juro_aa` é o preço que estamos auditando; usá-lo para prever o risco tornaria a auditoria circular.
- `parcela_mensal` está na lista negra porque, dados o valor e o prazo, ela embute o juro (correlação de 0,90 com a parcela calculada a partir do juro).

**Só auditoria (4): usadas apenas na auditoria de equidade, nunca para prever risco.**

`genero`, `idade`, `estado_civil`, `n_dependentes`

- `estado_civil` e `n_dependentes` só têm dados nos contratos até 2017, então a auditoria delas cobre só esse período.

**Indisponíveis após 2017 (4): fora do modelo.** Cerca de 81% em branco no teste, contra quase 0% no treino. Um modelo treinado com elas perderia a informação justamente onde será usado.

`finalidade`, `situacao_emprego`, `area_ocupacao`, `experiencia_trabalho`

**Identificadores e datas: servem para dividir e agrupar, não como variável.** O ano da concessão também não entra; o efeito de época vem da Euribor.

`loan_id`, `cliente_id`, `numero`, `data_referencia`, `data_pedido`, `data_emprestimo`, `data_primeira_parcela`, `data_vencimento_original`

**Candidatas a variáveis do modelo [A CONFIRMAR]:**

- Contrato: `novo_cliente`, `valor_solicitado`, `valor_concedido`, `prazo_meses`, `tipo_verificacao`
- Cliente: `pais`, `escolaridade`, `tipo_moradia`, `tempo_emprego_atual`, as oito colunas `renda_*`
- Histórico: `n_emprestimos_anteriores`, `valor_emprestimos_anteriores`, `pagamentos_anteriores` (14% em branco no teste), `quitacoes_antecipadas_valor`, `quitacoes_antecipadas_qtd`, `passivos_existentes`, `passivos_total`, `refinanciamento_passivos`, `divida_renda`, `caixa_livre`
- Scores externos (`score_es_microl`, `score_es_equifax`, `score_fi_asiakastieto`, `score_ee_mini`): a cobertura muda muito entre treino e teste (`score_es_microl` tem 77% em branco no treino e 16% no teste) e varia por país. Sugestão: fora do modelo base, testar depois como sensibilidade.
- `pais` entra no modelo. O default é 38% na Estônia, 72% na Finlândia e 76% na Espanha; sem o país, a auditoria de preço marcaria como discriminação o que é diferença de risco.
- A variável derivada parcela ÷ renda deve usar `valor_concedido / prazo_meses / renda_total` (parcela sem juros), porque `parcela_mensal` está na lista negra.

## 7. Valores especiais e qualidade

- `-1` nas colunas de código significa "sem informação" e vira NULL. O valor `0` é mantido; confirmar no dicionário o que ele significa em cada coluna.
- Datas anteriores a 2000 (como `0001-01-01`) viram NULL. `n_dependentes` "10Plus" vira 10.
- **Juros acima de 100% ao ano são legítimos** (Espanha 2.738 contratos, Finlândia 143, em 2016–2018; máximo de 264%). Não remover.
- Idade menor que 18 (53 contratos, 48 deles com idade 0) e renda zero (64 contratos): regras de validação no pandera. Marcar ou excluir **[A CONFIRMAR]**.
- Gênero 2 ("indefinido") é quase só da Espanha (12.164 de 12.180; cerca de 46% dos contratos espanhóis). Na auditoria, tratar como dado ausente e comparar só 0 e 1, de preferência dentro de cada país.
- `score_es_microl` tem o valor "M" em cerca de 136 mil linhas; confirmar o significado no dicionário.

## 8. Moeda e unidades

Valores em euro. Juros em % ao ano, como vêm do Bondora.

## 9. Fontes externas

- **Euribor (Portal de dados do BCE, data.ecb.europa.eu)** **[A CONFIRMAR com o Samuel]**:
  - Principal: Euribor de 12 meses, série mensal, média das observações do mês (`FM.M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA`).
  - Sensibilidade: Euribor de 3 meses, mesma frequência (`FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA`).
  - Período: 01/2009 a 07/2021 (concessões de 28/02/2009 a 19/07/2021). Baixar a série completa e recortar depois.
  - Junção: mês de `data_emprestimo` com o mês da série. Os valores negativos (de 2015–2016 em diante) ficam como vêm; o piso em zero, se houver, é decisão do Samuel na fórmula do preço.
  - Limitação: a Euribor tem no máximo 12 meses, e a mediana do prazo dos contratos é de 60 meses (36 a 48 meses nos contratos maduros).
- **Selic (Banco Central do Brasil)** **[A CONFIRMAR com o Samuel]**: Pepreçar os contratos históricos com a Selic do mesmo mês.
  - Série SGS 4189, "Selic acumulada no mês anualizada base 252": mensal, em % ao ano, 01/2009 a 07/2021.
  - Descartadas: a 4390 (% ao mês; exige anualizar e erra em meses curtos) e a meta Selic do Dados de Mercado (valor do 1º dia do mês; defasa quando a meta muda). A meta fica só como conferência da 4189.
  - Limitação: a Selic é uma taxa de um dia útil, e a Euribor principal é de 12 meses. A comparação mais justa em prazo é com a Euribor de 3 meses.
- **Tabelas no banco:** `euribor_mensal` (`mes`, `euribor_3m`, `euribor_12m`), `selic_mensal` (`mes`, `selic_aa` e `selic_meta_aa`, esta só para conferência) e a view `vw_custo_do_dinheiro`, que liga cada contrato ao mês da concessão. Esquema em `02_schema_macro.sql`; carga em `carga_macro.py`.
- **Taxas de crédito do BC:** o arquivo `historicotaxajurosdiario_BaCen.csv` é o ranking do período de 05/10/2026 a 09/10/2026: uma taxa por instituição, 78 instituições, só crédito pessoal não consignado prefixado para pessoa física. Há uma taxa zerada para limpar. É uma referência de mercado atual; **não** cobre o período dos dados do Bondora (2009–2021), então não serve para calibrar o preço dele.

## 10. Privacidade e LGPD (Lei Geral de Proteção de Dados)

- `cliente_id` é o `UserName` pseudonimizado com HMAC-SHA256 (Hash-based Message Authentication Code, hash com chave secreta), truncado em 16 caracteres.
- A chave é obrigatória (`CLIENTE_ID_SAL`, mínimo de 16 caracteres), fica no `.env`, é a mesma para todo o grupo, é compartilhada fora do Git e nunca vai ao repositório. Trocar a chave exige recarregar o banco.
- Nenhum identificador vai para os slides nem para a chamada ao LLM (Large Language Model, modelo de linguagem).
- Gênero, idade, estado civil e dependentes só são usados para auditar, nunca para decidir.

## 11. Limitações

- Dados estonianos, de 2009 a 2021, só de empréstimos aprovados.
- Análise jurídica hipotética ("se este contrato fosse brasileiro").
- A coorte madura exclui os contratos recentes e muda a composição por prazo ao longo dos anos.
- Excluir gênero e idade do modelo não elimina proxies (variáveis que carregam a mesma informação). É isso que a auditoria de resíduos testa.
- Gênero está muito ligado ao país (gênero indefinido é quase só da Espanha).
- Quando o grupo compara contratos "parecidos" controlando por variáveis como renda, é preciso lembrar que a renda pode ser afetada pelo próprio gênero. Registrar isso na parte de ética.

## 12. Pendências com o Samuel

- [ ] Confirmar o alvo (seção 3), a coorte madura (seção 4) e a divisão treino e teste (seção 5).
- [ ] Euribor: 12 meses como principal e 3 meses como sensibilidade, mensal, 01/2009 a 07/2021 (seção 9). Piso em zero para valores negativos?
- [ ] Selic: confirmar a série 4189 para a leitura A (seção 9).
- [ ] Confirmar `parcela_mensal` na lista negra e a fórmula da parcela ÷ renda sem juros.
- [ ] Confirmar `estado_civil` e `n_dependentes` como só auditoria.
- [ ] Confirmar `experiencia_trabalho` como indisponível após 2017.
- [ ] Decidir o tratamento dos scores externos.
- [ ] Combinar quem cria a view de contratos encerrados de coortes maduras (proposta: Marcos).
