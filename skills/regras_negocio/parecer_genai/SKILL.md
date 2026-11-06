---
name: auditor-parecer-genai
description: Use para construir ou alterar o parecer automatizado do Auditor de Preço Justo — quem decide o quê, linguagem, números, recomendação escolhida pelo código, RAG sobre normas brasileiras com pgvector, prompt versionado, chamada ao Gemini, checagem por código, template de reserva e avaliação.
---

# Parecer com GenAI

> Leia antes: `regras_negocio/governanca`, `regras_negocio/contratos_dados`. Dono: Maria (GenAI). Documentos do dono: `genai/REGRAS_PARECER.md` (v1.3), `genai/FORMATO_JSON.md` (v1.4).

## Objetivo

Transformar a saída do `prever()` num **parecer curto, em português, apoiado em normas**, cujos números e regras são **conferidos por código**, com reserva sem IA quando algo falhar.

## Arquivos

`genai/normas/*.md` + `FONTES.md`; `genai/src/dividir.py`, `indexar.py`, `testar_busca.py`, `checagem.py` (pydantic + `conferir_parecer`), `template.py` (`montar_template`, `escolher_recomendacao`), `prompt.py` (`montar_mensagens`), `testar_llm.py`; `genai/prompts/parecer_v1.md`; `genai/avaliacao/`; `tests/genai/`.

## Quem decide o quê

| Quem | Faz |
|---|---|
| `prever()` | todos os números e a marcação de revisão manual |
| Código da cadeia | escolhe a recomendação, decide LLM × template, formata números, busca normas, confere o resultado, escreve `contexto_mercado` |
| **LLM** | **só escreve**: resumo, pontos de atenção, texto da recomendação, escolha das fontes entre os trechos recebidos |
| Analista | decisão final; só ele encaminha ao compliance |

## Recomendação (escolhida pelo código, nesta ordem)

| # | Condição | Recomendação | Quem escreve | O texto deve dizer |
|---|---|---|---|---|
| 1 | `revisao_manual` **ou** `alerta_dados` | `revisao_manual` | template (LLM **não** é chamado) | dados fora da faixa; analisar manualmente; não opinar sobre o preço |
| 2 | `acima_do_justo` | `revisar_preco` | LLM | indício; se a política não justificar, recomenda-se encaminhar ao compliance |
| 3 | `abaixo_do_justo` | `revisar_preco` | LLM | o preço pode não cobrir a perda esperada; sem culpar o cliente |
| 4 | `dentro_da_margem` | `manter_preco` | LLM | não inventar problema |

`encaminhar_compliance` existe no formato, mas **nunca** é escolhida automaticamente.

## Linguagem e números

- PT-BR, frases curtas, sem jargão. Resumo ≤ 2 frases; ≤ 3 pontos de atenção. Modo hipotético: "se este contrato fosse de um banco brasileiro". A recomendação **sempre termina** com "A decisão final é do analista."
- Usar "indício", "ponto de atenção", "recomenda-se revisar", "recomenda-se encaminhar ao compliance". Palavras proibidas em `governanca`, regra 4 (regex `PALAVRAS_PROIBIDAS`; "discriminar" no sentido de detalhar é permitido).
- Fatores pelo `rotulo`, nunca pelo nome técnico.
- Só podem aparecer: PD, juro cobrado, juro justo, mínimo e máximo da margem (e a faixa). O LLM **copia** os números já formatados ("24,9% ao ano"); não recalcula, não arredonda, não calcula diferenças. Campo `null` nunca é citado. Todo número do texto entra em `numeros_citados` com o valor exato.
- Não falar de CET, tarifas, encargos ou média de mercado. **Números do REF nunca aparecem** no parecer (v1.3): os trechos do REF só explicam a composição do custo do crédito.

## Ética e privacidade

- Nada de identificador ao LLM (nem `contrato_id`, nem `versao_modelo`); o código reinsere.
- Gênero, idade e país nunca aparecem; `motivos_permitidos()` filtra motivos sensíveis antes do prompt.

## RAG

- Normas em `genai/normas/`, copiadas de fonte oficial e limpas (sem anotações, revogados ou vetados), com `FONTES.md` (arquivo, norma, artigos, URL, data de acesso):
  - `lgpd.md` Lei 13.709/2018, arts. 5º, 6º, 7º, 11, 12, 20
  - `cdc.md` Lei 8.078/1990, arts. 2º, 3º, 4º, 6º, 30, 31, 39, 42, 42-A, 46, 47, 52, 54, 54-A a 54-D, 54-F, 54-G, 104-A a 104-C
  - `cet.md` Res. CMN 4.881/2020, arts. 1º a 9º
  - `credito_oferta.md` Res. CMN 5.004/2022, arts. 1º a 9º
  - `ref.md` Relatório de Estabilidade Financeira do BC (maio/2026), seção 2.1 e apêndice, dividido por parágrafo
