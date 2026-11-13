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
| Parecer | LangChain (chain LCEL: busca → prompt → Gemini → conferência), Gemini (`langchain-google-genai`), pgvector, sentence-transformers multilíngue, prompts versionados |
| Back-end e front-end | FastAPI (API, porta 8000) e Streamlit (painel, porta 8501), conversando por HTTP/JSON |
| Infra e qualidade | Docker Compose, Terraform (Google Cloud), pytest, black, flake8, GitHub Actions |

## Estrutura

```
src/
├── api/        BACK-END  · FastAPI: rotas (main.py), formatos (schemas.py), banco (database.py), análise (contract_analysis.py), lote (portfolio.py)
├── app/        FRONT-END · Streamlit: telas (main.py), visual (styles.css), blocos (components.py)
├── modelos/    modelo de risco e juro justo: prever() e o lote da carteira (Samuel)
└── dados/      cargas do Bondora e das séries de juros (Marcos)
genai/          parecer: formato JSON, regras, normas, prompts e código (Maria)
db/             esquemas SQL; rodam sozinhos na primeira criação do banco
infra/          Terraform: VM na Google Cloud rodando o mesmo Docker Compose
docs/           decisões de modelagem, glossário, BPMN, roteiro da demo, resultados do lote
notebooks/      EDA e etapas do modelo (coortes, variáveis, XGBoost, LGD, margem)
tests/          testes, na mesma divisão do src/ (api, app, dados, modelos, genai)
skills/         guia do projeto por setor, para pessoas e para IA (ver skills/README.md)
data/raw/       arquivos de dados (fora do Git)
modelos_salvos/ pacote do modelo (.joblib, fora do Git)
```

## Como rodar

Pré-requisitos: Git, Python 3.14 e Docker Desktop.

**Atalho (Windows):** `.\iniciar.ps1` no PowerShell (antes, se o Windows bloquear: `Set-ExecutionPolicy Bypass -Scope Process`), ou `docker compose up -d`. Num PC novo basta Docker Desktop, `.env`, o `.joblib` do modelo e os 4 CSVs de custo do dinheiro em `data/raw/` (`ECB_Euribor_Serie-Mensal-12-Meses.csv`, `ECB_Euribor_Serie-Mensal-3-Meses.csv`, `BC-Selic_Acumulada_Mes_Anuzalizada_base252.csv`, `bcdata.sgs.20742.csv`). A base do Bondora só é necessária para refazer os dados e o modelo (passos 2 a 5 abaixo).

| Comando | O que faz |
| --- | --- |
| `.\iniciar.ps1` | confere portas, `.env` e modelo, sobe o banco, aplica a tabela de decisões, indexa as normas e carrega a referência do BC (se faltarem), sobe API e painel e abre o navegador. Constrói a imagem só se ela não existir. |
| `.\iniciar.ps1 -Build` | o mesmo, reconstruindo a imagem (mudou código ou requirements) |
| `.\iniciar.ps1 -Parar` | para tudo; os dados do banco ficam guardados |

O primeiro build leva alguns minutos (PyTorch); os seguintes reaproveitam o cache e uma imagem única serve API e painel.

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
   - `ECB_Euribor_Serie-Mensal-12-Meses.csv` (o download do BCE às vezes vem como `..._csv.csv`: os dois nomes funcionam) e `ECB_Euribor_Serie-Mensal-3-Meses.csv`
   - `BC-Selic_Acumulada_Mes_Anuzalizada_base252.csv`
   - `BC-Meta_Selic_Mensal.csv` (opcional, só conferência)
   - `bcdata.sgs.20742.csv` (opcional, referência de mercado do BC)
   - `bcdata.sgs.25464.csv` (opcional, só para conferir a conversão da taxa do BC: `python src/dados/validar_conversao_bc.py`)

3. **Configuração.** Crie um `.env` na raiz, que nunca vai ao Git:
   ```
   CLIENTE_ID_SAL=<chave de pelo menos 16 caracteres, a mesma para todo o grupo>
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/auditor_db
   GOOGLE_API_KEY=<chave do Gemini, para o parecer>
   ```
   A chave do sal pseudonimiza o `cliente_id`; peça-a ao grupo. Sem a `GOOGLE_API_KEY`, o parecer sai pelo template de reserva (sem IA). Se a porta 5432 estiver ocupada, use um `docker-compose.override.yml` local com a porta 5433 e ajuste a URL.

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

   **Normas do parecer** (busca no pgvector), uma vez, com `pip install -r requirements-genai.txt`:
   ```
   python genai/src/indexar.py
   ```
   Sem esse passo o parecer funciona, mas sai sem fontes.

