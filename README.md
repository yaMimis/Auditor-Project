# Auditor de Preço Justo

Projeto integrador do bootcamp de IA aplicada (segmento BFSI, TCS). Para cada contrato de crédito, o sistema estima o risco de inadimplência, diz se o juro cobrado é justo para esse risco e verifica se clientes com o mesmo risco pagam juros diferentes por gênero ou idade (país entra no modelo como controle, não como grupo auditado). Um parecer gerado por IA, apoiado em normas brasileiras, explica o resultado ao analista, que decide.

Status: em desenvolvimento. Entrega dos arquivos em 19/11/2026 e apresentação em 21/11/2026.

## Enquadramento

- O produto é pensado para o mercado brasileiro. Como não existe base pública brasileira com contratos individuais, usamos os dados reais da plataforma estoniana Bondora (2009 a 2021) como substituto do comportamento de crédito.
- O motor de risco e de preço usa o contexto da época de cada contrato (Euribor).
- O parecer segue a LGPD, o CDC e as normas do Banco Central, em modo hipotético: "se este contrato fosse de um banco brasileiro".

## Dados: fonte, licença e premissas

- **Fonte:** Bondora Public Reports, arquivo "Loan dataset" (LoanData): 179.235 contratos de 2009 a 2021, com corte em 20/07/2021 (impressão digital do arquivo no `DATA.md`). A Bondora descreve esse livro de empréstimos como público e disponível para qualquer pessoa, mas **não encontramos uma licença explícita**. Por isso o CSV não é redistribuído neste repositório (`data/raw/` fica fora do Git) e a fonte é citada aqui.
- **Séries do BC e do BCE:** a Selic e as taxas de crédito do Banco Central vêm do portal de dados abertos do BC, que informa a licença Open Data Commons ODbL (conferida na página da série 25464). A Euribor vem do Portal de dados do BCE. Os CSVs ficam em `data/raw/`, fora do Git.
- **Premissas declaradas:**
  - A base é real e europeia (Estônia, Espanha e Finlândia), usada "como se fosse de um banco brasileiro". Nenhum número foi simulado.
  - Os valores estão em euro, com uma exceção: a renda e os passivos da Estônia até 2010 vinham em coroas e foram convertidos (÷ 15,6466).
  - Os juros estão em % ao ano, como taxa **nominal** (a mensal é a anual ÷ 12). A taxa do BC é efetiva e aparece só como contexto, convertida para nominal; a conversão foi conferida contra a série mensal oficial do BC (SGS 25464), com diferença máxima de 0,005 ponto percentual ao mês.
  - O período é outro (2009–2021), e o modelo usa só contratos encerrados de 2009 a 2016.
- **Colunas por grupo** (regras completas no [`DATA.md`](DATA.md), seção 6):

| Grupo | Colunas | Regra |
| --- | --- | --- |
| Variáveis do modelo | 21 | Pedido, renda e dívidas, perfil, histórico e scores de bureau (`docs/DECISOES.md`, seção 5) |
| Lista negra | 26 | Pós-concessão ou saídas do Bondora; nunca entram como variável (há teste automático) |
| Só auditoria | 4 | `genero`, `idade`, `estado_civil` e `n_dependentes`: auditam, nunca decidem |
| Indisponíveis depois de 2017 | 7 | Em branco ou zeradas na carteira de 2017–2021; fora do modelo |

## Arquitetura

Contrato → modelo de risco (PD, probabilidade de default) → juro justo por fluxo de caixa → comparação com o juro cobrado → busca das normas (RAG, geração aumentada por recuperação) → parecer em JSON → checagem dos números contra a API → painel do analista → decisão humana.

| Camada | Tecnologias |
| --- | --- |
| Dados | pandas, pandera, PostgreSQL, SQLAlchemy |
| Vetores | pgvector, no mesmo PostgreSQL |
| Modelo | scikit-learn, XGBoost, SHAP, scipy |
| Parecer | Gemini (`google-genai`), sentence-transformers multilíngue, prompts versionados |
| Serviço e app | FastAPI, Streamlit |
| Infra e qualidade | Docker Compose, pytest, black, flake8, GitHub Actions |

