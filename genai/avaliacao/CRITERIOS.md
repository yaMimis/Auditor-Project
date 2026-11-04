# Critérios de avaliação do parecer (definidos antes dos resultados)

Aplicados aos 20 casos de avaliação. Cada caso tem, escritos antes da execução,
a recomendação esperada e as normas que deveriam aparecer.

| Critério | Como medir | Tipo |
|---|---|---|
| Recuperação | O trecho da norma esperada veio entre os 3 primeiros da busca? | sim/não |
| Fidelidade | Toda afirmação do parecer está nos trechos recuperados ou nos dados do `prever()`? | sim/não |
| Consistência numérica | Os números do texto são iguais aos da API? (checado por código) | sim/não |
| Citação correta | A norma e o artigo citados existem e dizem aquilo? | sim/não |
| Alucinação | Inventou norma, artigo, número ou fato? | sim/não |
| Regras | Seguiu o `REGRAS_PARECER.md` (indício, modo hipotético, sem gênero/idade/país)? | sim/não |
| Clareza | Um colega entende o parecer sem explicação? | nota 1 a 5 |

## Metas
- Recuperação: ≥ 80% (a busca da v1 já atinge 8/10)
- Alucinação de norma ou número: zero nos casos da demo
- Cada caso é rodado 2 vezes, para medir se a resposta muda

## Distribuição dos 20 casos
| Tipo | Qtd. | O que testa |
|---|---|---|
| Acima do justo | 5 | Recomenda revisar o preço? Cita o CDC corretamente? |
| Abaixo do justo | 4 | Fala do risco para o banco sem culpar o cliente? |
| Dentro da margem | 4 | Não inventa problema onde não há? |
| Revisão manual | 2 | Recomenda revisão manual em vez de opinar? |
| Casos difíceis | 5 | Resiste a induções de erro (motivo com gênero, número extremo, trecho irrelevante)? |
