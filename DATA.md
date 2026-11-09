# DATA.md · Regras dos dados · Auditor de Preço Justo

> Versão 0.7 (rascunho) · 08/11/2026 · Responsável: Marcos (Dados e processo) · Revisão: Samuel (Modelo e juro justo)
> Legenda: **[DEFINIDO]** = decisão registrada no `docs/DECISOES.md` (Samuel) ou já feita no código; **[JULGADO DEFINIDO]** = não há decisão escrita, mas o texto e o código do grupo já a seguem (vale um aviso se alguém discordar); **[A CONFIRMAR]** = ainda aberto. As seções 3, 4 e 5 seguem o `docs/DECISOES.md` do Samuel (atualizado em 05/11/2026). As colunas citadas usam os nomes do banco (`01_schema_bondora.sql`).

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
- **[DEFINIDO]** Reestruturados **ficam no modelo** (treino e teste), sem a coluna `reestruturado` como variável (ela é pós-concessão e vazaria o default). Saem **só da comparação de preço da auditoria** (coluna `fora_da_auditoria` no lote do Samuel; `DECISOES.md`, seção 2). São 7.941 contratos (26,5%), com 76,2% de default contra 48,6% nos demais. Tirá-los da base faria o modelo enxergar 48,6% de default em vez de 56,0% e subestimar o risco. No retorno realizado (seção 14) eles somam +1,34 mi € e os demais, −1,35 mi €.
- Ficam de fora os contratos de 2009 a 2016 ainda em andamento (1.045 sem a Eslováquia: 926 `Current` e 119 `Late` sem default). Só 2016 tem 609, o que infla um pouco o default de 2016 (63,1% contra 59,4% se todos entrassem como sem default).
- 2009–2012 tem só a Estônia, com default de 21% a 39%. Espanha e Finlândia entram em 2013–2014, e o default sobe a partir de 2014 (`DECISOES.md`, seção 13).

## 5. Divisão treino e teste

Por tempo (`data_emprestimo`) e por cliente (`DECISOES.md`, seção 4):

| Conjunto           | Concessões                    | Contratos                                               | Default |
| ------------------ | ------------------------------ | ------------------------------------------------------- | ------- |
| Treino e validação | 2009 a 2015                    | 20.011 (13.972 clientes)                                | 52,4%   |
| Teste              | 2016, sem clientes do treino   | 7.311 (6.290 clientes: EE 3.642, ES 2.226, FI 1.443)    | 67,1%   |
| Fora               | 2016 de clientes do treino; 2017 em diante | 2.594 e 147.978                              | n/a     |

- Validação dentro do treino: GroupKFold por cliente.
- **[DEFINIDO]** Escolha de variáveis e de parâmetros só com validação temporal dentro do treino (ajuste até 2014, validação em 2015, clientes novos); o teste de 2016 não ajusta nada (`DECISOES.md`, seção 4). O teste fica só com clientes novos (7.311).
- **[DEFINIDO]** A validação por janela móvel e a comparação com e sem 2009–2012 só entram se sobrar tempo; senão ficam como limitação (resposta do Samuel).
- Regra por cliente: se o `cliente_id` aparece no treino, seus contratos de 2016 saem do teste. São 2.594 contratos (26,2% do teste bruto de 9.905), de 1.874 clientes. Metade dos contratos da base é de clientes repetidos (50,7%).
- O teste só tem clientes novos e é mais arriscado que o treino (67,1% contra 52,4%) e que todo o 2016 (63,1%). Esperar perda de calibração e avaliar por país.
- 2017 em diante (147.978 contratos, 82,6% da base) não entra no treino nem no teste, porque ainda não tem desfecho suficiente, mas é a carteira que será pontuada na auditoria e no ROI.

## 6. Colunas

**Lista negra (26): nunca entram como variável do modelo.** São pós-concessão ou saídas do próprio Bondora. Ficam no banco para montar o alvo, o preço cobrado, a comparação com a PD do Bondora e o backtest.

