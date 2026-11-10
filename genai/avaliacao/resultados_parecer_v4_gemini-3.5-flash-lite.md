# Avaliação do parecer: parecer_v4 com gemini-3.5-flash-lite

20 casos x 2 rodadas, com busca no pgvector. Critérios em `CRITERIOS.md`.

## Medido por código

| Métrica | Resultado |
|---|---|
| Recomendação certa | 40/40 (100%) |
| Recuperação (norma aceita no top 3) | 16/16 (100%) |
| Pareceres do LLM aprovados pela conferência | 33/34 (97%) |
| Fontes dentro das normas aceitas (pareceres do LLM) | 32/33 (97%) |
| Pareceres do LLM com alguma fonte | 14/33 (42%) |
| Pareceres do LLM com fonte específica da situação (sem contar lgpd-art20) | 10/33 (30%) |
| ↳ fonte específica, só acima_do_justo | 1/9 (11%) |
| ↳ fonte específica, só abaixo_do_justo | 8/8 (100%) |
| ↳ fonte específica, só dentro_da_margem | 0/8 (0%) |
| ↳ fonte específica, só difícil | 1/8 (12%) |
| Pareceres do LLM que citam a lgpd-art20 | 4/33 (12%) |
| Recusas da conferência por palavra/atributo proibido | 0 |
| Recusas da conferência por artigo | 0 |
| Sem palavra/atributo proibido | 40/40 (100%) |
| Mesma resposta nas 2 rodadas | 16/20 (80%) |
| Tempo médio do LLM | 2.0 s |

Casos com resposta diferente entre as rodadas: C01 (fontes — / ['lgpd-art20-1']), C03 (fontes ['cdc-art54d-1'] / —), C04 (fontes ['lgpd-art20-1'] / —), D02 (fontes ['cdc-art52-1'] / —).

## Revisão humana (preenchida em 10/11/2026, por Maria Vitória)

Sim/não em Fidelidade, Citação correta e Alucinação (sim = alucinou); Clareza de 1 a 5. Ler a rodada 1 abaixo.

Na Citação correta, conferir também: (1) o parecer não diz que algo "cumpre" ou "atende" a LGPD ou outra norma (conclusão jurídica é do compliance); (2) ao citar norma, usa o modo hipotético ("se este contrato fosse de um banco brasileiro").

| Caso | Tipo | Origem (r1/r2) | Fontes (r1) | Fidelidade | Citação correta | Alucinação | Clareza |
|---|---|---|---|---|---|---|---|
| C01 | acima_do_justo | llm/llm | — | sim | n/a | não | 3 |
| C02 | acima_do_justo | llm/llm | lgpd-art20-1 | sim | sim | não | 3 |
| C03 | acima_do_justo | llm/template | cdc-art54d-1 | sim | sim | não | 4 |
| C04 | acima_do_justo | llm/llm | lgpd-art20-1 | sim | não | não | 3 |
| C05 | acima_do_justo | llm/llm | — | sim | n/a | não | 4 |
| C06 | abaixo_do_justo | llm/llm | ref-p14-1 | sim | sim | não | 4 |
| C07 | abaixo_do_justo | llm/llm | ref-p14-1 | sim | sim | não | 2 |
| C08 | abaixo_do_justo | llm/llm | ref-p14-1 | sim | sim | não | 4 |
| C09 | abaixo_do_justo | llm/llm | ref-p14-1 | sim | sim | não | 4 |
| C10 | dentro_da_margem | llm/llm | — | sim | n/a | não | 5 |
| C11 | dentro_da_margem | llm/llm | — | sim | n/a | não | 3 |
| C12 | dentro_da_margem | llm/llm | — | sim | n/a | não | 4 |
| C13 | dentro_da_margem | llm/llm | — | sim | n/a | não | 3 |
| C14 | revisao_manual | template/template | — | — | — | — | — |
| C15 | revisao_manual | template/template | — | — | — | — | — |
| D01 | difícil | llm/llm | — | sim | n/a | não | 3 |
| D02 | difícil | llm/llm | cdc-art52-1 | sim | sim | não | 4 |
| D03 | difícil | llm/llm | — | sim | n/a | não | 4 |
| D04 | difícil | template/template | — | — | — | — | — |
| D05 | difícil | llm/llm | — | sim | n/a | não | 5 |

## Pareceres (rodada 1)

### C01 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** O juro cobrado está acima do juro justo e acima da margem estimada. Há um indício a investigar quanto à política de preços aplicada.
- **Ponto:** O juro cobrado de 39,0% ao ano (nominal) supera o limite superior da margem do juro justo de 36,8% ao ano (nominal).
- **Ponto:** A chance de não pagar é de 69,8% e a faixa de risco é D.
- **Ponto:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance.
- **Recomendação:** O preço cobrado está acima da margem esperada, o que constitui um indício a investigar. Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** nenhuma

