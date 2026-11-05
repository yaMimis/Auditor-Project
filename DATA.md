# DATA.md · Regras dos dados · Auditor de Preço Justo

<<<<<<< HEAD
> Versão 0.5 (rascunho) · 31/10/2026 · Responsável: Marcos (Dados e processo) · Revisão: Samuel (Modelo e juro justo)
=======
> Versão 0.6 (rascunho) · 02/11/2026 · Responsável: Marcos (Dados e processo) · Revisão: Samuel (Modelo e juro justo)
>>>>>>> 1f820b3c914b802dbd014244569ce101f8323b73
> Itens marcados **[A CONFIRMAR]** dependem de decisão do Samuel. As seções 3, 4 e 5 seguem o `docs/DECISOES.md` do Samuel (29/10/2026); onde o texto e o notebook dele divergem, a seção diz qual foi seguido. As colunas citadas usam os nomes do banco (`01_schema_bondora.sql`).

## 1. Fonte e versão

- Bondora LoanData: 179.235 contratos, 112 colunas, concessões de 2009 a 2021, data de corte 20/07/2021 (`ReportAsOfEOD`).
- Arquivo: `data/raw/LoanData_Bondora.csv`. SHA-256 (impressão digital do arquivo): `4728fc5ecf6d1f42246d97780a827d43b133dfa09b9f2f363ad91eee588663b5`. Conferir com `Get-FileHash data\raw\LoanData_Bondora.csv -Algorithm SHA256`.
- Dicionário de dados: Public Reports do Bondora, consultado em 28/10/2026.
- O CSV nunca entra no Git.

## 2. Unidade de análise

Uma linha por contrato, nas três tabelas ligadas por `loan_id`: `emprestimo`, `cliente` e `historico_credito`. O mesmo cliente tem vários contratos (85.087 clientes; 36.185 deles com mais de um) e é identificado por `cliente_id`.

## 3. Alvo (o que é inadimplente)

`inadimplente = 1` quando `data_default` está preenchida; senão 0. Não se usa `status` (`DECISOES.md`, seção 1). O Bondora registra essa data quando o atraso passa de 60 dias (segundo o dicionário; anotar a data da consulta).

Os contratos que atrasaram e depois quitaram (`status = 'Repaid'` com data de default: 5.465 na base de modelagem) contam como inadimplentes; a recuperação entra na LGD (Loss Given Default, perda dado o default).

A PD (Probability of Default, probabilidade de default) é a de "default em qualquer momento do contrato".

## 4. Recorte (base de modelagem)

Entra o contrato concedido de 2009 a 2016 (`data_emprestimo`) e encerrado: `status = 'Repaid'` ou `data_default` preenchida (`DECISOES.md`, seção 2). A view `vw_base_modelagem` (`03_view_modelagem.sql`) aplica esta regra e marca o conjunto de cada contrato.

- Resultado: 30.210 contratos, com 56,3% de default.
- Sai a Eslováquia (294 contratos, quase todos de 2014). Sobram **29.916 contratos, com 56,0% de default**.
- **[A CONFIRMAR]** Reestruturados: o texto do `DECISOES.md` manda excluí-los, mas o notebook do Samuel não aplica a exclusão, e a view segue o notebook. São 7.941 contratos (26,5%), com 76,2% de default contra 48,6% nos demais. Excluí-los reduziria a base a 21.975.
- Ficam de fora os contratos de 2009 a 2016 ainda em andamento (1.045 sem a Eslováquia: 926 `Current` e 119 `Late` sem default). Só 2016 tem 609, o que infla um pouco o default de 2016 (63,1% contra 59,4% se todos entrassem como sem default).
- 2009–2012 tem só a Estônia, com default de 21% a 39%. Espanha e Finlândia entram em 2013–2014, e o default sobe a partir de 2014 (`DECISOES.md`, seção 10).

## 5. Divisão treino e teste

Por tempo (`data_emprestimo`) e por cliente (`DECISOES.md`, seção 4):

| Conjunto           | Concessões                    | Contratos                                               | Default |
| ------------------ | ------------------------------ | ------------------------------------------------------- | ------- |
| Treino e validação | 2009 a 2015                    | 20.011 (13.972 clientes)                                | 52,4%   |
| Teste              | 2016, sem clientes do treino   | 7.311 (6.290 clientes: EE 3.642, ES 2.226, FI 1.443)    | 67,1%   |
| Fora               | 2016 de clientes do treino; 2017 em diante | 2.594 e 147.978                              | n/a     |

