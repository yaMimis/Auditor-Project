
# DATA.md · Regras dos dados · Auditor de Preço Justo

> Versão 0.7 · 05/11/2026 · Responsável: Marcos (Dados e processo) · Revisão: Samuel (Modelo e juro justo)
> As decisões do Samuel de 05/11/2026 estão incorporadas; não restam itens **[A CONFIRMAR]**. Itens que dependem do grupo estão na seção 12. As seções 3, 4 e 5 seguem o `docs/DECISOES.md` do Samuel (29/10/2026); onde o texto e o notebook dele divergem, a seção diz qual foi seguido. As colunas citadas usam os nomes do banco (`01_schema_bondora.sql`).

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
- Reestruturados (7.941 contratos, 26,5%, com 76,2% de default contra 48,6% nos demais) **ficam no modelo**: tirá-los seria escolher os dados por algo que aconteceu depois da concessão, e o modelo subestimaria o risco. Eles saem **só da auditoria de preço**, porque o juro mudou no meio do contrato (marca `fora_da_auditoria`; `DECISOES.md`, seção 2). A view já segue essa regra.
- Ficam de fora os contratos de 2009 a 2016 ainda em andamento (1.045 sem a Eslováquia: 926 `Current` e 119 `Late` sem default). Só 2016 tem 609, o que infla um pouco o default de 2016 (63,1% contra 59,4% se todos entrassem como sem default).
- 2009–2012 tem só a Estônia, com default de 21% a 39%. Espanha e Finlândia entram em 2013–2014, e o default sobe a partir de 2014 (`DECISOES.md`, seção 10).

## 5. Divisão treino e teste

Por tempo (`data_emprestimo`) e por cliente (`DECISOES.md`, seção 4):

| Conjunto             | Concessões                                | Contratos                                            | Default |
| -------------------- | ------------------------------------------ | ---------------------------------------------------- | ------- |
| Treino e validação | 2009 a 2015                                | 20.011 (13.972 clientes)                             | 52,4%   |
| Teste                | 2016, sem clientes do treino               | 7.311 (6.290 clientes: EE 3.642, ES 2.226, FI 1.443) | 67,1%   |
| Fora                 | 2016 de clientes do treino; 2017 em diante | 2.594 e 147.978                                      | n/a     |

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

**Só auditoria (4): usadas apenas na auditoria de equidade, nunca para prever risco.** `estado_civil` e `n_dependentes` entram nesta categoria pela mesma lógica de gênero e idade: são atributos pessoais com risco de discriminação e só existem até 2017, então não serviriam para a carteira de 2017–2021 (decisão de 05/11; validar com o grupo).

`genero`, `idade`, `estado_civil`, `n_dependentes`

- `estado_civil` e `n_dependentes` só têm dados nos contratos até 2017, então a auditoria delas cobre só esse período.

**Indisponíveis após 2017 (7): fora do modelo** (decidido; estão em `PROIBIDAS`, `variaveis.py`). As quatro primeiras estão preenchidas em 2009–2016 (no máximo 1,0% em branco no treino e no teste), mas 96,4% em branco nos contratos de 2017 a 2021, que são 82,6% da base e a carteira a pontuar. As três últimas vêm com zero no lugar de vazio: zeros em no máximo 7% dos contratos até 2016, 70% a 72% em 2017 e 100% a partir de 2018, o que não é valor real. Um modelo treinado com elas perderia a informação justamente onde será usado.

`finalidade`, `situacao_emprego`, `area_ocupacao`, `experiencia_trabalho`, `divida_renda`, `caixa_livre`, `renda_empregador_principal`

- A carga grava as três últimas como vêm (zero), e elas já estão em `COLUNAS_INDISPONIVEIS_RECENTES` (`carga_bondora.py`), então o teste antivazamento as barra. Em qualquer análise que as use, tratá-las como NULL a partir de 2018.

**Identificadores e datas: servem para dividir e agrupar, não como variável.** O ano da concessão também não entra no modelo; o efeito de época vem da Euribor e, no preço, da margem por safra do juro justo.

