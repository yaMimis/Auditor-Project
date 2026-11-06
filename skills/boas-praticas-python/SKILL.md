---
name: auditor-boas-praticas-python
description: Use ao escrever ou revisar qualquer código, teste ou documento do Auditor de Preço Justo — idioma, nomes, unidades, pydantic como contrato, testes sintéticos, padrão dos documentos, versionamento e como mudar um contrato entre frentes.
---

# Boas práticas de Python e documentação

> Leia antes: `estrutura-projeto`. Vale para todos os setores.

## Objetivo

Código e documentos que qualquer frente entende, testa e muda sem quebrar o trabalho das outras.

## Idioma e nomes

1. **Português do Brasil** em código (variáveis, funções, colunas), documentação, commits e textos ao usuário. Termos técnicos consagrados ficam em sigla: PD, LGD, AUC, KS, SHAP, RAG, LLM.
2. Nomes de colunas são os **do banco**, em português (`juro_aa`, `prazo_meses`, `valor_concedido`, `renda_total`, `pais`). Nomes em inglês só existem na fronteira do formulário da API (`amount`, `loan_duration` …) e são convertidos logo na entrada.
3. Funções com verbo (`carregar_carteira`, `montar_contrato`, `conferir_parecer`); constantes em MAIÚSCULAS no topo do módulo, com comentário do porquê (`TOLERANCIA_PP = 0.051  # texto usa 1 casa decimal`).

## Unidades (erro mais comum do projeto)

- PD e juros circulam **em fração** (0.249 = 24,9% a.a.). Exceção única: `juro_aa` do banco e `interest_cobrado` da API vêm **em %** e são divididos por 100 dentro do `prever()`.
- Juros são **nominais ao ano** (taxa mensal = juro ÷ 12), a convenção do Bondora. A série do Banco Central é **efetiva**; converter com `12 × ((1 + t)^(1/12) − 1)` antes de comparar.
- Valores em euro. Renda e passivos da Estônia antes de 2011 vinham em coroas e já são convertidos na carga e no `ler_base()`.
- Texto para pessoas: vírgula decimal e 1 casa ("24,9%"), feito **pelo código**, nunca pelo LLM. Campo nulo vira "—", nunca 0%.
- Datas em ISO 8601; horários com fuso −03:00.

## Contratos e validação

1. Todo formato que atravessa frentes é um **modelo pydantic** (fonte da verdade em `genai/src/checagem.py`). API e painel importam esses modelos.
2. Campos que podem faltar são `Optional` com `None` explícito, nunca 0.
3. Dados tabulares têm esquema **pandera** separando **erros** (quebram o teste) de **alertas** (registrados, sem falhar).
4. Divisão segura: renda zero ou vazia vira `NaN`, **nunca infinito**.

## Testes

1. Todo módulo novo tem teste em `tests/<setor>/`.
2. Dados de teste **sintéticos**; nenhum teste depende do CSV real ou do `.joblib` para passar na CI. Quando precisar deles, o teste se pula sozinho (`pytest.skip` / `pytest.importorskip`).
3. Para lógica de tela, separe funções puras (formatação, HTML, resumos) num módulo testável sem Streamlit (`src/app/componentes.py`, `src/app/carteira.py`).
4. Para a API, troque o `prever()` por respostas de `docs/exemplos_prever.json` com `monkeypatch`.
5. Nada é dado como pronto com teste falhando.

## Padrão dos documentos

- Cabeçalho: título, **versão, data, responsável, revisor e status**.
- Final: **Pendências** (checkbox) e **Histórico** (versão, data, mudança).
- Item não decidido: **[A CONFIRMAR]** com a escolha padrão adotada até a decisão.
- Decisão sempre com **o motivo** (`docs/DECISOES.md`).

## Como mudar um contrato entre frentes

1. Propor no documento do dono (ex.: `FORMATO_JSON.md`) como nova versão.
2. Avisar as quatro frentes.
3. Mudar o pydantic, os exemplos (`docs/exemplos_prever.json`) e os testes **no mesmo PR**.
4. Atualizar o `skills/regras_negocio/contratos_dados/SKILL.md`.

## Git

- Branch por tarefa (`samuel-margem`, `yasmin-painel` …); PR para `main` com descrição em Markdown (o que muda, testes, como testar, pendências).
- Commits em português, no imperativo ("Liga a API ao prever() real").
- Nunca commitar `.env`, CSVs, `.joblib` ou chaves.

## Uso de IA no desenvolvimento

Cada frente registra no `README.md` como usou assistentes de IA e **como revisou** o resultado (testes, leitura do código, conferência com os documentos). Código gerado por IA passa pelos mesmos testes e revisões que o resto.