- Validação dentro do treino: GroupKFold por cliente.
- Regra por cliente: se o `cliente_id` aparece no treino, seus contratos de 2016 saem do teste. São 2.594 contratos (26,2% do teste bruto de 9.905), de 1.874 clientes. Metade dos contratos da base é de clientes repetidos (50,7%).
- O teste só tem clientes novos e é mais arriscado que o treino (67,1% contra 52,4%) e que todo o 2016 (63,1%). Esperar perda de calibração e avaliar por país.
- 2017 em diante (147.978 contratos, 82,6% da base) não entra no treino nem no teste, porque ainda não tem desfecho suficiente, mas é a carteira que será pontuada na auditoria e no ROI.

## 6. Colunas

**Lista negra (26): nunca entram como variável do modelo.** São pós-concessão ou saídas do próprio Bondora. Ficam no banco para montar o alvo, o preço cobrado, a comparação com a PD do Bondora e o backtest.

`juro_aa`, `parcela_mensal`, `rating`, `versao_modelo_bondora`, `pd_bondora`, `perda_esperada_bondora`, `lgd_bondora`, `retorno_esperado_bondora`, `status`, `data_default`, `dias_atraso`, `pior_categoria_atraso`, `reestruturado`, `data_vencimento_atual`, `data_fim_contrato`, `data_ultimo_pagamento`, `principal_pago`, `juros_multas_pagos`, `principal_baixado`, `juros_baixados`, `saldo_principal`, `recuperacao_principal`, `recuperacao_juros`, `ead1`, `ead2`, `estagio_recuperacao`

- `juro_aa` é o preço que estamos auditando; usá-lo para prever o risco tornaria a auditoria circular.
- `parcela_mensal` está na lista negra porque, dados o valor e o prazo, ela embute o juro (correlação de 0,90 com a parcela calculada a partir do juro).
- A `COLUNAS_LISTA_NEGRA` exportada pela `carga_bondora.py` já inclui `parcela_mensal`; o teste automático não precisa somá-la à parte.

**Só auditoria (4): usadas apenas na auditoria de equidade, nunca para prever risco.** `estado_civil` e `n_dependentes` ainda precisam da aprovação do grupo **[A CONFIRMAR]**.

`genero`, `idade`, `estado_civil`, `n_dependentes`

- `estado_civil` e `n_dependentes` só têm dados nos contratos até 2017, então a auditoria delas cobre só esse período.

<<<<<<< HEAD
**Indisponíveis após 2017 (4): fora do modelo [A CONFIRMAR].** Estão preenchidas em 2009–2016 (no máximo 1,0% em branco no treino e no teste), mas 96,4% em branco nos contratos de 2017 a 2021, que são 82,6% da base e a carteira a pontuar. Um modelo treinado com elas perderia a informação justamente onde será usado.
=======
**Indisponíveis após 2017 (7): fora do modelo [A CONFIRMAR].** As quatro primeiras estão preenchidas em 2009–2016 (no máximo 1,0% em branco no treino e no teste), mas 96,4% em branco nos contratos de 2017 a 2021, que são 82,6% da base e a carteira a pontuar. As três últimas vêm com zero no lugar de vazio: zeros em no máximo 7% dos contratos até 2016, 70% a 72% em 2017 e 100% a partir de 2018, o que não é valor real. Um modelo treinado com elas perderia a informação justamente onde será usado.
>>>>>>> 1f820b3c914b802dbd014244569ce101f8323b73

`finalidade`, `situacao_emprego`, `area_ocupacao`, `experiencia_trabalho`, `divida_renda`, `caixa_livre`, `renda_empregador_principal`

- A carga grava as três últimas como vêm (zero), e elas já estão em `COLUNAS_INDISPONIVEIS_RECENTES` (`carga_bondora.py`), então o teste antivazamento as barra. Em qualquer análise que as use, tratá-las como NULL a partir de 2018.

**Identificadores e datas: servem para dividir e agrupar, não como variável.** O ano da concessão também não entra; o efeito de época vem da Euribor.

`loan_id`, `cliente_id`, `numero`, `data_referencia`, `data_pedido`, `data_emprestimo`, `data_primeira_parcela`, `data_vencimento_original`

**Candidatas a variáveis do modelo [A CONFIRMAR]:**