`loan_id`, `cliente_id`, `numero`, `data_referencia`, `data_pedido`, `data_emprestimo`, `data_primeira_parcela`, `data_vencimento_original`

**Variáveis do modelo (XGBoost v2; lista em `variaveis.py`):**

- Numéricas: `valor_concedido`, `prazo_meses`, `renda_total`, `parcela_neutra_sobre_renda` (`valor_concedido / prazo_meses / renda_total`, parcela sem juros, porque `parcela_mensal` está na lista negra), `valor_sobre_renda`, `divida_sobre_renda` (`passivos_total / renda_total`), `renda_relativa` (renda ÷ mediana do país e ano, calculada no treino), `n_emprestimos_anteriores`, `valor_emprestimos_anteriores`, `passivos_existentes`, `pagamentos_anteriores`, `quitacoes_antecipadas_qtd`, `quitacoes_antecipadas_valor`, `score_ee_mini`
- Categóricas: `pais`, `novo_cliente`, `tempo_emprego_atual`, `escolaridade`, `tipo_moradia`, `tipo_verificacao`, `score_fi_asiakastieto`, `score_es_equifax`, `score_es_microl` (fora do próprio país: "sem_info"; categorias com menos de 1% viram "outros")
- Testadas e descartadas (`DECISOES.md`, seção 12): `fracao_concedida` (usa `valor_solicitado`), `caixa_livre_sobre_renda`, `divida_renda_bondora`, `refinanciamento_passivos` e as frações da renda vindas de auxílios e de pensão. Os componentes `renda_*` não entram: o principal, `renda_empregador_principal`, vem zerado desde 2018.
- Atenção: `pagamentos_anteriores` e `quitacoes_antecipadas_valor` mudam de regime (zeros de 84% e 99% dos contratos em 2014 para 11% e 89% em 2018, e 0% a partir de 2019), e a cobertura dos scores muda entre treino, teste e carteira (`score_es_microl`: 81% em branco no treino e 4% em 2017–2021; `score_es_equifax`: 81% e 96%). Confirmar o significado no dicionário; ver a seção 11.
- `pais` entra no modelo. O default é 42% na Estônia, 73% na Finlândia e 78% na Espanha (base de modelagem); sem o país, a auditoria de preço marcaria como discriminação o que é diferença de risco.

## 7. Valores especiais e qualidade

- `-1` nas colunas de código significa "sem informação" e vira NULL. O valor `0` é mantido; confirmar no dicionário o que ele significa em cada coluna.
- Datas anteriores a 2000 (como `0001-01-01`) viram NULL. `n_dependentes` "10Plus" vira 10.
- **Juros acima de 100% ao ano são legítimos** (Espanha 2.738 contratos, Finlândia 143, em 2016–2018; máximo de 264%). Não remover.
- Idade menor que 18 (53 contratos, 48 deles com idade 0) e renda zero (64 contratos): regras de validação no pandera. **Marcar, não excluir** (decisão de 05/11). Excluir não muda o modelo: idade não é variável do modelo, e renda fora da faixa de treino já leva o `prever()` a `revisao_manual`. Na auditoria de equidade, os contratos com idade menor que 18 ficam de fora.
- Outros alertas, para registrar no relatório de qualidade sem falhar o teste: `valor_concedido` maior que `valor_solicitado` (249 contratos), `prazo_meses` menor que 3 (221; o mínimo é 1), vencimento original diferente de concessão mais prazo em mais de 2 meses (133), `Current` com `data_default` (163) e `caixa_livre` negativo (23).
- **Zeros no lugar de vazio:** `divida_renda`, `caixa_livre` e `renda_empregador_principal` têm 100% de zeros a partir de 2018 (70% a 72% em 2017). A carga não os pega, porque só troca `-1` por NULL. Ver a seção 6.
- Gênero 2 ("indefinido") é quase só da Espanha (12.164 de 12.180; cerca de 46% dos contratos espanhóis). Na auditoria, tratar como dado ausente e comparar só 0 e 1, de preferência dentro de cada país.
- **Codificação do gênero em 2017–2019:** entre os contratos com gênero 0 ou 1, a proporção de mulheres na Estônia vai de 45% em 2016 para 26% em 2017 e 9% em 2018, e volta a 34% em 2019 e 51% em 2020 (Finlândia: 45%, 21%, 23%, 41% e 51%). Além disso, 5.633 clientes aparecem com os dois valores em contratos diferentes, e a idade deles é coerente entre os contratos (0 incoerências em 94.148 pares), ou seja, é a mesma pessoa. É um indício de erro de codificação nesse período; o dicionário do Bondora não o confirma. Gênero fica fora do treino e do teste, então o modelo não é afetado; a análise de gênero será apresentada ao final como achado, com essa ressalva.
- `score_es_microl` tem o valor "M" em cerca de 136 mil linhas; confirmar o significado no dicionário.
- `novo_cliente` e `n_emprestimos_anteriores` parecem medir coisas diferentes: 15.668 contratos têm `novo_cliente` verdadeiro e empréstimos anteriores, e 303 têm o caso oposto. Confirmar no dicionário antes de validar uma contra a outra.