- **Divisão:** um trecho por artigo; longos quebrados entre incisos/parágrafos (`TAMANHO_MAXIMO = 1000`, sobra < `TAMANHO_MINIMO = 300` junta à anterior, repete `TAMANHO_CAPUT = 150` caracteres do caput).
- **`trecho_id`:** `<arquivo>-art<número>-<parte>` (`cdc-art6-1`, `cdc-art54b-1`, `lgpd-art20-1`); REF `ref-p<parágrafo>-1`. O inciso vai no campo `artigo` da fonte ("art. 6º, III").
- **Indexação:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensões) na tabela `trechos_normas` do pgvector.
- **Busca:** top 3–5 trechos com `norma`, `artigo`, `trecho_id`, `texto`. O LLM cita só o que recebeu. Sem trecho pertinente → `fontes: []`; a tela mostra "Não encontrei base normativa para este caso."

## Prompt e LLM

- Prompt versionado em `genai/prompts/parecer_vN.md`; `prompt.py` lê só as seções "Mensagem do sistema" e "Mensagem do usuário" e preenche `{situacao}`, `{recomendacao}`, `{faixa}`, `{numeros}`, `{fatores}`, `{trechos}`. Qualquer mudança de regra = novo arquivo, com o motivo anotado nas notas.
- LLM: **Gemini** via `google-genai`, chave `GOOGLE_API_KEY` no `.env`, **saída estruturada** no formato `RespostaLLM`. Timeout de **20 s**.
- `gerar_parecer(saida_prever) -> Parecer`: valida a entrada → escolhe a recomendação → revisão manual? template : (busca → prompt → LLM → `conferir_parecer`) → falhou? template → preenche `contrato_id`, `recomendacao`, `origem`, `versao_prompt`, `gerado_em` (−03:00).

## Checagem (`conferir_parecer`)

Entrada válida (`EntradaPrever`; inválida → revisão manual) · resposta válida (`RespostaLLM`) · cada valor de `numeros_citados` igual ao da entrada e cada número do texto ligado a um valor recebido (tolerância **0,051 pp**) · todo `trecho_id` entre os recuperados · nenhuma palavra proibida · nenhum atributo sensível · tamanho do resumo e dos pontos. **Qualquer falha → template.**

## Template de reserva

Usado em revisão manual, falha da API, timeout > 20 s, JSON inválido ou checagem reprovada. Texto só com faixa, situação, números formatados e até 3 rótulos de motivos (em revisão manual, só o juro cobrado). `origem: "template"`, `versao_prompt: "template_v1"`, `fontes: []`, mesma recomendação da tabela, fuso −03:00.

## Avaliação (`genai/avaliacao/CRITERIOS.md`, critérios definidos **antes** dos resultados)

20 casos: 5 acima, 4 abaixo, 4 dentro, 2 revisão manual, 5 difíceis (motivo com gênero, número extremo, trecho irrelevante). Critérios: recuperação no top 3 (meta ≥ 80%; a busca v1 atinge 8/10), fidelidade, consistência numérica (por código), citação correta, alucinação (meta zero na demo), regras, clareza (1–5). Cada caso rodado 2 vezes.

## Pronto quando

`tests/genai/` passa: `test_checagem`, `test_conferencia` (números, fontes, tamanho), `test_regras` (palavras e atributos), `test_template` (recomendação por situação, sem LLM em revisão manual), `test_prompt`. A avaliação dos 20 casos está registrada.

## Estado em 06/11/2026

- **[PRONTO]** normas, divisão, indexação, busca v1, checagem, template, prompt v1 + `montar_mensagens`, teste da chave do Gemini.
- **[EM ANDAMENTO] (Maria, até 08/11)** `gerar_parecer()`; avaliação dos 20 casos.
- **[EM ANDAMENTO] (Maria + Yasmin)** `contexto_mercado` (ver `contratos_dados`, seção 3).
- **[A DECIDIR]** `REGRAS_PARECER.md` v1.3 aguardando o grupo; saída do `FORMATO_JSON.md` aguardando a Yasmin.
- Integração: a API hoje chama `montar_template` em `_parecer()`; trocar por `gerar_parecer()` é uma linha (ver `regras_negocio/api`).
