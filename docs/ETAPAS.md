# Etapas do desenvolvimento

Como o projeto foi construído, de 26/10 a 16/11/2026, na ordem em que as etapas aconteceram. Cada etapa diz o que foi feito, o que se descobriu e onde está o detalhe. Foram 273 commits e 28 pull requests, de quatro frentes: Dados e processo (Marcos), Modelo e juro justo (Samuel), GenAI (Maria) e App e infraestrutura (Yasmin).

## Linha do tempo

| Período | Etapa | Resultado principal |
| --- | --- | --- |
| até 28/10 | 1. Escolha do tema | Troca do CredFlow pelo CredFlare, com a base da Bondora |
| 26 a 29/10 | 2. Estrutura e processo | Repositório, CI, regras de trabalho e BPMN v1 |
| 28/10 a 04/11 | 3. Dados: carga, limpeza e validação | Banco com 179.235 contratos, validação automática e correção da moeda |
| 03 a 13/11 | 4. Análise exploratória | 10 figuras e os achados que mudaram o modelo |
| 31/10 a 14/11 | 5. Modelo de risco e juro justo | XGBoost v1 a v3 e juro justo por fluxo de caixa |
| 03 a 16/11 | 6. GenAI: RAG e parecer | Cadeia em LangChain, prompts v1 a v5, modelo reserva e avaliação com 20 casos |
| 28/10 a 15/11 | 7. API, painel e banco de decisões | FastAPI, Streamlit e registro de decisões no PostgreSQL |
| 10 a 15/11 | 8. Infraestrutura | Docker Compose local e Terraform na Google Cloud |
| 08 a 16/11 | 9. Auditoria, ROI e governança | Backtest, equidade, invariância e documentos para a banca |

## 1. Escolha do tema

- **Primeira ideia:** o CredFlow, sobre portabilidade de crédito via Open Finance, com a base Berka e taxas do Banco Central. A base não tinha juro por contrato, e a taxa teria de ser simulada.
- **Troca:** o grupo passou para o CredFlare, que pergunta se o juro cobrado de cada contrato acompanha o risco. A base Bondora tem contratos reais, com juro, desfecho e perfil do cliente.
- **Enquadramento:** não existe base pública brasileira com contratos individuais. Os dados europeus são usados como substituto, e o parecer aplica a lei brasileira "como se o contrato fosse de um banco brasileiro".
- Onde está: `README.md` (Enquadramento) e o plano do projeto.

## 2. Estrutura e processo

- Repositório com uma pasta por frente, CI no GitHub Actions desde 27/10 e a regra de que cada frente é dona dos seus arquivos. Mudança em contrato entre frentes (tabelas, formato do `prever()`, formato do parecer) só com aviso ao grupo.
- O processo de negócio foi desenhado em BPMN 2.0 e evoluiu com o produto: v1 (29/10), v2 com dois participantes, v3 e v4 (15/11) com a busca por contrato, a revisão manual, o registro da decisão e o teste de invariância.
- A primeira carga da Bondora entrou em 28/10.
- O desenvolvimento usou assistentes de IA, guiados por skills por setor (`skills/`).
- Onde está: `docs/bpmn/`, `skills/README.md` e `.github/workflows/ci.yml`.

## 3. Dados: carga, limpeza e validação