## 8. Moeda e unidades

- **Valores em euro**, com uma exceção: a renda e os passivos dos contratos **da Estônia concedidos até 31/12/2010** vinham em coroas estonianas (EEK). A carga os converte para euros (÷ 15,6466; `src/dados/moeda.py`), e o treino faz o mesmo ao ler o CSV. Evidências: a renda mediana vai de 12.000 (dez/2010) para 860 (jan/2011), e o valor pedido de 2009–2010 multiplicado por 15,6466 dá um número redondo de coroas em 100% dos contratos. São 1.822 contratos, todos da Estônia.
- **Juros em % ao ano, como taxa nominal.** A taxa mensal do contrato é `juro_aa ÷ 12`. Conferido na parcela: com `juro_aa ÷ 12` o erro mediano é de 2,6% nos contratos acima de 100% ao ano, contra 36,6% com a equivalência composta, (1 + i)^(1/12) − 1.
- **A taxa do BC (série 20742) é efetiva.** O "% ao ano" dela é a composição das taxas mensais: 6,42% ao mês correspondem a 110,95% ao ano. A etiqueta é a mesma, e a convenção é outra.
- **Conversão para comparar** (feita pelo código do parecer, nunca no banco):

  | De                | Para                           | Fórmula                          |
  | ----------------- | ------------------------------ | --------------------------------- |
  | efetiva a.a. (BC) | nominal a.a. (como o contrato) | 12 × [(1 + efetiva)^(1/12) − 1] |
  | efetiva a.a.      | taxa ao mês                   | (1 + efetiva)^(1/12) − 1         |
  | nominal a.a.      | efetiva a.a.                   | (1 + nominal ÷ 12)^12 − 1       |

  Exemplo (concessão em mar/2016): 126,2% efetiva = 84,5% nominal = 7,04% ao mês.
- **O juro justo do `prever()` segue a mesma convenção nominal** (taxa mensal = juro ÷ 12), para a comparação com o juro cobrado ser na mesma base. A margem por safra foi recalibrada com essa convenção.

## 9. Fontes externas

- **Euribor (Portal de dados do BCE, data.ecb.europa.eu)** (decidido: 12 meses como principal, 3 meses como sensibilidade):
  - Principal: Euribor de 12 meses, série mensal, média das observações do mês (`FM.M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA`).
  - Sensibilidade: Euribor de 3 meses, mesma frequência (`FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA`).
  - Período: 01/2009 a 07/2021 (concessões de 28/02/2009 a 19/07/2021). Baixar a série completa e recortar depois.
  - Junção: mês de `data_emprestimo` com o mês da série. Os valores negativos (de 2015–2016 em diante) ficam como vêm na tabela; a fórmula do preço usa piso em zero (`DECISOES.md`, seção 7).
  - Contratos posteriores à série (auditoria de um contrato novo pela API) usam o último mês disponível. Atualizar a série até a data atual; com o último mês em 07/2021 (negativo), o custo do dinheiro fica em zero.
  - Limitação: a Euribor tem no máximo 12 meses, e a mediana do prazo dos contratos é de 60 meses (48 meses no treino e 36 no teste).