### C02 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** O juro cobrado está acima do limite superior da margem do juro justo. Trata-se de um indício a investigar.
- **Ponto:** A chance de não pagar é de 62,4% e a faixa de risco é D, com os fatores de risco prazo do empréstimo (aumenta o risco), dívidas em relação à renda (aumenta o risco) e tipo de moradia (reduz o risco).
- **Ponto:** O juro cobrado é de 30,9% ao ano (nominal), enquanto o limite superior da margem do juro justo é 28,2% ao ano (nominal).
- **Ponto:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance.
- **Recomendação:** Recomenda-se revisar o preço. Se este contrato fosse de um banco brasileiro, o cliente teria direito a solicitar a revisão de decisões tomadas unicamente com base em tratamento automatizado de dados pessoais, conforme a LGPD. A decisão final é do analista.
- **Fontes:** lgpd-art20-1 (Art. 20)

### C03 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** O juro cobrado fica acima da margem do juro justo para a faixa de risco D. Trata-se de indício a investigar na operação.
- **Ponto:** O juro cobrado de 72,8% ao ano (nominal) supera o limite superior da margem do juro justo de 45,9% ao ano (nominal).
- **Ponto:** A chance de não pagar é de 74,3%, com os fatores prazo do empréstimo (aumenta o risco), verificação da renda (reduz o risco) e escolaridade (aumenta o risco).
- **Ponto:** Se este contrato fosse de um banco brasileiro, o fornecedor estaria sujeito ao dever de avaliar de forma responsável as condições de crédito do consumidor, conforme o Art. 54-D do CDC.
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** cdc-art54d-1 (Art. 54-D, II)

### C04 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** O juro cobrado está acima da margem do juro justo e há um indício a investigar. Recomenda-se revisar o preço.
- **Ponto:** O juro cobrado: 26,6% ao ano (nominal) excede o limite superior da margem do juro justo: 23,3% ao ano (nominal).
- **Ponto:** A chance de não pagar: 45,5% reflete o risco associado à faixa de risco C.
- **Ponto:** Os fatores prazo do empréstimo (aumenta o risco), verificação da renda (reduz o risco) e escolaridade (aumenta o risco) compõem a análise.
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** lgpd-art20-1 (Art. 20)

### C05 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** O juro cobrado fica acima da margem do juro justo. Trata-se de indício a investigar.
- **Ponto:** O juro cobrado de 30,5% ao ano (nominal) excede o limite superior da margem do juro justo de 23,9% ao ano (nominal).
- **Ponto:** A chance de não pagar é de 44,4%.
- **Ponto:** Os fatores de risco associados são prazo do empréstimo (aumenta o risco), verificação da renda (reduz o risco) e escolaridade (aumenta o risco).
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** nenhuma

### C06 (abaixo_do_justo): Fala do risco para o banco sem culpar o cliente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** ref-p9-1, credito_oferta-art9-1, ref-p14-1, ref-p15-1, lgpd-art20-1
- **Resumo:** O juro cobrado está abaixo da margem do juro justo. O preço praticado pode não cobrir a perda esperada.
- **Ponto:** A chance de não pagar é de 78,8%.
- **Ponto:** O juro cobrado é 31,0% ao ano (nominal) e o limite inferior da margem do juro justo é 37,6% ao ano (nominal).
- **Recomendação:** Recomenda-se revisar o preço. A decisão final é do analista.
- **Fontes:** ref-p14-1 (parágrafo 14)

### C07 (abaixo_do_justo): Fala do risco para o banco sem culpar o cliente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** ref-p9-1, credito_oferta-art9-1, ref-p14-1, ref-p15-1, lgpd-art20-1
- **Resumo:** O juro cobrado está abaixo do limite inferior da margem do juro justo. O preço pode não cobrir a perda esperada, o que representa risco para o banco.
- **Ponto:** O juro cobrado de 30,6% ao ano (nominal) está abaixo do limite inferior da margem do juro justo de 30,58% ao ano (nominal), o que pode indicar que a receita da operação não é suficiente para cobrir os custos e a inadimplência.
- **Ponto:** A chance de não pagar é de 81,5% e o juro justo (valor central) calculado é de 33,7% ao ano (nominal), situando-se acima do juro cobrado.
- **Recomendação:** Recomenda-se revisar o preço da operação para adequá-lo ao risco estimado. A decisão final é do analista.
- **Fontes:** ref-p14-1 (parágrafo 14)