`juro_aa`, `parcela_mensal`, `rating`, `versao_modelo_bondora`, `pd_bondora`, `perda_esperada_bondora`, `lgd_bondora`, `retorno_esperado_bondora`, `status`, `data_default`, `dias_atraso`, `pior_categoria_atraso`, `reestruturado`, `data_vencimento_atual`, `data_fim_contrato`, `data_ultimo_pagamento`, `principal_pago`, `juros_multas_pagos`, `principal_baixado`, `juros_baixados`, `saldo_principal`, `recuperacao_principal`, `recuperacao_juros`, `ead1`, `ead2`, `estagio_recuperacao`

- `juro_aa` é o preço que estamos auditando; usá-lo para prever o risco tornaria a auditoria circular.
- `parcela_mensal` está na lista negra porque, dados o valor e o prazo, ela embute o juro (correlação de 0,90 com a parcela calculada a partir do juro).
- A `COLUNAS_LISTA_NEGRA` exportada pela `carga_bondora.py` já inclui `parcela_mensal`; o teste automático não precisa somá-la à parte.

**Só auditoria (4): usadas apenas na auditoria de equidade, nunca para prever risco.** `estado_civil` e `n_dependentes` ficam só para auditoria **[DEFINIDO]** (`DECISOES.md`, pendências).

`genero`, `idade`, `estado_civil`, `n_dependentes`

- `estado_civil` e `n_dependentes` só têm dados nos contratos até 2017, então a auditoria delas cobre só esse período.

**Indisponíveis após 2017 (7): fora do modelo [DEFINIDO].** As quatro primeiras estão preenchidas em 2009–2016 (no máximo 1,0% em branco no treino e no teste), mas 96,4% em branco nos contratos de 2017 a 2021, que são 82,6% da base e a carteira a pontuar. As três últimas vêm com zero no lugar de vazio: zeros em no máximo 7% dos contratos até 2016, 70% a 72% em 2017 e 100% a partir de 2018, o que não é valor real. Um modelo treinado com elas perderia a informação justamente onde será usado.

`finalidade`, `situacao_emprego`, `area_ocupacao`, `experiencia_trabalho`, `divida_renda`, `caixa_livre`, `renda_empregador_principal`

- A carga grava as três últimas como vêm (zero), e elas já estão em `COLUNAS_INDISPONIVEIS_RECENTES` (`carga_bondora.py`), então o teste antivazamento as barra. Em qualquer análise que as use, tratá-las como NULL a partir de 2018.

**Identificadores e datas: servem para dividir e agrupar, não como variável.** O ano da concessão também não entra; o efeito de época vem da Euribor.

`loan_id`, `cliente_id`, `numero`, `data_referencia`, `data_pedido`, `data_emprestimo`, `data_primeira_parcela`, `data_vencimento_original`

**Variáveis do modelo [DEFINIDO]: 21 desde 05/11** (`DECISOES.md`, seção 5; a v3 tinha 23).

| Grupo | Variáveis |
| --- | --- |
| Pedido | `valor_concedido`, `prazo_meses`, `pais` |
| Renda e dívidas | `renda_total`, `parcela_neutra_sobre_renda`, `valor_sobre_renda`, `divida_sobre_renda`, `renda_relativa`, `passivos_existentes` |
| Perfil | `novo_cliente`, `tempo_emprego_atual`, `escolaridade`, `tipo_moradia`, `tipo_verificacao` |
| Histórico na plataforma | `n_emprestimos_anteriores`, `valor_emprestimos_anteriores`, `quitacoes_antecipadas_qtd` |
| Scores de bureau | `score_ee_mini`, `score_fi_asiakastieto`, `score_es_equifax`, `score_es_microl` (fora do próprio país: "sem_info") |