6. **API e painel.** Coloque `pacote_prever_v1.joblib` em `modelos_salvos/` (fora do Git; peça ao Samuel) e suba:
   ```
   docker compose up --build api streamlit
   ```
   O primeiro build demora mais: a imagem instala o PyTorch (CPU) para a busca nas normas. Depois, `docker compose up -d` sobe sem reconstruir; use `--build` só quando mudar código ou requirements.
   - Painel: http://localhost:8501 (sem o modelo, use os exemplos da aba de revisão)
   - API: http://localhost:8000/docs (`GET /` informa se o modelo foi carregado)
   - Para os dados da carteira, a API lê `docs/resultados/carteira_auditoria.csv` e `equidade.json` (`src/api/portfolio.py`) e o painel pede pelas rotas `/portfolio/overview` e `/contracts`.
   - As decisões do analista ficam na tabela `decisao_analista`. Banco criado antes de 09/11? Aplique (ou reaplique) uma vez; pode rodar de novo sem problema:
     ```
     docker cp db\05_decisoes_analista.sql auditor_postgres:/tmp/05.sql
     docker exec auditor_postgres psql -U postgres -d auditor_db -v ON_ERROR_STOP=1 -f /tmp/05.sql
     ```
     Em http://localhost:8000/ deve aparecer `"banco_disponivel": true`.

## Documentação

- [`DATA.md`](DATA.md): regras dos dados (alvo, recorte, divisão treino e teste, colunas proibidas, fontes externas, privacidade e limitações).
- [`docs/DECISOES.md`](docs/DECISOES.md): decisões de modelagem.
- [`docs/glossario.md`](docs/glossario.md): siglas e termos do projeto.
- [`docs/qualidade_dados.md`](docs/qualidade_dados.md): relatório de qualidade dos dados (regras e alertas).
- [`notebooks/dados/01_eda.ipynb`](notebooks/dados/01_eda.ipynb): análise exploratória e as figuras dos slides (`docs/figuras/`).
- [`docs/bpmn/`](docs/bpmn/): processo em BPMN 2.0.
- [`genai/FORMATO_JSON.md`](genai/FORMATO_JSON.md) e [`genai/REGRAS_PARECER.md`](genai/REGRAS_PARECER.md): contrato e regras do parecer.
- [`genai/avaliacao/`](genai/avaliacao/CRITERIOS.md): critérios, os 20 casos de avaliação e os resultados do parecer (prompts v2 a v4), com a revisão humana da v4.
- [`docs/ROTEIRO_DEMO.md`](docs/ROTEIRO_DEMO.md): roteiro da demo, plano B e perguntas prováveis.
- [`infra/`](infra/README.md): Terraform que cria na Google Cloud uma VM rodando o mesmo Docker Compose (para a demo na nuvem).
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
- **App e infraestrutura:** a integração da API com o `prever()`, as telas do painel e os testes foram feitos com apoio do Claude, a partir dos protótipos do grupo e dos contratos (`FORMATO_JSON.md`, `REGRAS_PARECER.md`). A responsável revisou o código e conferiu o resultado com testes automáticos e rodando as telas. O formulário com etapas travadas, a separação do visual em `styles.css` e os scripts `iniciar` seguiram o mesmo processo.
- **Modelo:** a completar pela frente.
- **GenAI:** o código do parecer, os prompts e os documentos da frente foram escritos com apoio do Claude, guiado pelos guias da frente em `skills/regras_negocio/` ([`normas_rag`](skills/regras_negocio/normas_rag/SKILL.md), [`parecer_genai`](skills/regras_negocio/parecer_genai/SKILL.md) e [`avaliacao_parecer`](skills/regras_negocio/avaliacao_parecer/SKILL.md)) e pelos contratos (`FORMATO_JSON.md`, `REGRAS_PARECER.md`). As propostas maiores (template, cadeia em LangChain, prompts v3 e v4) também passaram pela revisão de uma segunda IA. A responsável leu cada mudança antes de aplicá-la e conferiu o resultado com os testes automáticos (`tests/genai/`), a avaliação dos 20 casos e a revisão humana dos pareceres (`genai/avaliacao/`).