1. **Esquema:** três tabelas ligadas por `loan_id` (`emprestimo`, `cliente`, `historico_credito`), com cada coluna marcada como lista negra (pós-concessão, nunca entra no modelo), só auditoria (gênero, idade, estado civil, dependentes) ou disponível. DER em `docs/der/`.
2. **Carga:** `src/dados/carga_bondora.py` troca códigos -1 por vazio, datas inválidas por vazio e pseudonimiza o cliente com HMAC-SHA256.
3. **Séries externas:** Euribor de 3 e 12 meses (BCE), Selic e a taxa do crédito pessoal do BC (série 20742), por mês (`src/dados/carga_macro.py`).
4. **Validação:** regras com pandera, separadas em erro (quebra o contrato dos dados) e alerta (ocorrência conhecida). Resultado: 0 erros e 12 alertas, publicados em `docs/qualidade_dados.md`.
5. **Achados e correções:**
    - A renda e os passivos da Estônia até 2010 estavam em coroas estonianas. A renda mediana caía de 12.000 para 860 na virada para o euro. Foram convertidos em 1.822 contratos (`src/dados/moeda.py`).
    - O gênero foi codificado errado de 2017 a 2019 (a proporção de mulheres na Estônia cai de 45% para 9% e volta a 51%). A auditoria de gênero usa só 2013 a 2016.
    - Sete colunas ficam vazias ou zeradas a partir de 2018 e saíram do modelo.
    - Em 2017, dois scores de bureau mudam de escala. Os valores novos passaram a valer "sem informação" (repontuação de 14/11).
    - O juro da Bondora é taxa nominal; o do BC é efetiva. A conversão foi validada contra a série mensal oficial do BC, com diferença máxima de 0,005 ponto ao mês.
- Onde está: `DATA.md`, `docs/datasheet.md` e `docs/qualidade_dados.md`.

## 4. Análise exploratória

- O notebook `notebooks/dados/01_eda.ipynb` gera as 10 figuras de `docs/figuras/`: inadimplência por ano e país, juro por época e rating, renda, juro contra inadimplência, codificação do gênero, correção da moeda, retorno realizado, equidade, carteira auditada e validação da taxa do BC.
- Achados que mudaram decisões:
    - A inadimplência média é de 56%, e varia muito por país (Estônia 42%, Finlândia 73%, Espanha 78%). Por isso o país entra no modelo como controle.
    - Na Espanha, o juro cobrado varia bastante e a inadimplência quase não muda (73% a 87%): o preço não separa o risco.
    - A carteira de 2009 a 2016 devolveu praticamente o que emprestou (−0,01 mi € em 73,0 mi €): lucro na Estônia, prejuízo na Espanha e na Finlândia.

## 5. Modelo de risco e juro justo

1. **Recorte e divisão:** contratos encerrados de 2009 a 2016 (`vw_base_modelagem`); treino até 2015 e teste em 2016 só com clientes novos (7.311 contratos), para simular o uso no futuro.
2. **Linha de base:** regressão logística, AUC 0,70 no teste.
3. **XGBoost v1 e v2 (01/11):** AUC 0,73.
4. **XGBoost v3 (05/11):** retreino com as coroas corrigidas e 21 variáveis, sem as duas que mudavam de regime. AUC 0,72, KS 0,33. A pequena perda de AUC troca um ganho artificial por um modelo que vale na carteira de 2017 a 2021.
5. **Juro justo:** fluxo de caixa com o custo do dinheiro (Euribor de 12 meses), a perda esperada e uma margem de incerteza por bootstrap (20 reamostras). A mediana do juro de contratos parecidos ficou como segunda opinião, porque usá-la como régua seria circular.
6. **Lote:** a carteira inteira (157.883 contratos) é pontuada de uma vez e gravada em `docs/resultados/carteira_auditoria.csv`.
- Onde está: `docs/DECISOES.md`, `src/modelos/` e `docs/resultados/`.

## 6. GenAI: RAG e parecer