- Contrato: `novo_cliente`, `valor_solicitado`, `valor_concedido`, `prazo_meses`, `tipo_verificacao`
<<<<<<< HEAD
- Cliente: `pais`, `escolaridade`, `tipo_moradia`, `tempo_emprego_atual`, as oito colunas `renda_*`
- Histórico: `n_emprestimos_anteriores`, `valor_emprestimos_anteriores`, `pagamentos_anteriores` (0% em branco no treino e no teste, mas 42% em 2017–2021), `quitacoes_antecipadas_valor`, `quitacoes_antecipadas_qtd`, `passivos_existentes`, `passivos_total`, `refinanciamento_passivos`, `divida_renda`, `caixa_livre`
=======
- Cliente: `pais`, `escolaridade`, `tipo_moradia`, `tempo_emprego_atual`, `renda_total` (os componentes `renda_*` não entram: o principal, `renda_empregador_principal`, vem zerado desde 2018)
- Histórico: `n_emprestimos_anteriores`, `valor_emprestimos_anteriores`, `pagamentos_anteriores` (0% em branco no treino e no teste, mas 42% em 2017–2021), `quitacoes_antecipadas_valor`, `quitacoes_antecipadas_qtd`, `passivos_existentes`, `passivos_total`, `refinanciamento_passivos`
- Atenção: `pagamentos_anteriores` e `quitacoes_antecipadas_valor` mudam de regime. Os zeros vão de 84% e 99% dos contratos em 2014 para 11% e 89% em 2018, e para 0% nas duas a partir de 2019. Confirmar o significado no dicionário antes de usar.
>>>>>>> 1f820b3c914b802dbd014244569ce101f8323b73
- Scores externos (`score_es_microl`, `score_es_equifax`, `score_fi_asiakastieto`, `score_ee_mini`): a cobertura muda muito entre treino, teste e carteira (`score_es_microl` tem 81% em branco no treino e 4% em 2017–2021; `score_es_equifax` faz o contrário, com 81% e 96%) e varia por país. Sugestão: fora do modelo base, testar depois como sensibilidade.
- `pais` entra no modelo. O default é 42% na Estônia, 73% na Finlândia e 78% na Espanha (base de modelagem); sem o país, a auditoria de preço marcaria como discriminação o que é diferença de risco.
- A variável derivada parcela ÷ renda deve usar `valor_concedido / prazo_meses / renda_total` (parcela sem juros), porque `parcela_mensal` está na lista negra.

## 7. Valores especiais e qualidade

- `-1` nas colunas de código significa "sem informação" e vira NULL. O valor `0` é mantido; confirmar no dicionário o que ele significa em cada coluna.
- Datas anteriores a 2000 (como `0001-01-01`) viram NULL. `n_dependentes` "10Plus" vira 10.
- **Juros acima de 100% ao ano são legítimos** (Espanha 2.738 contratos, Finlândia 143, em 2016–2018; máximo de 264%). Não remover.
- Idade menor que 18 (53 contratos, 48 deles com idade 0) e renda zero (64 contratos): regras de validação no pandera. Marcar ou excluir **[A CONFIRMAR]**.
- Outros alertas, para registrar no relatório de qualidade sem falhar o teste: `valor_concedido` maior que `valor_solicitado` (249 contratos), `prazo_meses` menor que 3 (221; o mínimo é 1), vencimento original diferente de concessão mais prazo em mais de 2 meses (133), `Current` com `data_default` (163) e `caixa_livre` negativo (23).
- **Zeros no lugar de vazio:** `divida_renda`, `caixa_livre` e `renda_empregador_principal` têm 100% de zeros a partir de 2018 (70% a 72% em 2017). A carga não os pega, porque só troca `-1` por NULL. Ver a seção 6.
- Gênero 2 ("indefinido") é quase só da Espanha (12.164 de 12.180; cerca de 46% dos contratos espanhóis). Na auditoria, tratar como dado ausente e comparar só 0 e 1, de preferência dentro de cada país.
- **Codificação do gênero em 2017–2019:** entre os contratos com gênero 0 ou 1, a proporção de mulheres na Estônia vai de 45% em 2016 para 26% em 2017 e 9% em 2018, e volta a 34% em 2019 e 51% em 2020 (Finlândia: 45%, 21%, 23%, 41% e 51%). Além disso, 5.633 clientes aparecem com os dois valores em contratos diferentes, e a idade deles é coerente entre os contratos (0 incoerências em 94.148 pares), ou seja, é a mesma pessoa. É um indício de erro de codificação nesse período; o dicionário do Bondora não o confirma. Gênero fica fora do treino e do teste, então o modelo não é afetado; a análise de gênero será apresentada ao final como achado, com essa ressalva.
- `score_es_microl` tem o valor "M" em cerca de 136 mil linhas; confirmar o significado no dicionário.
- `novo_cliente` e `n_emprestimos_anteriores` parecem medir coisas diferentes: 15.668 contratos têm `novo_cliente` verdadeiro e empréstimos anteriores, e 303 têm o caso oposto. Confirmar no dicionário antes de validar uma contra a outra.