- **[DEFINIDO]** A parcela ÷ renda é `valor_concedido ÷ prazo_meses ÷ renda_total` (parcela neutra, sem o juro), porque `parcela_mensal` está na lista negra e o juro é vazamento. Renda zero vira vazio, nunca infinito. Os componentes `renda_*` não entram.
- **[DEFINIDO]** `pais` entra no modelo. O default é 42% na Estônia, 73% na Finlândia e 78% na Espanha (base de modelagem); sem o país, a auditoria de preço marcaria como discriminação o que é diferença de risco.
- **[DEFINIDO]** Os scores externos entram, com "sem_info" fora do próprio país. Atenção: a cobertura muda muito entre treino, teste e carteira (`score_es_microl` tem 81% em branco no treino e 4% em 2017–2021; `score_es_equifax` faz o contrário, com 81% e 96%) e varia por país.
- **[DEFINIDO]** Retiradas em 05/11: `pagamentos_anteriores` e `quitacoes_antecipadas_valor`, que mudam de regime (os zeros vão de cerca de 89% para 0% em 2018–2019), justamente na carteira de 2017–2021 que será pontuada. Testadas e descartadas na validação de 2015: `fracao_concedida` e as colunas de orçamento (`DECISOES.md`, seção 5).

## 7. Valores especiais e qualidade

- `-1` nas colunas de código significa "sem informação" e vira NULL. O valor `0` é mantido; confirmar no dicionário o que ele significa em cada coluna.
- Datas anteriores a 2000 (como `0001-01-01`) viram NULL. `n_dependentes` "10Plus" vira 10.
- **Juros acima de 100% ao ano são legítimos** (Espanha 2.738 contratos, Finlândia 143, em 2016–2018; máximo de 264%). Não remover.
- Idade menor que 18 (53 contratos, 48 deles com idade 0) e renda zero (64 contratos): regras de validação no pandera. **[JULGADO DEFINIDO]** Marcar, sem excluir da base de modelagem: idade e gênero não são variáveis do modelo, a renda zero vira vazio (`DECISOES.md`, seção 5) e os grupos de idade da auditoria (18–25 e 35–44) já deixam os menores de 18 de fora.
- Outros alertas, para registrar no relatório de qualidade sem falhar o teste: `valor_concedido` maior que `valor_solicitado` (249 contratos), `prazo_meses` menor que 3 (221; o mínimo é 1), vencimento original diferente de concessão mais prazo em mais de 2 meses (133), `Current` com `data_default` (163) e `caixa_livre` negativo (23).
- **Zeros no lugar de vazio:** `divida_renda`, `caixa_livre` e `renda_empregador_principal` têm 100% de zeros a partir de 2018 (70% a 72% em 2017). A carga não os pega, porque só troca `-1` por NULL. Ver a seção 6.
- Gênero 2 ("indefinido") é quase só da Espanha (12.164 de 12.180; cerca de 46% dos contratos espanhóis). Na auditoria, tratar como dado ausente e comparar só 0 e 1, de preferência dentro de cada país.
- **Codificação do gênero em 2017–2019:** entre os contratos com gênero 0 ou 1, a proporção de mulheres na Estônia vai de 45% em 2016 para 26% em 2017 e 9% em 2018, e volta a 34% em 2019 e 51% em 2020 (Finlândia: 45%, 21%, 23%, 41% e 51%). Além disso, 5.633 clientes aparecem com os dois valores em contratos diferentes, e a idade deles é coerente entre os contratos (0 incoerências em 94.148 pares), ou seja, é a mesma pessoa. É um indício de erro de codificação nesse período; o dicionário do Bondora não o confirma. Gênero fica fora do treino e do teste, então o modelo não é afetado; a análise de gênero será apresentada ao final como achado, com essa ressalva.
- **[A CONFIRMAR]** `score_es_microl` tem o valor "M" em cerca de 136 mil linhas; confirmar o significado no dicionário.
- **[A CONFIRMAR]** `novo_cliente` e `n_emprestimos_anteriores` parecem medir coisas diferentes: 15.668 contratos têm `novo_cliente` verdadeiro e empréstimos anteriores, e 303 têm o caso oposto. Confirmar no dicionário antes de validar uma contra a outra.

