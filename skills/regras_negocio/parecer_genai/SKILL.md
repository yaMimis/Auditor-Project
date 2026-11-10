---
name: auditor-parecer-genai
description: Use para construir ou alterar o parecer automatizado do Auditor de Preço Justo — quem decide o quê, linguagem, números, recomendação escolhida pelo código, prompt versionado, cadeia LCEL com o Gemini, conferência por código, ajustes de estilo e template de reserva. Normas e busca ficam em normas_rag; avaliação em avaliacao_parecer.
---

# Parecer com GenAI

> Leia antes: `regras_negocio/governanca`, `regras_negocio/contratos_dados`. Junto: `regras_negocio/normas_rag` (busca) e `regras_negocio/avaliacao_parecer` (avaliação). Dono: Maria (GenAI). Documentos do dono: `genai/REGRAS_PARECER.md` (v1.7), `genai/FORMATO_JSON.md` (v1.5).

## Objetivo

Transformar a saída do `prever()` num **parecer curto, em português, apoiado em normas**, cujos números e regras são **conferidos por código**, com reserva sem IA quando algo falhar.

## Arquivos

`genai/src/checagem.py` (pydantic, `conferir_parecer`, `ajustar_resposta`, formatação dos números), `template.py` (`montar_template`, `escolher_recomendacao`), `prompt.py` (`montar_mensagens`, `VERSAO_PROMPT`), `cadeia.py` (`gerar_parecer`, `buscar_trechos`, `carregar_modelo_embeddings`), `testar_llm.py`; `genai/prompts/parecer_v1.md` a `parecer_v4.md`; `tests/genai/`. As normas e a busca estão em `normas_rag`; a avaliação, em `avaliacao_parecer`.

## Quem decide o quê

| Quem | Faz |
|---|---|
| `prever()` | todos os números e a marcação de revisão manual |
| Código da cadeia | escolhe a recomendação, decide LLM × template, formata números, busca normas, confere o resultado, faz os ajustes de estilo, escreve `contexto_mercado` |
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
- Só podem aparecer: PD, juro cobrado, juro justo, mínimo e máximo da margem (e a faixa). O LLM **copia** os números já formatados ("24,9% ao ano (nominal)"); não recalcula, não arredonda, não calcula diferenças. Campo `null` nunca é citado. Todo número do texto entra em `numeros_citados` com o valor exato.
- Juros com **1 casa decimal**; com **2** quando dois juros diferentes ficariam iguais com 1 casa (ex.: 30,56% e 30,58%, que virariam "30,6% abaixo de 30,6%"). Vale para o prompt e para o template (`casas_decimais`).
- Unidade: `UNIDADE_JURO = "ao ano (nominal)"` (mensal = anual ÷ 12, como o Bondora e o `prever()`).
- Não falar de CET, tarifas, encargos ou média de mercado. **Números do REF nunca aparecem** no parecer (v1.3): os trechos do REF só explicam a composição do custo do crédito.
- A média de mercado do BC vai só em `contexto_mercado`, uma **frase fixa escrita pelo código** (série 20742, efetiva, convertida para nominal: 12 × ((1 + e)^(1/12) − 1)); o LLM nunca a escreve. Sem o dado (antes de 03/2011) → `null`.
- Nenhuma regra do prompt nomeia um artigo de lei (v4): na v3, o exemplo "art. 6º, III" virou alucinação.

## Ética e privacidade

- Nada de identificador ao LLM (nem `contrato_id`, nem `versao_modelo`); o código reinsere.
- Gênero, idade e país nunca aparecem; `motivos_permitidos()` filtra motivos sensíveis antes do prompt e tira o país entre parênteses dos rótulos (ex.: "score de crédito (Estônia)").

## Normas e busca

Detalhes em `regras_negocio/normas_rag`. O que importa aqui: a cadeia recebe até 5 trechos (`norma`, `artigo`, `trecho_id`, `texto`); o LLM cita só o que recebeu; sem trecho pertinente → `fontes: []`, e a tela mostra "Não encontrei base normativa para este caso." Sem banco, o parecer sai sem fontes e nunca falha.

## Prompt e LLM

