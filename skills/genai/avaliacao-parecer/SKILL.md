---
name: auditor-avaliacao-parecer
description: Aplique ao avaliar o parecer do Auditor de Preço Justo antes de trocar o prompt, o modelo do Gemini ou a busca — os 20 casos, critérios definidos antes dos resultados, avaliar.py, métricas e revisão humana.
---

# Avaliação do parecer

Antes de trocar o prompt, o modelo do Gemini ou a busca, avalie o parecer seguindo estas regras (`genai/avaliacao/`). Defina os critérios **antes** de ver os resultados (`genai/avaliacao/CRITERIOS.md`). Siga também as skills `auditor-parecer` e `auditor-normas-rag`. Dona: Maria.

## Contexto

Medir se o parecer é **certo, fiel às normas e claro** antes de qualquer mudança chegar à demo, e registrar cada versão para comparar.

## Arquivos

`genai/avaliacao/CRITERIOS.md`, `montar_casos.py` (monta os casos e as normas aceitas por situação), `casos_avaliacao.json`, `avaliar.py`, `resultados_<versão>_<modelo>.json` e `.md` (v2, v3 e v4); `tests/genai/test_avaliacao.py`.

## Regras

20 casos: 5 acima, 4 abaixo, 4 dentro, 2 revisão manual, 5 difíceis (motivo com gênero, número extremo, trecho irrelevante, revisão manual prevalecendo, país no rótulo). Critérios: recuperação no top 3 (meta ≥ 80%; a busca v1 atingiu 8/10 e a v4, 16/16), fidelidade, consistência numérica (por código), citação correta, alucinação (meta zero na demo), regras, clareza (1–5). Cada caso rodado 2 vezes.

- Rodar (com o banco indexado e a chave): `python -m genai.avaliacao.avaliar`, que grava `resultados_<versão>_<modelo>.json` e `.md`; `--relatorio` refaz o `.md` a partir do JSON da versão e do modelo atuais.
- **Atenção:** rodar de novo ou usar `--relatorio` **reescreve o `.md` do zero e apaga a revisão humana**. Antes, faça o commit da revisão; numa versão já revisada, não rode de novo com o mesmo prompt e modelo.
- As normas aceitas por situação ficam em `montar_casos.py` e só mudam **antes** de rodar uma versão.
- Métricas por código além dos critérios: fonte específica por situação (sem contar a LGPD art. 20, que entra em todos os casos), citações da LGPD art. 20, recusas por palavra e por artigo.
- Resultado da v4 (09/11): recomendação 40/40, sem palavra proibida 40/40, mesma resposta nas 2 rodadas 16/20, fonte específica 8/8 no caso "abaixo" e 1/9 no "acima" (as normas tratam de transparência, não de teto de juros). Revisão humana (10/11, 17 pareceres): fidelidade 17/17, alucinação 0/17, citação correta 7/8, clareza média 3,6. As duas quedas para o template (C13 na v3, C03 na v4) foram timeouts do Gemini.
- Na v4, "fontes dentro das normas aceitas" dá 32/33 por causa do C03: ele citou o CDC art. 54-D, II corretamente (sim na revisão humana), mas esse artigo não estava entre as normas aceitas do caso "acima". A métrica está certa: ela mede o gabarito definido antes de rodar, não se a citação está correta.
- Os casos e as normas aceitas **não mudam depois de rodar** uma versão: mudar o gabarito depois do resultado invalida a comparação. Os casos com país no rótulo ("Estônia") ficam como estão: testam se o código retira o país.
- A revisão humana é do **texto original do LLM**, antes dos ajustes de estilo; não reavaliar com os ajustes e dizer que o modelo melhorou.
- Relatar a fonte específica **por situação**: no caso "dentro" não há problema a apontar, e no "acima" muitas vezes não há norma pertinente (o sistema prefere não citar a citar errado).

## Como construir

1. Banco indexado (`auditor-normas-rag`), `DATABASE_URL` e `GOOGLE_API_KEY` definidos.
2. Antes de rodar uma versão nova, decidir e registrar se as normas aceitas mudam (`montar_casos.py`).
3. `python -m genai.avaliacao.avaliar` (cerca de 5 a 10 minutos: há uma pausa de 4 s entre as chamadas, configurável por `PAUSA_ENTRE_CHAMADAS`, para não estourar o limite do plano gratuito do Gemini).
4. Preencher a revisão humana no `.md` (fidelidade, citação correta, alucinação, clareza 1–5), com legenda, resumo e observações logo abaixo da tabela.
5. Comparar com a versão anterior e anotar o motivo da próxima versão nas notas do prompt.

## Ao terminar

Confirme, antes de dar a tarefa por pronta:

O `.md` da versão tem as métricas por código e a revisão humana preenchida; recomendação certa e "sem palavra proibida" em 100%; alucinação zero na revisão humana; `tests/genai/test_avaliacao.py` passa.

## Situação atual (10/11/2026)

Não refaça o que está **[PRONTO]**; não altere o que está **[EM ANDAMENTO]** por outra pessoa; em **[A DECIDIR]** ou **[A CONFIRMAR]**, use a escolha padrão e avise.

- **[PRONTO]** critérios, 20 casos, `avaliar.py` com `--relatorio`, avaliações v2, v3 e v4, revisão humana da v4.
