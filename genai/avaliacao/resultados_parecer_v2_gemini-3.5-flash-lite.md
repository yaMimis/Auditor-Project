# Avaliação do parecer: parecer_v2 com gemini-3.5-flash-lite

20 casos x 2 rodadas, com busca no pgvector. Critérios em `CRITERIOS.md`.

## Medido por código

| Métrica | Resultado |
|---|---|
| Recomendação certa | 40/40 (100%) |
| Recuperação (norma aceita no top 3) | 16/16 (100%) |
| Pareceres do LLM aprovados pela conferência | 34/34 (100%) |
| Fontes dentro das normas aceitas (pareceres do LLM) | 34/34 (100%) |
| Pareceres do LLM com alguma fonte | 11/34 (32%) |
| Sem palavra/atributo proibido | 40/40 (100%) |
| Mesma resposta nas 2 rodadas | 15/20 (75%) |
| Tempo médio do LLM | 2.1 s |

Casos com resposta diferente entre as rodadas: C03 (fontes ['cdc-art52-1'] / —), C04 (fontes — / ['cdc-art52-1']), C05 (fontes — / ['cdc-art52-1']), C09 (fontes — / ['ref-p14-1', 'ref-p15-1']), D02 (fontes ['cdc-art52-1'] / —).

## Revisão humana (preencher)

Sim/não em Fidelidade, Citação correta e Alucinação (sim = alucinou); Clareza de 1 a 5. Ler a rodada 1 abaixo.

| Caso | Tipo | Origem (r1/r2) | Fontes (r1) | Fidelidade | Citação correta | Alucinação | Clareza |
|---|---|---|---|---|---|---|---|
| C01 | acima_do_justo | llm/llm | cdc-art52-1 |  |  |  |  |
| C02 | acima_do_justo | llm/llm | — |  |  |  |  |
| C03 | acima_do_justo | llm/llm | cdc-art52-1 |  |  |  |  |
| C04 | acima_do_justo | llm/llm | — |  |  |  |  |
| C05 | acima_do_justo | llm/llm | — |  |  |  |  |
| C06 | abaixo_do_justo | llm/llm | ref-p14-1 |  |  |  |  |
| C07 | abaixo_do_justo | llm/llm | — |  |  |  |  |
| C08 | abaixo_do_justo | llm/llm | — |  |  |  |  |
| C09 | abaixo_do_justo | llm/llm | — |  |  |  |  |
| C10 | dentro_da_margem | llm/llm | — |  |  |  |  |
| C11 | dentro_da_margem | llm/llm | — |  |  |  |  |
| C12 | dentro_da_margem | llm/llm | — |  |  |  |  |
| C13 | dentro_da_margem | llm/llm | — |  |  |  |  |
| C14 | revisao_manual | template/template | — |  |  |  |  |
| C15 | revisao_manual | template/template | — |  |  |  |  |
| D01 | difícil | llm/llm | cdc-art52-1 |  |  |  |  |
| D02 | difícil | llm/llm | cdc-art52-1 |  |  |  |  |
| D03 | difícil | llm/llm | — |  |  |  |  |
| D04 | difícil | template/template | — |  |  |  |  |
| D05 | difícil | llm/llm | — |  |  |  |  |

## Pareceres (rodada 1)

### C01 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art52-1, cdc-art42-1, cdc-art54b-1, credito_oferta-art7-1
- **Resumo:** O juro cobrado de 39,0% ao ano (nominal) está acima da faixa de juro justo, que tem como limite superior 36,8% ao ano (nominal). Trata-se de um indício a investigar, pois a diferença não é explicada pelo risco estimado.
- **Ponto:** O juro cobrado supera o juro justo (valor central) de 34,0% ao ano (nominal) e o limite superior da margem do juro justo de 36,8% ao ano (nominal), com base na faixa de risco D e na chance de não pagar de 69,8%.
- **Ponto:** Se este contrato fosse de um banco brasileiro, o fornecedor deveria informar prévia e adequadamente sobre a taxa efetiva anual de juros, conforme estabelece o CDC.
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** cdc-art52-1 (Art. 52, II)

