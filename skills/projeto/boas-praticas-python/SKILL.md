---
name: auditor-boas-praticas-python
description: Aplique ao escrever ou revisar qualquer código, teste, commit ou documento do Auditor de Preço Justo. Define idioma e nomes (português, snake_case), unidades de juros e PD, contratos em pydantic, testes sintéticos, padrão dos documentos e Git.
---

# Boas práticas de Python e documentação

Ao criar, alterar ou revisar código, testes ou documentos deste projeto, siga estas convenções. Preserve os padrões que já existem quando não conflitarem com elas e prefira soluções simples, explícitas e idiomáticas. Siga também a skill `auditor-estrutura` para saber onde cada arquivo mora.

## Idioma e nomes

- Escreva código (variáveis, funções, colunas), documentação, commits e textos ao usuário em **português do Brasil**. Mantenha em sigla os termos técnicos consagrados: PD, LGD, AUC, KS, SHAP, RAG, LLM.
- Use `snake_case` para variáveis, funções e módulos; `PascalCase` para classes (`SolicitacaoEmprestimo`); `UPPER_SNAKE_CASE` para constantes no topo do módulo, com comentário do porquê (`TOLERANCIA_PP = 0.051  # texto usa 1 casa decimal`).
- Comece nomes de função por verbo (`carregar_carteira`, `montar_contrato`, `conferir_parecer`).
- Use os nomes de coluna **do banco** (`juro_aa`, `prazo_meses`, `valor_concedido`, `renda_total`, `pais`). Nomes em inglês só existem no formulário da API (`amount`, `loan_duration`) e são convertidos logo na entrada.

## Unidades (o erro mais comum do projeto)

- Faça PD e juros circularem **em fração** (0.249 = 24,9% a.a.). Exceção única: `juro_aa` do banco e `interest_cobrado` da API chegam **em %** e o `prever()` divide por 100.
- Trate juros como **nominais ao ano** (taxa mensal = juro ÷ 12). Converta a série efetiva do Banco Central com `12 × ((1 + t)^(1/12) − 1)` antes de comparar.
- Use valores em euro. Renda e passivos da Estônia antes de 2011 já são convertidos de coroas na carga e no `ler_base()`; não converta de novo.
- Formate texto para pessoas pelo código, nunca pelo LLM: vírgula decimal e 1 casa ("24,9%"); nulo vira "—", nunca 0%.
- Use datas em ISO 8601 e horários com fuso −03:00.

## Código

- Represente todo formato que atravessa frentes como modelo **pydantic** (fonte da verdade em `genai/src/checagem.py`); importe, não copie.
- Declare campos que podem faltar como `Optional` com `None` explícito, nunca 0.
- Valide dados tabulares com esquema **pandera**, separando erros (quebram o teste) de alertas (registrados).
- Faça divisões seguras: renda zero ou vazia vira `NaN`, nunca infinito.
- Trate erros específicos; não esconda falhas com `except` genérico ou silencioso.
- Use `with` para conexões e arquivos.
- Separe lógica de entrada e saída: funções puras (formatação, cálculo, resumo) ficam em módulos testáveis sem Streamlit, FastAPI ou banco.
- Remova no mesmo PR qualquer arquivo, função, constante ou dependência que ficar sem uso.

## Testes

- Crie teste em `tests/<parte>/` para todo módulo novo.
- Use dados **sintéticos**; nenhum teste pode depender do CSV real ou do `.joblib` para passar na CI. Quando precisar deles, pule com `pytest.skip` ou `pytest.importorskip`.
- Na API, troque o `prever()` por respostas de `docs/exemplos_prever.json` com `monkeypatch`.
- Nomeie o arquivo de teste pelo **assunto**, nunca pela versão (`test_regras.py`, não `test_v4.py`).
- Não considere nada pronto com teste falhando.

## Documentos

- Abra com título, **versão, data, responsável, revisor e status**; termine com **Pendências** (checkbox) e **Histórico** (versão, data, mudança).
- Marque item não decidido com **[A CONFIRMAR]** e a escolha padrão adotada.
- Registre decisões sempre com **o motivo** (`docs/DECISOES.md`).

## Mudar um contrato entre frentes

1. Proponha como nova versão no documento do dono (ex.: `genai/FORMATO_JSON.md`).
2. Avise as quatro frentes.
3. Mude o pydantic, os exemplos (`docs/exemplos_prever.json`) e os testes **no mesmo PR**.
4. Atualize a skill `auditor-contratos-dados`.

## Git

- Crie um ramo por tarefa (`samuel-margem`, `yasmin-painel`) e abra PR para `main` com descrição em Markdown: o que muda, testes, como testar, pendências.
- Escreva commits em português, no imperativo ("Liga a API ao prever() real").
- Nunca faça commit de `.env`, CSVs, `.joblib` ou chaves.
- Registre no `README.md` (seção "Uso de IA") como a IA foi usada e como o resultado foi revisado.