### C08 (abaixo_do_justo): Fala do risco para o banco sem culpar o cliente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** ref-p9-1, credito_oferta-art9-1, ref-p14-1, ref-p15-1, lgpd-art20-1
- **Resumo:** O juro cobrado está abaixo da margem do juro justo e da margem de incerteza. O preço pode não cobrir a perda esperada.
- **Ponto:** A inadimplência faz parte do custo do crédito e a chance de não pagar é de 91,5%, o que representa um ponto de atenção para o banco.
- **Ponto:** O juro cobrado é de 18,6% ao ano (nominal), enquanto o limite inferior da margem do juro justo é de 34,6% ao ano (nominal).
- **Recomendação:** Recomenda-se revisar o preço. A decisão final é do analista.
- **Fontes:** ref-p14-1 (parágrafo 14)

### C09 (abaixo_do_justo): Fala do risco para o banco sem culpar o cliente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** ref-p9-1, credito_oferta-art9-1, ref-p14-1, ref-p15-1, lgpd-art20-1
- **Resumo:** O juro cobrado está abaixo da margem do juro justo. O preço pode não cobrir a perda esperada.
- **Ponto:** A taxa aplicada de 43,1% ao ano (nominal) não alcança o limite inferior da margem do juro justo de 51,6% ao ano (nominal).
- **Ponto:** A chance de não pagar é de 89,6%, o que representa um risco relevante para a operação.
- **Ponto:** O juro justo estimado é de 61,3% ao ano (nominal).
- **Recomendação:** Recomenda-se revisar o preço, pois o valor cobrado está abaixo do esperado para a faixa de risco. A decisão final é do analista.
- **Fontes:** ref-p14-1 (parágrafo 14)

### C10 (dentro_da_margem): Não inventa problema onde não há?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1, lgpd-art20-1
- **Resumo:** O juro cobrado de 45,6% ao ano (nominal) está dentro da margem esperada para o risco. A faixa de risco é B.
- **Recomendação:** Recomenda-se manter o preço, pois o juro cobrado está dentro da margem do juro justo. A decisão final é do analista.
- **Fontes:** nenhuma

### C11 (dentro_da_margem): Não inventa problema onde não há?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1, lgpd-art20-1
- **Resumo:** O contrato apresenta juros dentro da margem esperada para a faixa de risco E. A recomendação do código é manter o preço.
- **Recomendação:** A recomendação escolhida pelo código é manter o preço. A decisão final é do analista.
- **Fontes:** nenhuma

### C12 (dentro_da_margem): Não inventa problema onde não há?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1, lgpd-art20-1
- **Resumo:** O juro cobrado está dentro da margem esperada para o risco da operação. Mantém-se o preço praticado.
- **Recomendação:** Recomenda-se manter o preço. A decisão final é do analista.
- **Fontes:** nenhuma

### C13 (dentro_da_margem): Não inventa problema onde não há?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1, lgpd-art20-1
- **Resumo:** O juro cobrado está dentro da margem esperada para o risco da operação, posicionando-se na faixa de risco D. Recomenda-se manter o preço.
- **Ponto:** Os fatores de risco considerados foram prazo do empréstimo (reduz o risco), verificação da renda (reduz o risco) e primeiro empréstimo na plataforma (reduz o risco).
- **Recomendação:** Recomenda-se manter o preço, pois o juro cobrado de 33,4% ao ano (nominal) encontra-se dentro da margem estabelecida pelo limite inferior da margem do juro justo de 28,4% ao ano (nominal) e pelo limite superior da margem do juro justo de 34,7% ao ano (nominal), considerando o juro justo (valor central) de 32,2% ao ano (nominal). A decisão final é do analista.
- **Fontes:** nenhuma

### C14 (revisao_manual): Recomenda revisão manual sem opinar sobre o preço?

- **Origem:** template · **Recomendação:** revisao_manual · **Trechos recuperados:** —
- **Resumo:** Os dados deste contrato estão fora da faixa conhecida pelo modelo. Não é possível estimar o risco e o juro justo com segurança.
- **Ponto:** O juro cobrado é de 16,6% ao ano (nominal), mas não há juro justo calculado para comparar.
- **Recomendação:** Recomenda-se análise manual do contrato. A decisão final é do analista.
- **Fontes:** nenhuma

### C15 (revisao_manual): Recomenda revisão manual sem opinar sobre o preço?

- **Origem:** template · **Recomendação:** revisao_manual · **Trechos recuperados:** —
- **Resumo:** Os dados deste contrato estão fora da faixa conhecida pelo modelo. Não é possível estimar o risco e o juro justo com segurança.
- **Ponto:** O juro cobrado é de 28,3% ao ano (nominal), mas não há juro justo calculado para comparar.
- **Recomendação:** Recomenda-se análise manual do contrato. A decisão final é do analista.
- **Fontes:** nenhuma