1. **Contrato antes do código:** `genai/FORMATO_JSON.md` e `genai/REGRAS_PARECER.md` definem o que entra no LLM e o que sai.
2. **Corpus:** cinco documentos oficiais (LGPD, CDC, Resoluções CMN 4.881 e 5.004 e o Relatório de Estabilidade Financeira do BC), divididos em trechos de até 1.000 caracteres e indexados no pgvector com embeddings multilíngues de 384 dimensões.
3. **Critérios antes dos resultados (03/11):** 20 casos de avaliação com a resposta esperada escrita antes da execução (`genai/avaliacao/CRITERIOS.md`).
4. **Cadeia:** LangChain (LCEL) em quatro passos: busca nas normas, montagem do prompt, Gemini Flash-Lite com saída estruturada e conferência de números e fontes. Sem memória entre pareceres. Se o LLM falha ou a conferência recusa, sai um parecer por regras.
5. **Prompts v1 a v4 (05 a 09/11):** cada versão corrigiu o que a avaliação mostrou. Na v4: recomendação certa em 100% dos casos, 97% dos pareceres aprovados pela conferência e nenhuma palavra proibida. Revisão humana feita em 10/11.
6. **Modelo reserva e prompt v5 (16/11):** quando o Gemini responde 503, um segundo modelo assume antes do template; a v5 faz o "acima do justo" citar o CDC sobre a informação do preço (10 de 10 casos).
- Onde está: `genai/` e o documento para a banca (`docs/CredFlare.pdf`).

## 7. API, painel e banco de decisões

- **API (FastAPI):** rotas de previsão, parecer, carteira, busca por contrato, cenário (Laboratório), teste de invariância e decisões.
- **Painel (Streamlit):** começou com um formulário e foi refeito em 13 e 14/11 a partir dos protótipos: busca do contrato pelo ID, análise ao vivo, Laboratório para testar cenários, Auditoria da carteira e registro de decisões.
- **Banco de decisões (06/11):** a tabela `decisao_analista` guarda cada decisão com justificativa, números do momento e versões, sem gênero nem idade. Gatilhos impedem alterar ou apagar.
- **Plano B:** se o cálculo ao vivo falhar, a tela usa os valores do lote, com aviso.
- **Testes:** cerca de 335 funções de teste automático, rodando no CI a cada pull request.
- Onde está: `docs/APP_E_INFRA.md`, `src/api/`, `src/app/` e `db/05_decisoes_analista.sql`.

## 8. Infraestrutura

- **Local:** Docker Compose sobe o PostgreSQL com pgvector, a API e o painel; os arquivos de `db/` rodam sozinhos na primeira criação do banco. O `iniciar.ps1` faz tudo com um comando no Windows.
- **Nuvem:** Terraform cria cinco recursos na Google Cloud, com uma VM que roda o mesmo Docker Compose.
- Onde está: `docker-compose.yml`, `iniciar.ps1` e `infra/README.md`.

## 9. Auditoria, ROI e governança

- **Backtest de 2016:** os contratos "acima do justo" tiveram o pior retorno (−22,7%) e os "abaixo", o melhor (−9,2%). A hipótese só vale nas faixas de risco B e C. O resultado é apresentado como indício, e a decisão é sempre do analista.
- **ROI:** 5,59 mi € de perda não coberta em 2016 e 44,3 mi € de excesso estimado acima da margem em 2017 a 2021 (`src/dados/roi_backtest.py`).
- **Equidade:** a risco igual, jovens de 18 a 25 anos pagam +5,45 pontos percentuais a mais que os de 35 a 44.
- **Invariância:** trocando gênero e idade em 500 contratos, 500 deram resultado idêntico.
- **Documentos:** datasheet dos dados, glossário, roteiro da demo e o documento de justificativas para a banca.

## O que mudou o rumo

| Momento | O que aconteceu | Decisão |
| --- | --- | --- |
| Até 28/10 | A base do CredFlow não tinha juro por contrato | Trocar de tema e de base |
| 04/11 | Renda da Estônia em coroas até 2010 | Converter na carga e retreinar (v3) |
| 05/11 | Colunas que mudam de regime depois de 2017 | Tirar do modelo, mesmo perdendo um pouco de AUC |
| 06/11 | Decisões do analista sumiam ao fechar a aba | Criar a tabela `decisao_analista` |
| 14/11 | Scores de bureau com escala nova em 2017 | Tratar como "sem informação" e repontuar a carteira |
| 15/11 | O backtest não confirma a auditoria no agregado | Apresentar como indício e propor calibração por safra |
