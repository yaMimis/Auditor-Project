# Auditor de Preço Justo

Projeto integrador do bootcamp de IA aplicada (segmento BFSI, TCS). Para cada contrato de crédito, o sistema estima o risco de inadimplência, diz se o juro cobrado é justo para esse risco e verifica se clientes com o mesmo risco pagam juros diferentes por gênero, idade ou país. Um parecer gerado por IA, apoiado em normas brasileiras, explica o resultado ao analista, que decide.

Status: em desenvolvimento. Entrega dos arquivos em 19/11/2026 e apresentação em 21/11/2026.

## Enquadramento

- O produto é pensado para o mercado brasileiro. Como não existe base pública brasileira com contratos individuais, usamos os dados reais da plataforma estoniana Bondora (2009 a 2021) como substituto do comportamento de crédito.
- O motor de risco e de preço usa o contexto da época de cada contrato (Euribor).
- O parecer segue a LGPD, o CDC e as normas do Banco Central, em modo hipotético: "se este contrato fosse de um banco brasileiro".

## Arquitetura

Contrato → modelo de risco (PD, probabilidade de default) → juro justo por fluxo de caixa → comparação com o juro cobrado → busca das normas (RAG, geração aumentada por recuperação) → parecer em JSON → checagem dos números contra a API → painel do analista → decisão humana.

| Camada | Tecnologias previstas |
| --- | --- |
| Dados | pandas, pandera, PostgreSQL, SQLAlchemy |
| Vetores | pgvector, no mesmo PostgreSQL |
| Modelo | scikit-learn, XGBoost, SHAP, statsmodels, fairlearn |
| Parecer | LangChain, API de LLM, embeddings multilíngues |
| Serviço e app | FastAPI, Streamlit |
| Infra e qualidade | Docker Compose, pytest, ruff, GitHub Actions |

## Estrutura

```
data/raw/     arquivos de dados (fora do Git)
db/           esquemas SQL; rodam sozinhos na primeira criação do banco
docs/         decisões de modelagem (DECISOES.md)
genai/        formato JSON e regras do parecer
notebooks/    análises exploratórias e de coortes
src/api/      API FastAPI
src/app/      painel Streamlit
src/dados/    cargas do Bondora e das séries de juros
src/db/       conexão e modelos do banco
src/modelos/  modelo de risco e juro justo
tests/        testes
```

## Como rodar

Pré-requisitos: Git, Python 3.11 e Docker Desktop.

1. Clone o repositório e instale as dependências:
   ```
   git clone https://github.com/yaMimis/Auditor-Project.git
   cd Auditor-Project
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
   No Mac ou Linux, ative com `source .venv/bin/activate`.

2. **Dados.** Todos os arquivos ficam numa pasta compartilhada do Drive, fora do Git (o repositório é público). Peça o link ao grupo e coloque os arquivos em `data/raw/`, com estes nomes:
   - `LoanData_Bondora.csv` (confira o SHA-256 em `DATA.md`)
   - `ECB_Euribor_Serie-Mensal-12-Meses_csv.csv` e `ECB_Euribor_Serie-Mensal-3-Meses.csv`
   - `BC-Selic_Acumulada_Mes_Anuzalizada_base252.csv`
   - `BC-Meta_Selic_Mensal.csv` (opcional, só conferência)
   - `bcdata.sgs.20742.csv` (opcional, referência de mercado do BC)

3. **Configuração.** Crie um `.env` na raiz, que nunca vai ao Git:
   ```
   CLIENTE_ID_SAL=<chave de pelo menos 16 caracteres, a mesma para todo o grupo>
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/auditor_db
   ```
   A chave pseudonimiza o `cliente_id`; peça-a ao grupo. Se a porta 5432 estiver ocupada, use um `docker-compose.override.yml` local com a porta 5433 e ajuste a URL.

4. **Banco.** Suba o PostgreSQL com pgvector:
   ```
   docker compose up -d db
   ```
   Na primeira criação, os arquivos de `db/` rodam sozinhos e criam a extensão, as tabelas e as views. Em um banco já existente, aplique-os à mão ou use `--ddl` nas cargas.

5. **Carga**, nesta ordem:
   ```
   python src/dados/carga_bondora.py --csv data/raw/LoanData_Bondora.csv
   python src/dados/carga_macro.py
   ```
   Esperado: 179.235 contratos e 85.087 clientes distintos.

6. **API.** `docker compose up --build api` e abra http://localhost:8000/docs. O painel Streamlit ainda está em desenvolvimento.

## Documentação

- [`DATA.md`](DATA.md): regras dos dados (alvo, recorte, divisão treino e teste, colunas proibidas, fontes externas, privacidade e limitações).
- [`docs/DECISOES.md`](docs/DECISOES.md): decisões de modelagem.
- [`genai/FORMATO_JSON.md`](genai/FORMATO_JSON.md) e [`genai/REGRAS_PARECER.md`](genai/REGRAS_PARECER.md): contrato e regras do parecer.

## Governança e ética

- Gênero e idade (e estado civil e dependentes, se aprovado) servem só para auditar, nunca para decidir.
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
- **Modelo, GenAI e App:** a completar por cada frente.