- **Selic (Banco Central do Brasil)** (decidido em 05/11): **cenário opcional "modo Brasil"** (leitura A), fora da entrega principal. Ele reprecificaria os contratos históricos com a Selic do mesmo mês, mas misturaria o risco do Bondora com o custo do dinheiro brasileiro. O motor base continua usando a Euribor da época. Série e carga ficam prontas para uso futuro.
  - Série SGS 4189, "Selic acumulada no mês anualizada base 252": mensal, em % ao ano, 01/2009 a 07/2021.
  - Descartadas: a 4390 (% ao mês; exige anualizar e erra em meses curtos) e a meta Selic do Dados de Mercado (valor do 1º dia do mês; defasa quando a meta muda). A meta fica só como conferência da 4189.
  - Limitação: a Selic é uma taxa de um dia útil, e a Euribor principal é de 12 meses. A comparação mais justa em prazo é com a Euribor de 3 meses.
- **Tabelas no banco:** `euribor_mensal` (`mes`, `euribor_3m`, `euribor_12m`), `selic_mensal` (`mes`, `selic_aa` e `selic_meta_aa`, esta só para conferência) e a view `vw_custo_do_dinheiro`, que liga cada contrato ao mês da concessão. Esquema em `02_schema_macro.sql`; carga em `carga_macro.py`. A série 20742 vai na tabela `bc_credito_pessoal_mensal` (`mes`, `taxa_aa`), que a `carga_macro.py` carrega quando o arquivo `data/raw/bcdata.sgs.20742.csv` existe; a view traz a coluna `bc_credito_pessoal_aa`, vazia antes de 03/2011.
- **Taxas de crédito do BC (referência de mercado)**: série SGS 20742, taxa média das novas operações de crédito pessoal não consignado para pessoas físicas, mensal, em % ao ano **efetiva**, de 03/2011 a 07/2021 (na janela, de 66,3% a 141,9% efetiva, ou de 52,0% a 91,7% nominal).
  - Uso: só contexto no painel do analista e no parecer, mostrando a taxa média do mercado brasileiro no mês da concessão de cada contrato (coluna `bc_credito_pessoal_aa` da view, em % efetiva ao ano). **Quem escreve a frase é o código, e não o LLM**: o código converte o valor para nominal (seção 8) e monta uma frase fixa, num campo próprio do parecer (`contexto_mercado`), separado do texto do LLM. O LLM não recebe o número, e o parecer não conclui "justo" ou "injusto" a partir dele; se o LLM citar uma "média do mercado", a conferência recusa o parecer. O campo é opcional: antes de 03/2011 fica vazio e a frase não aparece. Não calibra o preço e não entra no modelo.
  - Onde fica: a conversão, o campo `contexto_mercado` e os testes ficam em `genai/src/checagem.py` (Maria), com a regra em `REGRAS_PARECER.md` e o formato em `FORMATO_JSON.md`. Proposta, a combinar com a Maria: mostrar a efetiva entre parênteses, porque é a que o BC divulga e a que o CDC (art. 52) manda informar.
  - Escala: a série fica mensal, e cada contrato usa o mês da concessão. Não anualizar: a taxa varia de 8 a 37 pontos dentro de um mesmo ano, e usar a média do ano erraria, em média, 7 pontos.
  - Conferência opcional: a série SGS 25464 (a mesma medida, mensal, em % ao mês) deve dar o mesmo resultado que a conversão (12 × taxa mensal), com diferença só de arredondamento, porque o BC publica 2 casas.
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
- A referência de mercado do BC (série 20742) começa em 03/2011, e os dois mercados são muito diferentes: na mesma base (nominal ao ano), a taxa média do Bondora ficou abaixo da do BC em todos os 125 meses (mediana de 0,41 da taxa do BC; cerca de 30% contra 72% ao ano), e o risco também difere (56,0% de default na base de modelagem do Bondora). Serve de contexto, não de veredito sobre preço justo.
- Excluir gênero e idade do modelo não elimina proxies (variáveis que carregam a mesma informação). É isso que a auditoria de resíduos testa.
- Gênero está muito ligado ao país (gênero indefinido é quase só da Espanha).
- A codificação do gênero parece quebrada em 2017–2019 (proporção de mulheres na Estônia: 45% em 2016, 9% em 2018, 51% em 2020; 5.633 clientes com os dois valores). Gênero fica fora do treino e do teste. A análise será apresentada ao final como achado, com essa ressalva, e é relevante para a parte de governança, ética e equidade.
- Várias colunas mudam de regime depois de 2017 (zeros no lugar de vazio e campos de histórico), então a carteira a pontuar difere da base de treino.
- Quando o grupo compara contratos "parecidos" controlando por variáveis como renda, é preciso lembrar que a renda pode ser afetada pelo próprio gênero. Registrar isso na parte de ética.