## Estrutura

```
data/raw/     arquivos de dados (fora do Git)
db/           esquemas SQL; rodam sozinhos na primeira criação do banco
docs/         decisões de modelagem (DECISOES.md), glossário, BPMN, resultados
genai/        formato JSON, regras, normas, prompts e código do parecer
notebooks/    EDA e etapas do modelo (coortes, variáveis, XGBoost, LGD, margem)
src/api/      API FastAPI
src/app/      painel Streamlit
src/dados/    cargas do Bondora e das séries de juros
src/modelos/  modelo de risco e juro justo (prever())
modelos_salvos/  pacote do modelo (.joblib, fora do Git)
skills/       guia do projeto por setor, para pessoas e para IA
tests/        testes
```

## Como rodar

Pré-requisitos: Git, Python 3.14 e Docker Desktop.

1. Clone o repositório e instale as dependências:
   ```
   git clone https://github.com/yaMimis/Auditor-Project.git
   cd Auditor-Project
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements-dev.txt
   ```
   No Mac ou Linux, ative com `source .venv/bin/activate`.

2. **Dados.** Todos os arquivos ficam numa pasta compartilhada do Drive, fora do Git (o repositório é público). Peça o link ao grupo e coloque os arquivos em `data/raw/`, com estes nomes:
   - `LoanData_Bondora.csv` (confira o SHA-256 em `DATA.md`)
   - `ECB_Euribor_Serie-Mensal-12-Meses_csv.csv` e `ECB_Euribor_Serie-Mensal-3-Meses.csv`
   - `BC-Selic_Acumulada_Mes_Anuzalizada_base252.csv`
   - `BC-Meta_Selic_Mensal.csv` (opcional, só conferência)
   - `bcdata.sgs.20742.csv` (opcional, referência de mercado do BC)
   - `bcdata.sgs.25464.csv` (opcional, só para conferir a conversão da taxa do BC: `python src/dados/validar_conversao_bc.py`)

3. **Configuração.** Crie um `.env` na raiz, que nunca vai ao Git:
   ```
   CLIENTE_ID_SAL=<chave de pelo menos 16 caracteres, a mesma para todo o grupo>
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/auditor_db
   ```
   A chave pseudonimiza o `cliente_id`; peça-a ao grupo. Se a porta 5432 estiver ocupada, use um `docker-compose.override.yml` local com a porta 5433 e ajuste a URL.

4. **Banco.** Suba o PostgreSQL com pgvector:
   ```
   docker compose up -d postgres
   ```
   Na primeira criação, os arquivos de `db/` rodam sozinhos e criam a extensão, as tabelas e as views. Em um banco já existente, aplique-os à mão ou use `--ddl` nas cargas.

5. **Carga**, nesta ordem:
   ```
   python src/dados/carga_bondora.py --csv data/raw/LoanData_Bondora.csv
   python src/dados/carga_macro.py
   ```
   Esperado: 179.235 contratos e 85.087 clientes distintos.

6. **API e painel.** Coloque `pacote_prever_v1.joblib` em `modelos_salvos/` (fora do Git; peça ao Samuel) e suba:
   ```
   docker compose up --build api streamlit
   ```
   - Painel: http://localhost:8501 (sem o modelo, use os exemplos da aba de revisão)
   - API: http://localhost:8000/docs (`GET /` informa se o modelo foi carregado)
   - Para os dados da carteira, o painel lê `docs/resultados/carteira_auditoria.csv` e `equidade.json`.