## 8. Moeda e unidades

Valores em euro. Juros em % ao ano, como vêm do Bondora.

## 9. Fontes externas

- **Euribor (Portal de dados do BCE, data.ecb.europa.eu)** **[A CONFIRMAR com o Samuel: o prazo]**:
  - Principal: Euribor de 12 meses, série mensal, média das observações do mês (`FM.M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA`).
  - Sensibilidade: Euribor de 3 meses, mesma frequência (`FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA`).
  - Período: 01/2009 a 07/2021 (concessões de 28/02/2009 a 19/07/2021). Baixar a série completa e recortar depois.
  - Junção: mês de `data_emprestimo` com o mês da série. Os valores negativos (de 2015–2016 em diante) ficam como vêm na tabela; a fórmula do preço usa piso em zero (`DECISOES.md`, seção 7).
  - Limitação: a Euribor tem no máximo 12 meses, e a mediana do prazo dos contratos é de 60 meses (48 meses no treino e 36 no teste).
- **Selic (Banco Central do Brasil)** **[A CONFIRMAR com o Samuel]**: usada só no cenário "modo Brasil" (leitura A), que reprecifica os contratos históricos com a Selic do mesmo mês. O motor base continua usando a Euribor da época.
  - Série SGS 4189, "Selic acumulada no mês anualizada base 252": mensal, em % ao ano, 01/2009 a 07/2021.
  - Descartadas: a 4390 (% ao mês; exige anualizar e erra em meses curtos) e a meta Selic do Dados de Mercado (valor do 1º dia do mês; defasa quando a meta muda). A meta fica só como conferência da 4189.
  - Limitação: a Selic é uma taxa de um dia útil, e a Euribor principal é de 12 meses. A comparação mais justa em prazo é com a Euribor de 3 meses.
- **Tabelas no banco:** `euribor_mensal` (`mes`, `euribor_3m`, `euribor_12m`), `selic_mensal` (`mes`, `selic_aa` e `selic_meta_aa`, esta só para conferência) e a view `vw_custo_do_dinheiro`, que liga cada contrato ao mês da concessão. Esquema em `02_schema_macro.sql`; carga em `carga_macro.py`. A série 20742 vai na tabela `bc_credito_pessoal_mensal` (`mes`, `taxa_aa`), que a `carga_macro.py` carrega quando o arquivo `data/raw/bcdata.sgs.20742.csv` existe; a view traz a coluna `bc_credito_pessoal_aa`, vazia antes de 03/2011.
- **Taxas de crédito do BC (referência de mercado)** **[A CONFIRMAR com o Samuel]**: série SGS 20742, taxa média de juros do crédito pessoal não consignado para pessoas físicas, mensal, em % ao ano, de 03/2011 a 07/2021.
  - Uso: só contexto no painel do analista e no parecer, mostrando a taxa média do mercado brasileiro no mês da concessão de cada contrato (coluna `bc_credito_pessoal_aa` da view). O número vem da API, nunca do LLM, e o parecer não conclui "justo" ou "injusto" a partir dele. Antes de 03/2011 o campo fica vazio e o parecer não cita a referência. Não calibra o preço e não entra no modelo.
  - Cobertura: 2009 a 02/2011 ficam sem benchmark (1.894 contratos). Não emendar com a série de crédito pessoal total, que inclui o consignado.
  - O ranking de instituições de 2026 foi retirado do projeto.

## 10. Privacidade e LGPD (Lei Geral de Proteção de Dados)

- `cliente_id` é o `UserName` pseudonimizado com HMAC-SHA256 (Hash-based Message Authentication Code, hash com chave secreta), truncado em 16 caracteres.
- A chave é obrigatória (`CLIENTE_ID_SAL`, mínimo de 16 caracteres), fica no `.env`, é a mesma para todo o grupo, é compartilhada fora do Git e nunca vai ao repositório. Trocar a chave exige recarregar o banco.
- Nenhum identificador vai para os slides nem para a chamada ao LLM (Large Language Model, modelo de linguagem).
- Gênero, idade, estado civil e dependentes só são usados para auditar, nunca para decidir.

## 11. Limitações

