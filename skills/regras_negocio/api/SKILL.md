---
name: auditor-api
description: Use para construir ou alterar a API FastAPI do Auditor de Preço Justo — rotas, conversão do formulário para os nomes do banco, chamada ao prever(), anexação do parecer, tratamento de erros, testes com monkeypatch e próximas rotas (decisões, referência do BC).
---

# API (FastAPI)

> Leia antes: `regras_negocio/contratos_dados` (seção 4), `regras_negocio/governanca`, `ambiente-e-infra`. Dono: Yasmin. Código: `src/api/main.py`, `src/api/schemas.py`; testes `tests/api/test_api.py`.

## Objetivo

Ser a **única porta** entre o painel e o motor: recebe o formulário, converte para o contrato do `prever()`, devolve risco, juro justo, situação e parecer, sem reinventar formatos.

## Rotas

| Rota | Entrada | Saída | Observações |
|---|---|---|---|
| `GET /` | — | `{"status", "modelo_carregavel"}` | `modelo_carregavel = False` quando falta `modelos_salvos/pacote_prever_v1.joblib` |
| `POST /prever` | `SolicitacaoEmprestimo` | `RespostaPrever` (saída do `prever()` + `parecer_ia`) | sem modelo → **503** com mensagem clara; dados inválidos → 422 |
| `POST /parecer` | `RespostaPrever` (saída do `prever()` já calculada) | `Parecer` | usado pelos exemplos e pela carteira |
| `/docs` | — | documentação automática | |

`app = FastAPI(title="Auditor de Juros - API", version="1.0.0")`.

## Regras

1. **Schemas importam os modelos da GenAI** (`EntradaPrever`, `Motivo`, `Parecer` de `genai/src/checagem.py`). `RespostaPrever` **herda** de `EntradaPrever`; `MotivoPrever` herda de `Motivo` e acrescenta `valor` e `peso`. Nunca duplicar campos.
2. `montar_contrato(dados)` converte o formulário para os **nomes do banco** e inclui **todas** as chaves exigidas pelo `prever()`, com `None` quando não há dado (`contratos_dados`, seção 4). `juro_aa` vai **em %**.
3. `country` aceita "EE" ou "EE(Estônia)" e guarda só a sigla em maiúsculas. `data_emprestimo` tem padrão **hoje** e é recusada no futuro.
4. **Gênero e idade** podem chegar na requisição, mas **não** entram no dicionário do `prever()` nem no parecer.
5. O parecer é montado em `_parecer(resultado)`: hoje `montar_template(EntradaPrever.model_validate(resultado))`; com a entrega da Maria, `gerar_parecer(resultado)`. **Só essa função muda.**
6. A API não calcula número nenhum: tudo vem do `prever()` ou da GenAI.
7. Uma única função de pseudonimização existe no projeto, na carga. A API não pseudonimiza nada (não recebe `UserName`).

## Testes (`tests/api/test_api.py`)

- `pytest.importorskip("fastapi")` e `("xgboost")`; `TestClient` (exige `httpx2`).
- O `prever()` é trocado com `monkeypatch` por saídas de `docs/exemplos_prever.json`, então os testes rodam sem o `.joblib`.
- Cobrem: dicionário enviado (sigla do país, prazo, juro em %, passivos, chaves presentes, sem gênero/idade); as 4 situações passam no schema; `/parecer` devolve a recomendação certa por situação; data padrão hoje e futuro → 422; sem modelo → 503; os 8 casos reais de `docs/casos_de_teste.json` passam em `/prever` e `/parecer`.

## Pronto quando

- `pytest tests/api -v` passa.
- `GET /` com `modelo_carregavel: true` no Docker e `POST /prever` responde para um contrato do formulário.

## Estado em 06/11/2026 e próximos passos

- **[PRONTO]** `/`, `/prever` real, `/parecer`, conversões, erros, testes.
- **[PENDENTE] (Yasmin, depende da Maria)** trocar o template por `gerar_parecer()` em `_parecer()`; a imagem da API precisa das dependências da GenAI e da `GOOGLE_API_KEY` (`ambiente-e-infra`).
- **[PENDENTE] (Yasmin, depende do Marcos)** conexão com o banco (SQLAlchemy, `DATABASE_URL`) para:
  - `POST /decisoes` e `GET /decisoes` (gravar e listar decisões do analista; formato em `contratos_dados`, seção 6);
  - buscar `bc_credito_pessoal_aa` do mês da concessão na `vw_custo_do_dinheiro` e repassar ao `gerar_parecer()` para o `contexto_mercado`.
- **[A DECIDIR]** rota para buscar um contrato da carteira pelo ID (o protótipo da tela tem busca por ID). Padrão: não existe; o painel usa a fila da carteira e os exemplos.