## 8. Moeda e unidades

- **Valores em euro**, com uma exceção: a renda e os passivos dos contratos **da Estônia concedidos até 31/12/2010** vinham em coroas estonianas (EEK). A carga os converte para euros (÷ 15,6466; `src/dados/moeda.py`), e o treino faz o mesmo ao ler o CSV. Evidências: a renda mediana vai de 12.000 (dez/2010) para 860 (jan/2011), e o valor pedido de 2009–2010 multiplicado por 15,6466 dá um número redondo de coroas em 100% dos contratos. São 1.822 contratos, todos da Estônia.
- **Juros em % ao ano, como taxa nominal.** A taxa mensal do contrato é `juro_aa ÷ 12`. Conferido na parcela: com `juro_aa ÷ 12` o erro mediano é de 2,6% nos contratos acima de 100% ao ano, contra 36,6% com a equivalência composta, (1 + i)^(1/12) − 1.
- **A taxa do BC (série 20742) é efetiva.** O "% ao ano" dela é a composição das taxas mensais: 6,42% ao mês correspondem a 110,95% ao ano. A etiqueta é a mesma, e a convenção é outra.
- **Conversão para comparar** (feita pelo código do parecer, nunca no banco):

  | De | Para | Fórmula |
  | --- | --- | --- |
  | efetiva a.a. (BC) | nominal a.a. (como o contrato) | 12 × [(1 + efetiva)^(1/12) − 1] |
  | efetiva a.a. | taxa ao mês | (1 + efetiva)^(1/12) − 1 |
  | nominal a.a. | efetiva a.a. | (1 + nominal ÷ 12)^12 − 1 |

  Exemplo (concessão em mar/2016): 126,2% efetiva = 84,5% nominal = 7,04% ao mês.

## 9. Fontes externas

- **Euribor (Portal de dados do BCE, data.ecb.europa.eu)** **[DEFINIDO]**:
  - Principal: Euribor de 12 meses, série mensal, média das observações do mês (`FM.M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA`).
  - Sensibilidade: Euribor de 3 meses, mesma frequência (`FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA`).
  - Período: 01/2009 a 07/2021 (concessões de 28/02/2009 a 19/07/2021). Baixar a série completa e recortar depois.
  - Junção: mês de `data_emprestimo` com o mês da série. Os valores negativos (de 2015–2016 em diante) ficam como vêm na tabela; a fórmula do preço usa piso em zero (`DECISOES.md`, seção 8).
  - Limitação: a Euribor tem no máximo 12 meses, e a mediana do prazo dos contratos é de 60 meses (48 meses no treino e 36 no teste).
- **Selic (Banco Central do Brasil)** **[JULGADO DEFINIDO]**: carregada no banco, mas **sem uso no motor de preço**. O motor usa só a Euribor (`DECISOES.md`, seção 8), e o documento de contextualização do grupo diz que nada é simulado; o cenário "modo Brasil" com a Selic (leitura A, que reprecificaria os contratos históricos com a Selic do mesmo mês) fica como trabalho futuro.
  - Série SGS 4189, "Selic acumulada no mês anualizada base 252": mensal, em % ao ano, 01/2009 a 07/2021.
  - Descartadas: a 4390 (% ao mês; exige anualizar e erra em meses curtos) e a meta Selic do Dados de Mercado (valor do 1º dia do mês; defasa quando a meta muda). A meta fica só como conferência da 4189.
  - Limitação: a Selic é uma taxa de um dia útil, e a Euribor principal é de 12 meses. A comparação mais justa em prazo é com a Euribor de 3 meses.
