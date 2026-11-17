# App e infraestrutura: o que é cada arquivo

Frente da Yasmin: API (FastAPI), painel (Streamlit), Docker, `iniciar.ps1`, integração contínua e os scripts de conferência. Este guia diz para que serve cada pasta e arquivo dessa frente e como as partes se ligam. As regras de cada parte estão nas skills `regras_negocio/api`, `regras_negocio/painel` e `ambiente-e-infra`.

## Como as partes se ligam

```
Navegador ──► painel (Streamlit, porta 8501) ──► API (FastAPI, porta 8000) ──► prever() do modelo (src/modelos)
                     só mostra                        decide e calcula        ├─► banco PostgreSQL (contratos, decisões, normas)
                                                                              ├─► lote da carteira (docs/resultados)
                                                                              └─► parecer da GenAI (genai/src)
```

- O **painel** nunca calcula nem lê arquivo: tudo vem da API.
- A **API** é a única porta para o modelo, o banco, o lote e o parecer.
- O **Docker** sobe os três serviços (banco, API e painel) com um comando; o `iniciar.ps1` faz isso e prepara o banco.

## Pastas e arquivos

### `src/api/`: a API (back-end)

| Arquivo | Para que serve |
|---|---|
| `__init__.py` | Marca a pasta como pacote Python (permite `from src.api import ...`). |
| `main.py` | As **rotas**, agrupadas em /docs (Situação, Carteira, Contrato ao vivo, Laboratório, Auditoria, Decisões, Integração): o que a API responde em cada endereço (`/contracts/{id}/analysis`, `/scenario`, `/invariance`, `/portfolio/overview`, `/decisions` etc.), os códigos de erro e o plano B. |
| `schemas.py` | Os **formatos** de entrada e saída de cada rota (pydantic). A API recusa o que não estiver no formato. |
| `database.py` | Tudo que fala com o **PostgreSQL**: buscar o contrato pelo ID, o desfecho, a referência do BC, gravar e listar decisões. A consulta do contrato não lê gênero nem idade. |
| `contract_analysis.py` | Monta a tela **Análise do contrato**: as 21 variáveis (fornecidas × derivadas), os parâmetros do juro justo, a procedência (arquivo, hash e data do modelo) e o resultado montado a partir do lote no plano B. |
| `scenario.py` | O **Laboratório**: aplica os campos trocados sobre o contrato do banco, roda o `prever()` de novo e mede o efeito de cada campo sozinho; limites do treino. |
| `invariance.py` | O **teste de invariância**: roda o `prever()` com gênero e idade reais e trocados e compara, sem devolver os valores. |
| `portfolio.py` | Lê e resume o **lote da carteira** (`docs/resultados/`): Home, lista de contratos, exportação, equidade e o resumo da invariância em lote. |

### `src/app/`: o painel (front-end)

| Arquivo | Para que serve |
|---|---|
| `__init__.py` | Marca a pasta como pacote Python. |
| `main.py` | A **moldura** (~90 linhas): configuração da página, estilo, memória da sessão, menu do topo e qual página mostrar. É o arquivo que o `streamlit run` abre. |
| `nucleo.py` | O que **todas as páginas usam**: endereço da API, chamadas HTTP com os erros traduzidos para português, dados do lote em cache, navegação (`go_to`) e o `md()` que injeta HTML. |
| `paginas/` | **Uma página por arquivo**, cada uma com a sua função `render_*`: `inicio.py`, `contratos.py`, `analise.py` (inclui a decisão do analista), `laboratorio.py`, `auditoria.py`, `registro.py`, `sobre.py`. |
| `components/` | Formatação (números em português, "24,9%", "€ 1.234") e os **blocos de HTML**, separados por página: `base.py` (formatação, situações, cartão, ícone "i"), `analise.py`, `laboratorio.py`, `carteira.py`, `auditoria.py`, `equipe.py`. Não usa Streamlit, então é testável com pytest. |
| `styles/` | Todo o **visual**, um `.css` por parte, carregados em ordem pelo número: `01_base`, `02_menu`, `03_inicio`, `04_cartoes`, `05_contratos_analise`, `06_laboratorio`, `07_auditoria`, `08_registro`, `09_sobre`, `10_logo` (logo CredFlare e a animação da capa). |
| `imagens/` | `credflare_icone.png` (ícone da aba do navegador) e fotos opcionais: `capa.jpg` (topo da Início) e `equipe/<nome>.jpg` (página Sobre). Sem elas, aparecem a imagem padrão e as iniciais. Instruções em `imagens/LEIA-ME.md`. |

### `scripts/`: conferências com dados reais

| Arquivo | Para que serve |
|---|---|
| `__init__.py` | Permite rodar como `python -m scripts.<nome>`. |
| `conferir_analise.py` | Abre 20 contratos reais pela API e compara com o lote (PD, juro justo, margem, situação, motivos, sem gênero e idade). Esperado: **20/20**. |
| `invariancia_lote.py` | Teste de invariância em 500 contratos sorteados; grava `docs/resultados/invariancia_lote.json`, que a Auditoria mostra. Esperado: **500/500**. Rodar de novo quando o modelo mudar. |