- Dados estonianos, de 2009 a 2021, só de empréstimos aprovados.
- Análise jurídica hipotética ("se este contrato fosse brasileiro").
- A base de modelagem termina em 2016, e a carteira a pontuar (2017 a 2021) é 82,6% da base: o modelo será usado fora da época em que foi treinado e testado. O juro médio mudou nesse período (41,2% em 2016, 46,7% em 2017 e 31,7% em 2018, em todos os contratos).
- Só entram contratos encerrados. Os 609 de 2016 ainda em andamento ficam de fora e inflam um pouco o default de 2016.
- O teste só tem clientes novos, com default maior que o do 2016 inteiro (67,1% contra 63,1%).
- 2009–2012 tem só a Estônia, com default menor; o default sobe a partir de 2014, em boa parte pela entrada da Espanha e da Finlândia.
- A referência de mercado do BC (série 20742) começa em 03/2011 e o risco dos dois mercados é muito diferente (56,0% de default na base de modelagem do Bondora): serve de contexto, não de veredito sobre preço justo.
- Excluir gênero e idade do modelo não elimina proxies (variáveis que carregam a mesma informação). É isso que a auditoria de resíduos testa.
- Gênero está muito ligado ao país (gênero indefinido é quase só da Espanha).
- A codificação do gênero parece quebrada em 2017–2019 (proporção de mulheres na Estônia: 45% em 2016, 9% em 2018, 51% em 2020; 5.633 clientes com os dois valores). Gênero fica fora do treino e do teste. A análise será apresentada ao final como achado, com essa ressalva, e é relevante para a parte de governança, ética e equidade.
- Várias colunas mudam de regime depois de 2017 (zeros no lugar de vazio e campos de histórico), então a carteira a pontuar difere da base de treino.
- Quando o grupo compara contratos "parecidos" controlando por variáveis como renda, é preciso lembrar que a renda pode ser afetada pelo próprio gênero. Registrar isso na parte de ética.

## 12. Pendências com o Samuel

- [ ] Reestruturados: excluir ou não do treino? O texto e o notebook do `DECISOES.md` divergem (seção 4).
<<<<<<< HEAD
- [ ] Variáveis indisponíveis após 2017 (`finalidade`, `situacao_emprego`, `area_ocupacao`, `experiencia_trabalho`): fora do modelo principal? (seção 6).
=======
- [ ] Variáveis indisponíveis após 2017 (`finalidade`, `situacao_emprego`, `area_ocupacao`, `experiencia_trabalho` e, com zero no lugar de vazio, `divida_renda`, `caixa_livre` e `renda_empregador_principal`): fora do modelo principal? (seção 6).
>>>>>>> 1f820b3c914b802dbd014244569ce101f8323b73
- [ ] Desenho do teste e da validação: manter todo o 2016 tirando do treino os clientes do teste; validação por janela móvel; calibrar com o ano mais recente; comparar com e sem 2009–2012 (ver o documento "Avaliação do desenho de modelagem").
- [ ] Euribor: o prazo (12 meses como principal e 3 meses como sensibilidade, mensal, 01/2009 a 07/2021; seção 9).
- [ ] Selic: confirmar a série 4189 e que a leitura A é um cenário "modo Brasil", com o motor base na Euribor (seção 9).
- [ ] Confirmar a série 20742 como referência de mercado do BC, só como contexto, com 2009 a 02/2011 sem benchmark (seção 9).
- [ ] Combinar com a Yasmin e a Maria o campo da referência de mercado na API e no parecer (mudar o formato exige aviso a todos).
- [ ] Confirmar a fórmula da parcela ÷ renda sem juros.
<<<<<<< HEAD
=======
- [x] Marcos: incluir `divida_renda`, `caixa_livre` e `renda_empregador_principal` em `COLUNAS_INDISPONIVEIS_RECENTES` (feito na `carga_bondora.py`).
- [ ] Marcos: conferir no dicionário o significado de `pagamentos_anteriores`, `quitacoes_antecipadas_valor` e de `novo_cliente` frente a `n_emprestimos_anteriores`.
- [ ] Gênero: só para registro, o período da análise final (por exemplo 2013–2016 contra todos os anos) e a ressalva sobre 2017–2019 (seção 7).
>>>>>>> 1f820b3c914b802dbd014244569ce101f8323b73
- [ ] Grupo: `estado_civil` e `n_dependentes` como só auditoria.
- [ ] Decidir o tratamento dos scores externos.
- [ ] Conferir a view `vw_base_modelagem` contra os números do `DECISOES.md` (20.011 no treino e 7.311 no teste).