### C02 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art52-1, cdc-art42-1, cdc-art54b-1, credito_oferta-art7-1
- **Resumo:** O juro cobrado de 30,9% ao ano (nominal) está acima da margem do juro justo. Trata-se de um indício a investigar.
- **Ponto:** A taxa aplicada excede o limite superior da margem do juro justo de 28,2% ao ano (nominal) e a diferença não é explicada pelo risco estimado pelo modelo na faixa de risco D.
- **Ponto:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance.
- **Recomendação:** Recomenda-se revisar o preço. A decisão final é do analista.
- **Fontes:** nenhuma

### C03 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art52-1, cdc-art42-1, cdc-art54b-1, credito_oferta-art7-1
- **Resumo:** O juro cobrado de 72,8% ao ano (nominal) está acima do juro justo (valor central) de 42,4% ao ano (nominal), além da margem de incerteza. Trata-se de um indício a investigar.
- **Ponto:** A taxa aplicada supera o limite superior da margem do juro justo de 45,9% ao ano (nominal).
- **Ponto:** Se este contrato fosse de um banco brasileiro, o fornecedor deveria, entre outros requisitos, informar prévia e adequadamente sobre a taxa efetiva anual de juros.
- **Ponto:** Os fatores de risco associados incluem prazo do empréstimo (aumenta o risco), verificação da renda (reduz o risco) e escolaridade (aumenta o risco).
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** cdc-art52-1 (Art. 52, II)

### C04 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art52-1, cdc-art42-1, cdc-art54b-1, credito_oferta-art7-1
- **Resumo:** O juro cobrado de 26,6% ao ano (nominal) está acima da faixa do juro justo, que tem como limite superior de 23,3% ao ano (nominal). Trata-se de um indício a investigar, pois a diferença não é explicada pelo risco estimado pelo modelo.
- **Ponto:** Há um indício de divergência no preço aplicado em relação ao risco estimado, estando o juro cobrado de 26,6% ao ano (nominal) acima do juro justo (valor central) de 21,6% ao ano (nominal).
- **Ponto:** Recomenda-se revisar o preço, verificando se a política de preços justifica o valor cobrado acima do limite superior da margem do juro justo de 23,3% ao ano (nominal).
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** nenhuma

### C05 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art52-1, cdc-art42-1, cdc-art54b-1, credito_oferta-art7-1
- **Resumo:** O juro cobrado de 30,5% ao ano (nominal) está acima do juro justo (valor central) de 21,5% ao ano (nominal) e acima do limite superior da margem do juro justo de 23,9% ao ano (nominal). Trata-se de um indício a investigar.
- **Ponto:** Há um indício a investigar, pois a diferença não é explicada pelo risco estimado pelo modelo na faixa de risco B.
- **Ponto:** Os fatores de risco associados são prazo do empréstimo (aumenta o risco), verificação da renda (reduz o risco) e escolaridade (aumenta o risco).
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** nenhuma

### C06 (abaixo_do_justo): Fala do risco para o banco sem culpar o cliente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** ref-p9-1, credito_oferta-art9-1, ref-p14-1, ref-p15-1
- **Resumo:** O juro cobrado de 31,0% ao ano (nominal) encontra-se abaixo do juro justo (valor central) de 40,1% ao ano (nominal). O limite inferior da margem do juro justo é de 37,6% ao ano (nominal) e o limite superior é de 43,6% ao ano (nominal), indicando que o preço aplicado está abaixo do esperado para o risco estimado.
- **Ponto:** O preço cobrado pode não cobrir a perda esperada, dado que a chance de não pagar é de 78,8%.
- **Ponto:** A operação apresenta alta chance de não pagar, impactando a cobertura da inadimplência conforme o Relatório de Estabilidade Financeira (BC, maio/2026).
- **Recomendação:** Recomenda-se revisar o preço da operação, pois a taxa aplicada está abaixo do patamar considerado adequado para cobrir o risco estimado. A decisão final é do analista.
- **Fontes:** ref-p14-1 (parágrafo 14)

### C07 (abaixo_do_justo): Fala do risco para o banco sem culpar o cliente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** ref-p9-1, credito_oferta-art9-1, ref-p14-1, ref-p15-1
- **Resumo:** O juro cobrado está abaixo do juro justo estimado, situando-se abaixo do limite inferior da margem. O contrato apresenta a faixa de risco E e a chance de não pagar de 81,5%.
- **Ponto:** O preço cobrado pode não cobrir a perda esperada, considerando os fatores de risco prazo do empréstimo (aumenta o risco), verificação da renda (aumenta o risco) e tipo de moradia (reduz o risco).
- **Recomendação:** Recomenda-se revisar o preço, pois o valor atual está abaixo da margem esperada para o risco da operação, o que pode impactar a cobertura das perdas decorrentes da inadimplência e demais custos da operação. A decisão final é do analista.
- **Fontes:** nenhuma

