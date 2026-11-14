# Datasheet dos dados · Auditor de Preço Justo

> Versão 1.0 · 13/11/2026 · Responsável: Marcos (Dados e processo)
> Ficha do conjunto de dados no formato *Datasheets for Datasets* (Gebru et al.): motivação, composição, coleta, pré-processamento, usos, distribuição e manutenção.
> Os números saem do banco (`auditor_db`, carga completa) e do relatório [`docs/qualidade_dados.md`](qualidade_dados.md), gerado em 13/11/2026. As regras detalhadas estão no [`DATA.md`](../DATA.md); as decisões de modelagem, no [`docs/DECISOES.md`](DECISOES.md).

---

## 1. Motivação

- **Para que o conjunto existe:** auditar se o juro cobrado em crédito pessoal é justo para o risco de cada contrato. O sistema estima a probabilidade de default (PD), calcula um juro justo e compara com o juro cobrado; o analista decide e registra a decisão.
- **Por que estes dados:** não há base pública brasileira de crédito pessoal com contrato, cliente e desfecho no nível do contrato. O livro de empréstimos do Bondora é real, público e tem o desfecho de cada contrato. Ele é usado "como se fosse de um banco brasileiro", e nada é simulado.
- **Quem montou:** a frente de Dados do projeto (Marcos), a partir dos arquivos públicos do Bondora, do Banco Central do Brasil e do Banco Central Europeu.
- **Financiamento:** projeto acadêmico do bootcamp, sem financiamento externo.

## 2. Composição

### O que cada linha representa

Um **contrato de empréstimo pessoal** concedido pelo Bondora, dividido em três tabelas ligadas por `loan_id` (uma linha por contrato em cada uma):

| Tabela | Colunas | Conteúdo |
| --- | --- | --- |
| `emprestimo` | 39 | Pedido, valores, prazo, juro, datas, situação e pagamentos |
| `cliente` | 21 | Perfil do tomador (renda, moradia, escolaridade, país), com `cliente_id` pseudonimizado |
| `historico_credito` | 15 | Passivos, empréstimos anteriores na plataforma e scores de bureau |

Além delas, três séries mensais de apoio: `euribor_mensal` (custo do dinheiro), `selic_mensal` (carregada, sem uso no motor) e `bc_credito_pessoal_mensal` (referência de mercado brasileira, só contexto).

### Tamanho e cobertura

- **179.235 contratos**, concedidos de 28/02/2009 a 19/07/2021, com corte em 20/07/2021. Total concedido: 455,9 mi €.
- **85.087 clientes**; 36.185 deles têm mais de um contrato.
- Valor mediano de 2.125 €, prazo mediano de 60 meses e juro mediano de 30,0% ao ano (nominal).

| País | Contratos | % | Concedidos de 2017 em diante |
| --- | --- | --- | --- |
| Estônia (EE) | 110.714 | 61,8% | 92.098 |
| Finlândia (FI) | 41.955 | 23,4% | 36.109 |
| Espanha (ES) | 26.270 | 14,7% | 19.771 |
| Eslováquia (SK) | 296 | 0,2% | 0 |

| Ano | Contratos | Ano | Contratos |
| --- | --- | --- | --- |
| 2009 | 665 | 2016 | 10.514 |
| 2010 | 1.157 | 2017 | 17.933 |
| 2011 | 451 | 2018 | 25.103 |
| 2012 | 457 | 2019 | 55.839 |
| 2013 | 2.512 | 2020 | 27.519 |
| 2014 | 7.455 | 2021 | 21.584 |
| 2015 | 8.046 | **Total** | **179.235** |

- 2009–2012 tem só a Estônia; Espanha e Finlândia entram em 2013–2014.
- É uma **amostra de contratos aprovados**: os pedidos recusados não estão na base (viés de seleção; ver a seção 5).

### Rótulo (alvo)

`inadimplente = 1` quando `data_default` está preenchida (o Bondora registra a data quando o atraso passa de 60 dias). Situação no corte:

| `status` | Contratos | Com `data_default` |
| --- | --- | --- |
| `Late` | 68.574 | 60.510 |
| `Current` | 57.774 | 163 |
| `Repaid` | 52.887 | 10.743 |

### Subconjuntos usados

- **Base de modelagem** (`vw_base_modelagem`): concessões de 2009 a 2016, encerradas (`Repaid` ou com default), sem a Eslováquia. **29.916 contratos, 56,0% de default** (Estônia 42,5%, Espanha 77,5%, Finlândia 73,2%).
  - Treino 2009–2015: 20.011 (52,4% de default) · teste 2016, só clientes novos: 7.311 (67,1%) · fora do teste por cliente repetido: 2.594.