- **Tabelas no banco:** `euribor_mensal` (`mes`, `euribor_3m`, `euribor_12m`), `selic_mensal` (`mes`, `selic_aa` e `selic_meta_aa`, esta só para conferência) e a view `vw_custo_do_dinheiro`, que liga cada contrato ao mês da concessão. Esquema em `02_schema_macro.sql`; carga em `carga_macro.py`. A série 20742 vai na tabela `bc_credito_pessoal_mensal` (`mes`, `taxa_aa`), que a `carga_macro.py` carrega quando o arquivo `data/raw/bcdata.sgs.20742.csv` existe; a view traz a coluna `bc_credito_pessoal_aa`, vazia antes de 03/2011.
- **Taxas de crédito do BC (referência de mercado) [DEFINIDO]**: série SGS 20742, taxa média das novas operações de crédito pessoal não consignado para pessoas físicas, mensal, em % ao ano **efetiva**, de 03/2011 a 07/2021 (na janela, de 66,3% a 141,9% efetiva, ou de 52,0% a 91,7% nominal).
  - Uso: só contexto no painel do analista e no parecer, mostrando a taxa média do mercado brasileiro no mês da concessão de cada contrato (coluna `bc_credito_pessoal_aa` da view, em % efetiva ao ano). **Quem escreve a frase é o código, e não o LLM** **[JULGADO DEFINIDO]**: o código converte o valor para nominal (seção 8) e monta uma frase fixa, num campo próprio do parecer (`contexto_mercado`), separado do texto do LLM. O LLM não recebe o número, e o parecer não conclui "justo" ou "injusto" a partir dele; se o LLM citar uma "média do mercado", a conferência recusa o parecer. O campo é opcional: antes de 03/2011 fica vazio e a frase não aparece. Não calibra o preço e não entra no modelo.
  - Onde fica: a conversão, o campo `contexto_mercado` e os testes ficam em `genai/src/checagem.py` (Maria), com a regra em `REGRAS_PARECER.md` e o formato em `FORMATO_JSON.md`. Proposta, a combinar com a Maria: mostrar a efetiva entre parênteses, porque é a que o BC divulga e a que o CDC (art. 52) manda informar.
  - Escala: a série fica mensal, e cada contrato usa o mês da concessão. Não anualizar: a taxa varia de 8 a 37 pontos dentro de um mesmo ano, e usar a média do ano erraria, em média, 7 pontos.
  - **[DEFINIDO]** Conferência feita em 08/11/2026 contra a série mensal oficial SGS 25464 (a mesma medida, em % ao mês, desde 03/2011; baixada do portal de dados abertos do BC): nos 187 meses (125 na janela do projeto), a conversão 12 × [(1 + efetiva)^(1/12) − 1] difere da série oficial em no máximo 0,005 ponto percentual ao mês (0,06 ponto no nominal anual), que é o arredondamento de 2 casas que o BC publica. Nenhum mês passa de 0,01. Script: `src/dados/validar_conversao_bc.py`; teste: `tests/dados/test_conversao_bc.py`; figura 10 do EDA. O CSV da 25464 fica em `data/raw/` (fora do Git) e **não é carregado no banco**.
  - Cobertura: 2009 a 02/2011 ficam sem benchmark (1.894 contratos). Não emendar com a série de crédito pessoal total, que inclui o consignado.
  - O ranking de instituições de 2026 foi retirado do projeto.

## 10. Privacidade e LGPD (Lei Geral de Proteção de Dados)

- `cliente_id` é o `UserName` pseudonimizado com HMAC-SHA256 (Hash-based Message Authentication Code, hash com chave secreta), truncado em 16 caracteres.
- A chave é obrigatória (`CLIENTE_ID_SAL`, mínimo de 16 caracteres), fica no `.env`, é a mesma para todo o grupo, é compartilhada fora do Git e nunca vai ao repositório. Trocar a chave exige recarregar o banco.
- Nenhum identificador vai para os slides nem para a chamada ao LLM (Large Language Model, modelo de linguagem).
- Gênero, idade, estado civil e dependentes só são usados para auditar, nunca para decidir.
- As decisões do analista ficam registradas sem gênero nem idade (seção 13).