- Prompt versionado em `genai/prompts/parecer_vN.md`; `prompt.py` lê só as seções "Mensagem do sistema" e "Mensagem do usuário" e preenche `{situacao}`, `{recomendacao}`, `{faixa}`, `{numeros}`, `{fatores}`, `{trechos}`. Qualquer mudança de regra = novo arquivo, com o motivo anotado nas notas.
- Versão atual: **`parecer_v4`** (`VERSAO_PROMPT` em `prompt.py`). A v1, a v2 e a v3 continuam no repositório; o motivo de cada versão está nas notas do arquivo.
- LLM: **Gemini** (`MODELO_LLM`, padrão `gemini-3.5-flash-lite`; plano B `gemini-3.1-flash-lite`) via **LangChain** (`langchain-google-genai`, `ChatGoogleGenerativeAI.with_structured_output`), chave `GOOGLE_API_KEY` no `.env`, **saída estruturada** num esquema plano (`_RespostaGemini`: o Gemini não aceita dicionário livre) convertida para `RespostaLLM`. **10 s por tentativa** (mínimo aceito pelo Gemini), **2 tentativas** (a 2ª só em erro temporário, como 503).
- **Cadeia LCEL, fixa, sem agente e sem memória:** `busca_normas | monta_prompt | gemini | conferencia` (`RunnableLambda`). Cada parecer depende só do contrato. Sem LangChain instalado, `_CadeiaSemLangChain` roda os mesmos passos em ordem. Os imports do LangChain e do `sentence-transformers` ficam dentro das funções, para o CI testar sem torch.
- `gerar_parecer(saida_prever) -> dict`: valida a entrada → escolhe a recomendação → revisão manual? template : cadeia → erro ou conferência reprovada? template : ajustes de estilo → preenche `contrato_id`, `recomendacao`, `origem`, `versao_prompt`, `gerado_em` (−03:00), `contexto_mercado`. **Nunca lança exceção.**
- A API carrega o modelo de embeddings na subida (`carregar_modelo_embeddings()`), para a 1ª busca não demorar.

## Checagem (`conferir_parecer`)

Entrada válida (`EntradaPrever`; inválida → revisão manual) · resposta válida (`RespostaLLM`) · cada valor de `numeros_citados` igual ao da entrada e cada número do texto ligado a um valor recebido (tolerância **0,051 pp**) · todo `trecho_id` entre os recuperados · **artigos** (v4): o artigo de cada fonte é o do próprio trecho, e todo "art. N" do texto é o artigo de um trecho recuperado (compara número e letra, ignora inciso; o REF não tem artigo; "Lei nº" e "Resolução" não contam) · nenhuma palavra proibida · nenhum atributo sensível · tamanho do resumo e dos pontos. **Qualquer falha → template.**

## Ajustes de estilo (`ajustar_resposta`, depois da conferência)

Só rodam **depois** que a conferência aprova, que sempre vê a resposta original do LLM. **Só tiram, nunca acrescentam**, e não mandam para o template:
- pontos de atenção que começam com "Recomenda-se" saem; frases do resumo que começam assim saem se sobrar outra frase (duas versões do prompt não resolveram a repetição);
- a LGPD art. 20 sai das fontes quando o texto não fala de revisão de decisão automatizada (citação decorativa).

O que foi ajustado vai para o log. As métricas da avaliação medem o LLM **antes** desses ajustes.

## Template de reserva

Usado em revisão manual, falha da API, timeout (2 tentativas de 10 s), JSON inválido ou conferência reprovada. Texto só com faixa, situação, números formatados e até 3 rótulos de motivos (em revisão manual, só o juro cobrado). `origem: "template"`, `versao_prompt: "template_v1"`, `fontes: []`, mesma recomendação da tabela, fuso −03:00.

## Avaliação

Antes de trocar o prompt, o modelo ou a busca, rodar a avaliação dos 20 casos (`regras_negocio/avaliacao_parecer`). Na v4: recomendação 40/40, sem palavra proibida 40/40, alucinação 0/17 na revisão humana.

## Pronto quando

`tests/genai/` passa (164 testes em 10/11, sem internet e sem banco: o LLM e a busca são trocados por versões falsas): `test_checagem`, `test_conferencia` (números, fontes, tamanho), `test_regras` (palavras e atributos), `test_template` (recomendação por situação, sem LLM em revisão manual), `test_prompt`, `test_cadeia` e `test_cadeia_langchain` (cadeia, fallback e LCEL), `test_avaliacao`, `test_ajustes_v2`, `test_v3`, `test_v4` (checagem de artigos), `test_ajustes_finais`. A avaliação está registrada (`regras_negocio/avaliacao_parecer`).

## Estado em 10/11/2026

- **[PRONTO]** checagem (com artigos), ajustes de estilo, template, prompts v1 a v4, `gerar_parecer()` em cadeia LCEL, `contexto_mercado`. Normas e busca: ver `normas_rag`; avaliação: ver `avaliacao_parecer`.
- **[PRONTO]** integração: a API chama `gerar_parecer()` e carrega o modelo de embeddings na subida; `iniciar.ps1` indexa as normas.
- **[A DECIDIR]** `REGRAS_PARECER.md` v1.7 e `FORMATO_JSON.md` v1.5 aguardando o ok do grupo.
- **[PENDENTE] (Maria, até 14/11)** cache dos pareceres dos casos da demo (`docs/ROTEIRO_DEMO.md`).