## 12. Pendências com o Samuel

- [X] Reestruturados: ficam no modelo e saem só da auditoria de preço (seção 4).
- [X] Variáveis indisponíveis após 2017 (`finalidade`, `situacao_emprego`, `area_ocupacao`, `experiencia_trabalho` e, com zero no lugar de vazio, `divida_renda`, `caixa_livre` e `renda_empregador_principal`): fora do modelo (seção 6).
- [X] Desenho do teste e da validação: mantido o atual (teste em 2016 só com clientes novos, GroupKFold por cliente no treino, validação temporal em 2015, calibração Platt; `DECISOES.md`, seções 4 e 12). Os resultados em `docs/resultados/` dependem dele. Janela móvel e comparação com e sem 2009–2012 ficam como trabalho futuro.
- [X] Euribor: o prazo (12 meses como principal e 3 meses como sensibilidade, mensal, 01/2009 a 07/2021; seção 9).
- [X] Selic: série 4189 confirmada; "modo Brasil" é cenário opcional, fora da entrega principal; motor base na Euribor (seção 9).
- [X] Série 20742 como referência de mercado do BC, só como contexto, com 2009 a 02/2011 sem benchmark (documento de contextualização do Samuel, 31/10; seção 9).
- [ ] Campo da referência de mercado: desenho proposto pela Maria (campo opcional `bc_credito_pessoal_aa` na entrada e `contexto_mercado` na saída, frase escrita pelo código, conversão para nominal; seção 9). Falta a Yasmin passar o valor da view e mostrar o campo, e avisar todos da mudança de formato.
- [X] Fórmula da parcela ÷ renda sem juros confirmada (`parcela_neutra`, `variaveis.py`).
- [X] Marcos: incluir `divida_renda`, `caixa_livre` e `renda_empregador_principal` em `COLUNAS_INDISPONIVEIS_RECENTES` (feito na `carga_bondora.py`).
- [ ] Marcos: conferir no dicionário o significado de `pagamentos_anteriores`, `quitacoes_antecipadas_valor` e de `novo_cliente` frente a `n_emprestimos_anteriores`.
- [X] Gênero: análise final em **2013–2016** (os três países presentes e antes da quebra de codificação de 2017–2019; seção 7). Proposta do Samuel; validar com o grupo.
- [ ] Grupo: validar `estado_civil` e `n_dependentes` como só auditoria (proposta do Samuel: sim; seção 6).
- [X] Scores externos: entram no XGBoost v2 (seção 6).
- [ ] Conferir a view `vw_base_modelagem` contra os números do `DECISOES.md` (20.011 no treino e 7.311 no teste).
- [ ] Marcos: atualizar a Euribor (12m e 3m) até a data atual (seção 9)