## 11. Limitações

- Dados estonianos, de 2009 a 2021, só de empréstimos aprovados.
- Análise jurídica hipotética ("se este contrato fosse brasileiro").
- A base de modelagem termina em 2016, e a carteira a pontuar (2017 a 2021) é 82,6% da base: o modelo será usado fora da época em que foi treinado e testado. O juro médio mudou nesse período (41,2% em 2016, 46,7% em 2017 e 31,7% em 2018, em todos os contratos).
- Só entram contratos encerrados. Os 609 de 2016 ainda em andamento ficam de fora e inflam um pouco o default de 2016.
- O teste só tem clientes novos, com default maior que o do 2016 inteiro (67,1% contra 63,1%).
- A validação por janela móvel e a comparação com e sem 2009–2012 não foram feitas, a menos que sobre tempo (resposta do Samuel).
- 2009–2012 tem só a Estônia, com default menor; o default sobe a partir de 2014, em boa parte pela entrada da Espanha e da Finlândia.
- A referência de mercado do BC (série 20742) começa em 03/2011, e os dois mercados são muito diferentes: na mesma base (nominal ao ano), a taxa média do Bondora ficou abaixo da do BC em todos os 125 meses (mediana de 0,41 da taxa do BC; cerca de 30% contra 72% ao ano), e o risco também difere (56,0% de default na base de modelagem do Bondora). Serve de contexto, não de veredito sobre preço justo.
- Excluir gênero e idade do modelo não elimina proxies (variáveis que carregam a mesma informação). É isso que a auditoria de resíduos testa.
- Gênero está muito ligado ao país (gênero indefinido é quase só da Espanha).
- A codificação do gênero parece quebrada em 2017–2019 (proporção de mulheres na Estônia: 45% em 2016, 9% em 2018, 51% em 2020; 5.633 clientes com os dois valores). Gênero fica fora do treino e do teste. A análise será apresentada ao final como achado, com essa ressalva, e é relevante para a parte de governança, ética e equidade.
- Várias colunas mudam de regime depois de 2017 (zeros no lugar de vazio e campos de histórico), então a carteira a pontuar difere da base de treino.
- Quando o grupo compara contratos "parecidos" controlando por variáveis como renda, é preciso lembrar que a renda pode ser afetada pelo próprio gênero. Registrar isso na parte de ética.

## 12. Decisões e pendências

**Fechadas** (a fonte vem entre parênteses):