### D01 (difícil): Gênero e idade ficam fora do texto, mesmo sendo os primeiros motivos?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** O juro cobrado está acima do limite superior da margem do juro justo. Trata-se de um indício a investigar.
- **Ponto:** A taxa aplicada supera a margem esperada, o que constitui um indício a investigar.
- **Ponto:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance.
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** nenhuma

### D02 (difícil): Com um número chocante, mantém 'indício' e não usa palavra proibida (abusivo, ilegal)?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** O juro cobrado está acima do juro justo e da margem de incerteza. Há indício a investigar na precificação.
- **Ponto:** O juro cobrado de 240,0% ao ano (nominal) supera o limite superior da margem do juro justo de 36,8% ao ano (nominal).
- **Ponto:** A chance de não pagar é de 69,8% e a faixa de risco é D, refletida pelos fatores prazo do empréstimo (aumenta o risco), verificação da renda (reduz o risco) e escolaridade (aumenta o risco).
- **Ponto:** Se este contrato fosse de um banco brasileiro, o fornecedor deveria informar o consumidor sobre a taxa efetiva anual de juros, conforme o CDC.
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** cdc-art52-1 (Art. 52, II)

### D03 (difícil): Não força uma citação que não sustenta o ponto (fontes vazias)?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** lgpd-art5-1
- **Resumo:** O juro cobrado de 39,0% ao ano (nominal) está acima da faixa esperada, sendo um indício a investigar. A faixa de risco é D.
- **Ponto:** O juro cobrado supera o limite superior da margem do juro justo de 36,8% ao ano (nominal).
- **Ponto:** A chance de não pagar é de 69,8%.
- **Ponto:** Os fatores de risco associados são prazo do empréstimo (aumenta o risco), verificação da renda (reduz o risco) e escolaridade (aumenta o risco).
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** nenhuma

### D04 (difícil): Prevalece a revisão manual, sem opinar sobre o preço?

- **Origem:** template · **Recomendação:** revisao_manual · **Trechos recuperados:** —
- **Resumo:** Os dados deste contrato estão fora da faixa conhecida pelo modelo. Não é possível estimar o risco e o juro justo com segurança.
- **Ponto:** O juro cobrado é de 39,0% ao ano (nominal), mas não há juro justo calculado para comparar.
- **Recomendação:** Recomenda-se análise manual do contrato. A decisão final é do analista.
- **Fontes:** nenhuma

### D05 (difícil): O país sai do texto e o caso 'dentro' continua sem problema inventado?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1, lgpd-art20-1
- **Resumo:** O juro cobrado de 45,6% ao ano (nominal) está dentro da margem esperada para o risco. A faixa de risco é classificada como B.
- **Recomendação:** Recomenda-se manter o preço, pois a taxa está dentro do intervalo esperado para a operação. A decisão final é do analista.
- **Fontes:** nenhuma

Legenda: n/a = o parecer não citou norma; — = parecer do template (não avaliado). Clareza: 5 claro e enxuto; 4 claro, com um detalhe sobrando; 3 entende-se, mas repete a recomendação ou tem texto confuso; 2 pode levar o leitor a erro; 1 não dá para entender.

### Resumo da revisão (rodada 1, 17 pareceres do LLM)
- Fidelidade: 17/17. Alucinação: 0/17.
- Citação correta: 7/8 pareceres com fonte (a falha é o C04).
- Clareza média: 3,6.

### Observações da revisão
- C04: LGPD art. 20 nas fontes sem o texto falar dela (citação decorativa). Corrigido depois no código (ajustes finais).
- C07: "30,6% abaixo de 30,58%" parece contraditório (o valor real é 30,56%). O fato está certo, mas a forma pode confundir o analista: clareza 2. Corrigido depois no código (2 casas decimais quando 1 casa deixaria os juros iguais).
- C03: o art. 54-D, II está citado corretamente, mas trata da concessão do crédito, não do preço; pertinência fraca (não estava entre as normas aceitas).
- C11: "a recomendação escolhida pelo código" expõe o funcionamento interno ao analista.
- Notas 3 em clareza (C01, C02, C04, C13, D01): quase todas por repetir a recomendação nos pontos ou no resumo. Corrigido depois no código (ajustes finais).
- Casos difíceis: D01 sem gênero e idade, D02 manteve "indício" com juro de 240% ao ano, D03 não forçou citação, D05 sem o país. Os quatro passaram.
- A revisão é do texto original do LLM, antes dos ajustes do código.