### `tests/api/` e `tests/app/`: testes automáticos (pytest)

| Arquivo | O que testa |
|---|---|
| `tests/api/test_api.py` | Rotas `/predict`, `/opinion` e `/decisions` (sem gênero e idade, sem gravar o mesmo clique duas vezes). |
| `tests/api/test_contract_analysis.py` | Rota de análise: 21 variáveis, precificação, procedência, plano B pelo lote, nomes combinados com o parecer, `loan_id` normalizado. |
| `tests/api/test_scenario.py` | Laboratório: só o juro não muda a PD; o prazo muda; limites; campos proibidos recusados. |
| `tests/api/test_invariance.py` | Invariância: resultado idêntico, valores reais nunca saem da API, um modelo que usasse gênero seria pego. |
| `tests/api/test_portfolio.py` e `test_portfolio_routes.py` | Leitura do lote e as rotas da Home e da lista. |
| `tests/api/test_integracao_analise.py` | Só roda com banco, modelo e lote reais (pulado no GitHub). |
| `tests/app/test_components.py` | Os blocos de HTML do painel. |
| `tests/__init__.py`, `tests/*/__init__.py` | Marcam as pastas como pacotes (um teste pode importar dados de outro). |

### Raiz do projeto: ambiente e Docker

| Arquivo | Para que serve |
|---|---|
| `Dockerfile` | Receita da **imagem** da aplicação (Python, bibliotecas e o código). A mesma imagem roda a API e o painel. |
| `docker-compose.yml` | Os **três serviços** (banco, API, painel), portas, volumes (onde ficam o modelo, o lote e os dados do banco) e a ordem de subida. |
| `.dockerignore` | O que **não** entra na imagem (Git, ambientes virtuais, caches, `data/raw/`, figuras). |
| `docker-compose.override.yml` | Opcional e só local (fora do Git): troca a porta do banco para 5433 quando o PC já tem outro PostgreSQL. |
| `iniciar.ps1` | Sobe tudo no Windows: confere `.env` e modelo, sobe o banco, aplica `db/05` a `db/07`, constrói a imagem, indexa as normas, carrega os contratos e a referência do BC e abre o navegador. O passo a passo está no topo do arquivo. |
| `requirements.txt` | Bibliotecas da aplicação (FastAPI, Streamlit, XGBoost, SHAP, pandas, psycopg2...). |
| `requirements-genai.txt` | Bibliotecas extras da GenAI (Gemini, busca nas normas). |
| `requirements-dev.txt` | Tudo do `requirements.txt` mais o pytest e o que os testes usam. |
| `pytest.ini` | Configuração do pytest (a raiz do projeto entra no caminho dos imports). |
| `.streamlit/config.toml` | Tema escuro do Streamlit e opções do servidor. |
| `.github/workflows/ci.yml` | **Integração contínua**: a cada push e PR, o GitHub sobe um banco temporário e roda os testes. São os "checks" verdes do PR. |
| `.env` | Segredos e endereço do banco (fora do Git): `CLIENTE_ID_SAL`, `DATABASE_URL`, `GOOGLE_API_KEY`. |

### Arquivos gerados e de apoio

| Arquivo | Para que serve |
|---|---|
| `docs/resultados/invariancia_lote.json` | Resultado do `scripts/invariancia_lote.py` (contagens e identificação do modelo, sem gênero nem idade). |
| `docs/ROTEIRO_DEMO.md` | Roteiro da demo (feito com a Maria): checklist do dia, sequência, plano B e perguntas da banca. |
| `docs/APP_E_INFRA.md` | Este guia. |
| `skills/regras_negocio/api/SKILL.md`, `painel/SKILL.md`, `skills/ambiente-e-infra/SKILL.md` | Regras da frente, para pessoas e para IA: o que pode, o que não pode e quando está pronto. |
| `infra/cloud-init.yaml` (passo 2b) | Trecho que carrega os contratos do Bondora na VM da nuvem (o resto da pasta `infra/` é do Marcos). |

## Extensões

| Extensão | O que é |
|---|---|
| `.py` | Código Python (API, painel, scripts, testes). |
| `.css` | Folha de estilo: cores, fontes e espaçamentos do painel. |
| `.ps1` | Script do PowerShell (Windows). |
| `.yml` / `.yaml` | Configuração em YAML (Docker Compose, CI do GitHub, cloud-init da VM). |
| `.toml` | Configuração em TOML (Streamlit). |
| `.ini` | Configuração em INI (pytest). |
| `.txt` | Lista de bibliotecas (requirements). |
| `.json` | Dados estruturados (resultados do lote, resumo da invariância). |
| `.md` | Documentação em Markdown (README, roteiro, skills, este guia). |
| `Dockerfile` (sem extensão) | Receita da imagem Docker; o nome é fixo. |
| `.env` (sem nome antes do ponto) | Variáveis de ambiente e segredos; nunca vai ao Git. |
| `.joblib` | O modelo treinado (do Samuel), salvo em Python; fica fora do Git, em `modelos_salvos/`. |