- **Carteira a pontuar:** 2017 a 2021, 147.978 contratos (82,6% da base), ainda sem desfecho suficiente.
- **Desfecho por contrato** (`vw_desfecho_contrato`, PR #75): os 179.235 contratos, com desfecho para os 29.916 da base de modelagem e o motivo para os demais.

### Dados sensíveis

- **Pessoais e protegidos:** `genero`, `idade`, `estado_civil` e `n_dependentes` ficam no banco **só para a auditoria de equidade**. Nunca entram no modelo nem nas views lidas pela API, e não são gravados no registro de decisões.
- **Identificadores:** o nome de usuário do Bondora vira `cliente_id`, pseudonimizado com HMAC-SHA256 e chave secreta fora do Git. A data de nascimento, a cidade e o condado do CSV **não são carregados**.
- Não há nome, documento, endereço nem contato de pessoas.

### Erros, ruído e lacunas conhecidos

Do relatório de qualidade de 13/11/2026: **0 erros e 12 alertas**. Os principais:

| Alerta | Contratos |
| --- | --- |
| `parcela_mensal` menor ou igual a zero (coluna da lista negra) | 3.627 |
| `prazo_meses` menor que 3 | 221 |
| `valor_concedido` maior que `valor_solicitado` | 208 |
| `Current` com `data_default` | 163 |
| Vencimento original diferente de concessão + prazo (mais de 2 meses) | 133 |
| `renda_total` igual a zero | 64 |
| `idade` menor que 18 | 53 |

Mudanças de regime a partir de 2017, que afetam a carteira:

- `divida_renda`, `caixa_livre` e `renda_empregador_principal` passam a ter zero no lugar de vazio (70% a 72% em 2017; 100% de 2018 em diante).
- `finalidade`, `situacao_emprego`, `area_ocupacao` e `experiencia_trabalho` ficam em branco (70% em 2017; 100% de 2018 em diante).
- `score_es_microl` ganha o valor "M" (sem nota; 136.415 contratos, sobretudo da Estônia e da Finlândia), e `score_fi_asiakastieto` muda para uma escala de 1 a 8 (35.410 contratos).
- A codificação do gênero parece quebrada em 2017–2019 (proporção de mulheres na Estônia: 45% em 2016, 9% em 2018 e 51% em 2020).

## 3. Coleta

| Fonte | O que é | Período | Onde fica |
| --- | --- | --- | --- |
| **Bondora Public Reports**, "Loan dataset" (LoanData) | Livro de empréstimos da plataforma estoniana de crédito entre pessoas: 179.235 linhas e 112 colunas | concessões de 02/2009 a 07/2021; corte em 20/07/2021 | `data/raw/LoanData_Bondora.csv` |
| **Banco Central Europeu**, Portal de dados | Euribor de 12 meses (principal) e de 3 meses (sensibilidade), média mensal | 01/1994 a 09/2026 no banco; o projeto usa 01/2009 a 07/2021 | `euribor_mensal` |
| **Banco Central do Brasil**, SGS 4189 | Selic acumulada no mês, anualizada (base 252) | 08/1986 a 11/2026 no banco | `selic_mensal` |
| **Banco Central do Brasil**, SGS 20742 | Taxa média de crédito pessoal não consignado (efetiva ao ano) | 03/2011 a 09/2026 | `bc_credito_pessoal_mensal` |

- **Como foi coletado pelo Bondora:** dados operacionais da plataforma, registrados no pedido, na concessão e ao longo da vida do contrato. Parte das colunas é **pós-concessão** (pagamentos, atrasos, recuperações) e parte é **saída dos modelos do próprio Bondora** (rating, PD, perda esperada).
- **Consentimento:** os dados foram publicados pelo Bondora como relatório público; os tomadores não foram contatados pelo projeto.
- **Dicionário de dados:** Public Reports do Bondora, consultado em 28/10/2026.

## 4. Pré-processamento

Feito na carga (`src/dados/carga_bondora.py` e `src/dados/carga_macro.py`), com o esquema em `db/01` e `db/02`:

- **Seleção de colunas:** 73 das 112 colunas do CSV são carregadas. As 39 restantes ficam de fora por minimização ou por não terem uso (por exemplo, `DateOfBirth`, `City`, `County`, detalhes de lances e cronogramas de pagamento).
- **Nomes:** as colunas ganham nomes em português (o `DATA.md`, seção 6, lista todas). O `loan_id` é gravado em minúsculas.
- **Pseudonimização:** `UserName` vira `cliente_id` com HMAC-SHA256, truncado em 16 caracteres.
- **Valores especiais:** `-1` nas colunas de código vira vazio; datas anteriores a 2000 (como `0001-01-01`) viram vazio; `n_dependentes` "10Plus" vira 10.
- **Moeda:** a renda e os passivos da Estônia até 31/12/2010 vinham em coroas estonianas e são convertidos para euro (÷ 15,6466; 1.822 contratos).
- **Mantidos como vêm:** juros acima de 100% ao ano (são legítimos) e os zeros no lugar de vazio a partir de 2017, que ficam fora do modelo em vez de serem alterados.
- **Views:** `vw_base_modelagem` (recorte e divisão treino e teste), `vw_retorno_realizado` (resultado em euros), `vw_custo_do_dinheiro` (Euribor e taxa do BC do mês da concessão), `vw_desfecho_contrato` (desfecho ou motivo) e `vw_decisao_atual` (última decisão do analista).
- **Validação:** `src/dados/validacao.py` (pandera) confere chaves, domínios, datas, faixas, contagens e cruzamentos entre tabelas. O relatório de qualidade registra os alertas.
- **Dados brutos:** o CSV original fica intacto em `data/raw/`, e a carga pode ser refeita a partir dele.

## 5. Usos

### Usos previstos (feitos no projeto)

- Treinar e testar o modelo de PD (base de modelagem, 2009–2016).
- Calcular o juro justo e auditar o preço da carteira de 2017–2021.
- Backtest e ROI em euros com o retorno realizado (2009–2016).
- Auditoria de equidade por gênero (2013–2016, dentro do país) e por idade (18 a 25 contra 35 a 44).
- Mostrar ao analista o contrato, o desfecho e a referência de mercado na tela de análise.

### Usos que não devem ser feitos

- **Decidir crédito de pessoas reais.** O modelo foi treinado com contratos aprovados de 2009 a 2015, de outro país e outra época.
- **Usar gênero, idade, estado civil ou dependentes para prever risco ou definir preço.**
- **Tirar conclusões sobre gênero em 2017–2019** sem a ressalva da codificação quebrada.
- **Comparar diretamente o juro do Bondora com a taxa do BC** como veredito de preço justo: os mercados e o risco são muito diferentes, e a taxa do BC é só contexto.
- **Medir retorno ou default de contratos de 2017 em diante** como se estivessem encerrados.

### Riscos e limitações

- **Viés de seleção:** só há contratos aprovados; o risco de quem foi recusado não aparece.
- **Mudança de época:** a carteira (2017–2021) é 82,6% da base e difere do treino (colunas que somem, scores com escala nova, juro médio de 41,2% em 2016, 46,7% em 2017 e 31,7% em 2018).
- **Teste mais arriscado que o treino:** 67,1% de default contra 52,4%, porque só tem clientes novos.
- **Proxies:** tirar gênero e idade do modelo não elimina variáveis que carregam a mesma informação; a auditoria de resíduos testa isso.
- **Leitura jurídica hipotética:** a análise trata os contratos "como se fossem brasileiros".

## 6. Distribuição

- **O CSV do Bondora não é redistribuído.** O Bondora descreve o livro de empréstimos como público, mas não encontramos uma licença explícita; por isso `data/raw/` fica fora do Git e a fonte é citada no README.
- **Séries do BC:** portal de dados abertos do BC, licença Open Data Commons ODbL (conferida na página da série 25464). **Euribor:** Portal de dados do BCE, citado como fonte.
- **O que está no repositório:** o esquema e as views (`db/`), os scripts de carga e validação, o relatório de qualidade e os resultados em `docs/resultados/`. Entre eles, o `carteira_auditoria.csv` tem uma linha por contrato da carteira auditada (157.883 linhas), com `contrato_id`, ano, país, valores, PD, juro justo e situação do preço, **sem** gênero, idade, estado civil, dependentes ou `cliente_id`. O banco é montado localmente (Docker) a partir dos arquivos de `data/raw/`.
- **Chave de pseudonimização:** `CLIENTE_ID_SAL`, compartilhada só dentro do grupo e fora do Git.

## 7. Manutenção

- **Responsável:** Marcos (frente de Dados). Dúvidas e correções: issue no repositório ou mensagem ao grupo.
- **Versão dos dados:** o arquivo é identificado pela impressão digital SHA-256 registrada no `DATA.md`, seção 1. **[A CONFIRMAR]** A cópia local do Marcos (mesmas 112 colunas e 179.235 linhas, contagens por ano iguais às esperadas) tem SHA-256 `465abbefd71dc58afa5f293fdbff5a0300aa6cd43c6bd5736edad4c5c31fa460`, diferente do registrado. Conferir com o grupo qual cópia gerou o hash do `DATA.md` antes de fechar a versão.
- **Atualização:** o Bondora publica novas versões do relatório; o projeto **congela** a versão com corte em 20/07/2021. Uma versão nova exige recarregar o banco, reaplicar `db/`, rodar `python src/dados/validacao.py` (0 erros) e regerar `python src/dados/relatorio_qualidade.py`, além de atualizar este datasheet e o `DATA.md`.
- **Erros encontrados:** viram regra no `validacao.py` (erro ou alerta) e linha no relatório de qualidade; decisões sobre eles ficam no `DATA.md`, seção 12.
- **Pendência conhecida:** repontuar a carteira de 2017–2021 tratando a escala nova do `score_fi_asiakastieto` e o "M" do `score_es_microl` (Samuel; `DATA.md`, seção 12).