7. **Parecer com IA (GenAI).** Instale as dependências da frente e crie a sua chave do Gemini em [aistudio.google.com](https://aistudio.google.com/api-keys) (nível gratuito; contas de instituição podem não ter o nível gratuito, então prefira um Gmail pessoal):
   ```
   pip install -r requirements-genai.txt
   ```
   Acrescente ao `.env` (nunca vai ao Git):
   ```
   GOOGLE_API_KEY=<sua chave>
   MODELO_LLM=gemini-3.5-flash-lite   # opcional; plano B: gemini-3.1-flash-lite
   ```
   Com o banco no ar (passo 4), indexe as normas e teste a busca:
   ```
   python genai/src/indexar.py
   python genai/src/testar_busca.py
   ```
   Esperado: 91 trechos indexados e 8 de 10 perguntas com o artigo certo entre os 3 primeiros. Para ver pareceres dos casos de teste:
   ```
   python -m genai.src.cadeia
   ```
   Sem chave ou sem banco, nada quebra: sem banco, o parecer sai sem fontes; sem LLM, sai do template de reserva (`origem: "template"`).

## Documentação

- [`DATA.md`](DATA.md): regras dos dados (alvo, recorte, divisão treino e teste, colunas proibidas, fontes externas, privacidade e limitações).
- [`docs/DECISOES.md`](docs/DECISOES.md): decisões de modelagem.
- [`docs/glossario.md`](docs/glossario.md): siglas e termos do projeto.
- [`docs/qualidade_dados.md`](docs/qualidade_dados.md): relatório de qualidade dos dados (regras e alertas).
- [`notebooks/dados/01_eda.ipynb`](notebooks/dados/01_eda.ipynb): análise exploratória e as figuras dos slides (`docs/figuras/`).
- [`docs/bpmn/`](docs/bpmn/): processo em BPMN 2.0.
- [`genai/FORMATO_JSON.md`](genai/FORMATO_JSON.md) e [`genai/REGRAS_PARECER.md`](genai/REGRAS_PARECER.md): contrato e regras do parecer.
- [`genai/normas/FONTES.md`](genai/normas/FONTES.md): normas usadas no RAG, com fonte oficial e data de acesso.
- [`genai/prompts/`](genai/prompts/): prompts versionados do parecer (a v2 corrige os problemas do primeiro teste real da v1).
- [`genai/avaliacao/CRITERIOS.md`](genai/avaliacao/CRITERIOS.md): critérios de avaliação do parecer, definidos antes dos resultados.
- [`skills/`](skills/README.md): guia do projeto por setor (estrutura, ambiente, dados, modelo, juro justo, parecer, API, painel, governança).

## Governança e ética

- Gênero, idade, estado civil e dependentes servem só para auditar, nunca para decidir. País entra no modelo como controle e não é grupo auditado.
- O sistema nunca decide sozinho: o analista decide e pode encaminhar ao compliance (direito de revisão, LGPD art. 20).
- O parecer fala em indício e ponto de atenção, nunca em ilegalidade, e seus números são checados contra a API.
- Identificadores não vão para o LLM nem para os slides; o `cliente_id` é pseudonimizado.
- Limitações: dados estonianos de 2009 a 2021, só empréstimos aprovados e análise jurídica hipotética.

## Equipe

| Pessoa | Frente |
| --- | --- |
| Marcos | Dados e processo |
| Samuel | Modelo e juro justo |
| Maria | GenAI |
| Yasmin | App e infraestrutura |

## Uso de IA no desenvolvimento

Cada frente registra aqui como usou assistentes de IA (agentic coding) e como revisou o resultado.

- **Dados:** os scripts de carga, os esquemas SQL e a documentação foram escritos com apoio do Claude e revisados e testados pelo responsável da frente.
- **App e infraestrutura:** a integração da API com o `prever()`, as telas do painel e os testes foram feitos com apoio do Claude, a partir dos protótipos do grupo e dos contratos (`FORMATO_JSON.md`, `REGRAS_PARECER.md`). A responsável revisou o código e conferiu o resultado com testes automáticos e rodando as telas.
- **Modelo:** a completar.
- **GenAI:** a limpeza das normas, o código (divisão, indexação, cadeia, checagem e template), os testes e os prompts foram feitos com apoio do Claude. A responsável conferiu cada norma na fonte oficial (`FONTES.md`), rodou os testes, leu os pareceres reais do Gemini e usou outra IA como revisora independente do código. Os problemas encontrados no primeiro teste real (país no texto, rótulo alterado, frase hipotética sem norma) viraram regras e testes, e o prompt passou para a v2.