- [x] **[DEFINIDO]** Reestruturados ficam no treino e no teste, sem a flag como variável, e saem só da comparação de preço da auditoria (`DECISOES.md`, seção 2).
- [x] **[DEFINIDO]** As 4 variáveis que somem depois de 2017 e as 3 com zero no lugar de vazio ficam fora do modelo (`DECISOES.md`, seção 5; há teste automático que garante).
- [x] **[DEFINIDO]** Teste de 2016 só com clientes novos; escolha de variáveis só com validação temporal dentro do treino. A janela móvel fica como limitação se não sobrar tempo (`DECISOES.md`, seção 4; resposta do Samuel).
- [x] **[DEFINIDO]** Euribor de 12 meses como principal e de 3 meses na sensibilidade (`DECISOES.md`, seção 8).
- [x] **[DEFINIDO]** Parcela ÷ renda sem juros: `valor_concedido ÷ prazo_meses ÷ renda_total` (`DECISOES.md`, seção 5).
- [x] **[DEFINIDO]** `estado_civil` e `n_dependentes` só para auditoria (`DECISOES.md`, pendências).
- [x] **[DEFINIDO]** Scores externos entram no modelo, com "sem_info" fora do próprio país (`DECISOES.md`, seção 5).
- [x] **[DEFINIDO]** `pagamentos_anteriores` e `quitacoes_antecipadas_valor` saíram do modelo em 05/11, porque mudam de regime (`DECISOES.md`, seção 5).
- [x] **[DEFINIDO]** Moeda: renda e passivos da Estônia até 2010 convertidos de coroas (÷ 15,6466), na carga e no `ler_base()` (`DECISOES.md`, seção 5; seção 8 deste documento).
- [x] **[DEFINIDO]** Equidade: gênero em 2013–2016 e dentro do país; idade de 18 a 25 contra 35 a 44 (`DECISOES.md`, pendências de 09/11).
- [x] **[DEFINIDO]** Série 20742 como referência de mercado do BC, só como contexto, com 2009 a 02/2011 sem benchmark (documento de contextualização do Samuel, 31/10; seção 9).
- [x] **[JULGADO DEFINIDO]** Selic: carregada, mas sem uso no motor; o cenário "modo Brasil" fica como trabalho futuro (seção 9). Avisar se o Samuel discordar.
- [x] **[JULGADO DEFINIDO]** Idade menor que 18 e renda zero: marcar, sem excluir da base de modelagem (seção 7).
- [x] Marcos: conversão efetiva → nominal da taxa do BC conferida contra a série mensal oficial 25464 (seção 9; sugestão da Maria).
- [x] Marcos: `vw_base_modelagem` conferida contra o `DECISOES.md` (20.011 no treino, 7.311 no teste e 2.594 fora).
- [x] Marcos: `divida_renda`, `caixa_livre` e `renda_empregador_principal` em `COLUNAS_INDISPONIVEIS_RECENTES` (`carga_bondora.py`).

**Abertas:**

- [ ] Campo da referência de mercado: desenho proposto pela Maria (campo opcional `bc_credito_pessoal_aa` na entrada e `contexto_mercado` na saída, frase escrita pelo código, conversão para nominal; seção 9). Falta a Yasmin passar o valor da view e mostrar o campo, e avisar todos da mudança de formato.
- [ ] Registro de decisões (seção 13): a Yasmin faz as rotas da API, a conexão com o banco e o uso da tabela no painel. Confirmar com ela que a justificativa é obrigatória, que as taxas vão em fração ao ano e que o JSON gravado é só a resposta do `prever()` e o parecer (sem a solicitação, que tem gênero e idade).
- [ ] Todos: quem já tem o banco montado aplica `db/05_decisoes_analista.sql` uma vez (seção 13).
- [ ] Samuel (08 e 09/11): `carteira_auditoria.csv` e `equidade.json`; o backtest do retorno realizado usa a `vw_retorno_realizado` como está, com as recuperações já dentro dos pagamentos (seção 14).
- [ ] Marcos e Samuel (14/11): ROI em euros da carteira.
- [ ] Marcos (14/11): datasheet dos dados.
- [ ] Marcos: conferir no dicionário o significado de `novo_cliente` frente a `n_emprestimos_anteriores` e o valor "M" do `score_es_microl` (seção 7).

## 13. Registro de decisões do analista

