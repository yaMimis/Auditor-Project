---
name: auditor-normas-rag
description: Use para incluir, trocar ou reindexar as normas do parecer do Auditor de Preço Justo e para mexer na busca (RAG) — fontes oficiais, divisão em trechos, trecho_id, embeddings multilíngues, tabela trechos_normas no pgvector, perguntas de busca por situação e pergunta de governança.
---

# Normas e busca (RAG)

> Leia antes: `regras_negocio/governanca`. Depois: `regras_negocio/parecer_genai` (quem usa os trechos) e `regras_negocio/avaliacao_parecer` (como medir a busca). Dono: Maria (GenAI). Código: `genai/src/dividir.py`, `indexar.py`, `testar_busca.py`, `cadeia.py` (`buscar_trechos`, `carregar_modelo_embeddings`).

## Objetivo

Guardar as normas brasileiras em trechos pesquisáveis e, para cada contrato, **trazer os trechos que podem sustentar o parecer**. A busca nunca decide nada: só entrega trechos ao LLM, que cita apenas o que recebeu.

## Arquivos

`genai/normas/*.md` + `FONTES.md`; `genai/src/dividir.py` (`dividir_normas`), `indexar.py` (cria a extensão e a tabela, grava os 91 trechos), `testar_busca.py` (10 perguntas de resposta conhecida); `buscar_trechos` em `genai/src/cadeia.py`; `genai/avaliacao/resultado_busca_v1*.txt`.

## Regras

- Normas em `genai/normas/`, copiadas de fonte oficial e limpas (sem anotações, revogados ou vetados), com `FONTES.md` (arquivo, norma, artigos, URL, data de acesso):
  - `lgpd.md` Lei 13.709/2018, arts. 5º, 6º, 7º, 11, 12, 20
  - `cdc.md` Lei 8.078/1990, arts. 2º, 3º, 4º, 6º, 30, 31, 39, 42, 42-A, 46, 47, 52, 54, 54-A a 54-D, 54-F, 54-G, 104-A a 104-C
  - `cet.md` Res. CMN 4.881/2020, arts. 1º a 9º
  - `credito_oferta.md` Res. CMN 5.004/2022, arts. 1º a 9º
  - `ref.md` Relatório de Estabilidade Financeira do BC (maio/2026), seção 2.1 e apêndice, dividido por parágrafo
- **Divisão:** um trecho por artigo; longos quebrados entre incisos/parágrafos (`TAMANHO_MAXIMO = 1000`, sobra < `TAMANHO_MINIMO = 300` junta à anterior, repete `TAMANHO_CAPUT = 150` caracteres do caput).
- **`trecho_id`:** `<arquivo>-art<número>-<parte>` (`cdc-art6-1`, `cdc-art54b-1`, `lgpd-art20-1`); REF `ref-p<parágrafo>-1`. O inciso vai no campo `artigo` da fonte ("art. 6º, III").
- **Indexação:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensões) na tabela `trechos_normas` do pgvector.
- **Busca (`buscar_trechos`):** uma pergunta fixa por situação (`PERGUNTAS_BUSCA`) traz os **4** trechos mais próximos (`QUANTOS_TRECHOS`), mais **1** trecho da pergunta de governança (`PERGUNTA_GOVERNANCA`, revisão de decisões automatizadas, que traz a LGPD art. 20), sem repetir trecho. Cada trecho tem `norma`, `artigo`, `trecho_id`, `texto`. Sem banco → segue sem trechos (o parecer sai sem fontes, nunca falha).
- O LLM cita só o que recebeu. Sem trecho pertinente → `fontes: []`; a tela mostra "Não encontrei base normativa para este caso."
- **Não direcionar** a busca do caso "acima" para o CDC art. 39 (ele está indexado, mas a pergunta evita): o texto começa com "práticas abusivas", e o LLM tenderia a copiar a palavra proibida. Três trechos indexados têm palavras proibidas no texto da lei (`cdc-art6-1`, `lgpd-art6-2`, `lgpd-art20-1` § 2º): o prompt pede para não copiá-las.
- Uma norma nova só entra com fonte oficial registrada no `FONTES.md`; depois, reindexar e rodar o `testar_busca.py` de novo. O `indexar.py` apaga a tabela e grava todos os trechos de novo (não há indexação parcial), o que leva poucos segundos depois que o modelo foi baixado.

## Como construir

1. Copiar a norma da fonte oficial para `genai/normas/<arquivo>.md`, limpa, e registrar no `FONTES.md`.
2. `python genai/src/dividir.py` para conferir os trechos (contagem por norma e tamanhos).
3. Com o banco no ar e `DATABASE_URL` definida: `python genai/src/indexar.py` (na 1ª vez baixa o modelo de embeddings, ~470 MB). No ambiente da demo, o `iniciar.ps1` faz este passo.
4. `python genai/src/testar_busca.py`: meta de **8 de 10** perguntas com o artigo certo entre os 3 primeiros.
5. Mudou uma pergunta de busca? Rodar a avaliação do parecer (`regras_negocio/avaliacao_parecer`) e comparar a recuperação.

## Pronto quando

`indexar.py` grava **91 trechos** (CDC 37, LGPD 17, REF 17, Res. 4.881 9, Res. 5.004 11); `testar_busca.py` acerta pelo menos 8 de 10 (a v1 acertou 8/10); na avaliação, a recuperação fica em pelo menos 80% (na v4: 16/16). Os testes de `buscar_trechos` em `tests/genai/` passam (busca sem banco devolve lista vazia; a pergunta de governança não repete trecho).

## Estado em 10/11/2026

- **[PRONTO]** normas, `FONTES.md`, divisão, indexação, busca v1 (8/10), pergunta de governança (v3), indexação automática no `iniciar.ps1`.