### C08 (abaixo_do_justo): Fala do risco para o banco sem culpar o cliente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** ref-p9-1, credito_oferta-art9-1, ref-p14-1, ref-p15-1
- **Resumo:** O juro cobrado está abaixo da margem do juro justo. Trata-se de um ponto de atenção para o banco, pois o preço pode não cobrir a perda esperada.
- **Ponto:** O juro cobrado de 18,6% ao ano (nominal) fica abaixo do juro justo (valor central) de 40,8% ao ano (nominal).
- **Ponto:** A chance de não pagar é de 91,5% e a faixa de risco é E.
- **Recomendação:** Recomenda-se revisar o preço da operação, pois a taxa aplicada está abaixo do mínimo esperado para cobrir o risco. A decisão final é do analista.
- **Fontes:** nenhuma

### C09 (abaixo_do_justo): Fala do risco para o banco sem culpar o cliente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** ref-p9-1, credito_oferta-art9-1, ref-p14-1, ref-p15-1
- **Resumo:** O juro cobrado de 43,1% ao ano (nominal) está abaixo do limite inferior da margem do juro justo de 51,6% ao ano (nominal). O preço pode não cobrir a perda esperada para a faixa de risco E.
- **Ponto:** A chance de não pagar é de 89,6%.
- **Ponto:** O juro justo central é de 61,3% ao ano (nominal) e o limite superior da margem do juro justo é de 72,0% ao ano (nominal).
- **Ponto:** Os fatores de risco associados são: verificação da renda (aumenta o risco), escolaridade (aumenta o risco), valor do empréstimo (aumenta o risco).
- **Recomendação:** Recomenda-se revisar o preço, pois a taxa cobrada encontra-se abaixo do patamar estimado pelo modelo de risco. A decisão final é do analista.
- **Fontes:** nenhuma

### C10 (dentro_da_margem): Não inventa problema onde não há?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1
- **Resumo:** O juro cobrado está dentro da margem esperada para o risco da operação, classificado na faixa de risco B. O modelo indica uma chance de não pagar de 35,7%.
- **Ponto:** A operação apresenta os seguintes fatores de risco: prazo do empréstimo (reduz o risco), verificação da renda (reduz o risco) e primeiro empréstimo na plataforma (reduz o risco).
- **Recomendação:** Recomenda-se manter o preço, pois a taxa aplicada está alinhada ao risco estimado. A decisão final é do analista.
- **Fontes:** nenhuma

### C11 (dentro_da_margem): Não inventa problema onde não há?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1
- **Resumo:** O juro cobrado está dentro da margem esperada para o risco da operação, classificado na faixa de risco E. A chance de não pagar é de 82,2%.
- **Ponto:** Os fatores de risco identificados são prazo do empréstimo, verificação da renda e valor do empréstimo.
- **Recomendação:** Recomenda-se manter o preço, pois o juro cobrado de 33,3% ao ano (nominal) está inserido entre o limite inferior da margem do juro justo de 31,8% ao ano (nominal) e o limite superior da margem do juro justo de 35,9% ao ano (nominal), alinhado ao juro justo (valor central) de 34,1% ao ano (nominal). A decisão final é do analista.
- **Fontes:** nenhuma

### C12 (dentro_da_margem): Não inventa problema onde não há?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1
- **Resumo:** O juro cobrado está dentro da margem esperada para o risco da operação. A faixa de risco é D.
- **Ponto:** Os fatores de risco associados são prazo do empréstimo (reduz o risco), verificação da renda (reduz o risco) e primeiro empréstimo na plataforma (reduz o risco).
- **Recomendação:** Recomenda-se manter o preço, pois a taxa está dentro da margem estimada para o risco. A decisão final é do analista.
- **Fontes:** nenhuma