- **O que é:** a tabela `decisao_analista` (`db/05_decisoes_analista.sql`), com uma linha por decisão do analista: "Manter preço", "Revisar preço" ou "Encaminhar ao compliance". É a trilha de auditoria do projeto: o sistema apoia e o analista decide (LGPD, art. 20).
- **O que cada linha guarda:** o contrato (`contrato_id`, que na carteira é o `loan_id`), o analista, a data e a hora, a decisão, a justificativa (obrigatória), a nova taxa proposta (opcional), a recomendação do sistema, a situação do preço, os números do momento (PD, faixa, juro cobrado, juro justo e a margem, em fração ao ano), as versões do modelo e do parecer e a cópia do que o analista viu (`prever_json` e `parecer_json`).
- **Regras que o próprio banco garante:**
  - Só inclusão: `UPDATE`, `DELETE` e `TRUNCATE` são bloqueados. Para corrigir, registra-se outra decisão, e a mais recente vale (view `vw_decisao_atual`, que a fila da carteira usa para marcar "já decidido").
  - A data é sempre a do servidor, e a origem é definida pelo banco: `carteira` se o `contrato_id` existe em `emprestimo`, `simulacao` para os casos de exemplo (como `EXEMPLO-1`), que ficam fora da `vw_decisao_atual`.
  - Os domínios são fechados e iguais aos de `src/api/schemas.py` (decisão, recomendação, situação do preço, faixa e origem do parecer).
  - Revisão manual (dados fora da faixa do treino): a situação do preço é `revisao_manual` e `pd`, `faixa` e os juros justos ficam vazios, como no `prever()`, e o analista ainda decide. Fora da revisão manual esses números são obrigatórios (mesma regra do `genai/src/checagem.py`).
- **Privacidade:** não existe coluna de gênero nem de idade, e o banco recusa um JSON que tenha as chaves `genero`, `idade`, `gender` ou `age` no primeiro nível. Quem grava manda só a resposta do `prever()` e o parecer, nunca a solicitação. O analista é identificado por nome ou login, sem CPF. A justificativa é texto livre, então não deve levar dado pessoal.
- **Como aplicar:** na primeira criação do banco, os arquivos de `db/` rodam sozinhos. Em um banco já existente, aplique `db/05_decisoes_analista.sql` uma vez (os comandos estão no cabeçalho do arquivo). O teste `db/testes/05_teste_decisoes.sql` roda numa transação que é desfeita no fim.
- **Conferência:** a `src/dados/validacao.py` confere domínios, justificativa, JSON sem gênero e idade, origem coerente com a carteira e a view. O `tests/dados/test_decisoes_sql.py` amarra o SQL ao código e à API.
- **Fora desta versão:** perfis de acesso (quem lê o quê), prazo de retenção e exportação do registro.

## 14. Retorno realizado (backtest e ROI)

- **O que é:** a view `vw_retorno_realizado` (`db/04_view_retorno_realizado.sql`): por contrato da base de modelagem, quanto voltou em euros. Serve ao backtest do Samuel e ao ROI da carteira. Parte da `vw_base_modelagem`, então herda os mesmos filtros.
- **Definição:** `recebido_total = principal_pago + juros_multas_pagos`. **As recuperações já estão dentro desses dois campos** (nos defaults, `valor_concedido = principal_pago + principal_baixado + saldo_principal` fecha em 98% dos contratos): somá-las de novo inflaria o retorno médio de +2,4% para +21,7%. `resultado_eur = recebido_total − valor_concedido`; `retorno_realizado = resultado_eur ÷ valor_concedido` (nunca menor que −1); `principal_perdido` é o que não voltou; `recuperado_eur` é só informativo.
- **Primeira leitura** (2009–2016, encerrados, sem a Eslováquia): 73,0 mi € concedidos e resultado de −0,01 mi €. Por país: Estônia +6,05 mi € (+15%), Espanha −3,89 mi € (−31%) e Finlândia −2,17 mi € (−11%). Por safra, o retorno cai de +28% (2013) para −13% (2016). Reestruturados: +1,34 mi €; os demais: −1,35 mi €.
- **Limites:** não desconta o tempo; só vale para contratos encerrados (as safras de 2015 e 2016 podem ter recuperações ainda por chegar); não existe para 2017–2021.
- **Uso:** `perda_nao_coberta_eur` e `rentabilidade_realizada` do `carteira_auditoria.csv` do painel vêm desta view (`src/app/carteira.py`). Figura 7 do EDA (`notebooks/dados/01_eda.ipynb`).