### C13 (dentro_da_margem): Não inventa problema onde não há?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1
- **Resumo:** O juro cobrado de 33,4% ao ano (nominal) está dentro da margem esperada para o risco. A faixa de risco é D e a chance de não pagar é 70,9%.
- **Ponto:** Os fatores de risco associados são prazo do empréstimo (reduz o risco), verificação da renda (reduz o risco) e primeiro empréstimo na plataforma (reduz o risco).
- **Recomendação:** Recomenda-se manter o preço, pois o juro cobrado de 33,4% ao ano (nominal) está situado entre o limite inferior da margem do juro justo de 28,4% ao ano (nominal) e o limite superior da margem do juro justo de 34,7% ao ano (nominal), alinhado ao valor central de 32,2% ao ano (nominal). A decisão final é do analista.
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

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art52-1, cdc-art42-1, cdc-art54b-1, credito_oferta-art7-1
- **Resumo:** O juro cobrado de 39,0% ao ano (nominal) está acima da faixa de juro justo, que tem limite superior de 36,8% ao ano (nominal). Trata-se de um indício a investigar.
- **Ponto:** O juro cobrado de 39,0% ao ano (nominal) ultrapassa o limite superior da margem do juro justo de 36,8% ao ano (nominal), ficando acima do valor central de 34,0% ao ano (nominal).
- **Ponto:** A chance de não pagar é de 69,8% e a faixa de risco é D, sob os fatores de risco prazo do empréstimo (aumenta o risco), verificação da renda (reduz o risco) e escolaridade (aumenta o risco).
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. Se este contrato fosse de um banco brasileiro, o fornecedor estaria sujeito ao dever de informar adequadamente a taxa efetiva anual de juros conforme o CDC. A decisão final é do analista.
- **Fontes:** cdc-art52-1 (Art. 52, II)

### D02 (difícil): Com um número chocante, mantém 'indício' e não usa palavra proibida (abusivo, ilegal)?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art52-1, cdc-art42-1, cdc-art54b-1, credito_oferta-art7-1
- **Resumo:** O juro cobrado de 240,0% ao ano (nominal) está acima do juro justo estimado de 34,0% ao ano (nominal), além da margem de incerteza. Trata-se de um indício a investigar.
- **Ponto:** O juro cobrado passa da margem do juro justo de 36,8% ao ano (nominal), sem que a diferença seja explicada pelo risco estimado pelo modelo na faixa D.
- **Ponto:** Se este contrato fosse de um banco brasileiro, o fornecedor deveria, entre outros requisitos, informar prévia e adequadamente sobre a taxa efetiva anual de juros, conforme o CDC.
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** cdc-art52-1 (Art. 52, II)

### D03 (difícil): Não força uma citação que não sustenta o ponto (fontes vazias)?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** lgpd-art5-1
- **Resumo:** O juro cobrado de 39,0% ao ano (nominal) está acima da margem do juro justo e da faixa de risco D. Há um indício a investigar considerando a chance de não pagar de 69,8%.
- **Ponto:** O juro cobrado passa da margem do juro justo e a diferença não é explicada pelo risco estimado pelo modelo, considerando o limite superior da margem do juro justo de 36,8% ao ano (nominal).
- **Ponto:** O juro justo (valor central) é de 34,0% ao ano (nominal) e o limite inferior da margem do juro justo é 31,7% ao ano (nominal).
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** nenhuma

### D04 (difícil): Prevalece a revisão manual, sem opinar sobre o preço?

- **Origem:** template · **Recomendação:** revisao_manual · **Trechos recuperados:** —
- **Resumo:** Os dados deste contrato estão fora da faixa conhecida pelo modelo. Não é possível estimar o risco e o juro justo com segurança.
- **Ponto:** O juro cobrado é de 39,0% ao ano (nominal), mas não há juro justo calculado para comparar.
- **Recomendação:** Recomenda-se análise manual do contrato. A decisão final é do analista.
- **Fontes:** nenhuma

### D05 (difícil): O país sai do texto e o caso 'dentro' continua sem problema inventado?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1
- **Resumo:** O juro cobrado está dentro da margem esperada para o risco da operação, classificado na faixa de risco B. O modelo indica que os fatores verificação da renda, prazo do empréstimo e primeiro empréstimo na plataforma influenciam a avaliação.
- **Recomendação:** Recomenda-se manter o preço, pois a taxa está alinhada com a margem do juro justo. A decisão final é do analista.
- **Fontes:** nenhuma
