# Avaliação do parecer: parecer_v3 com gemini-3.5-flash-lite

20 casos x 2 rodadas, com busca no pgvector. Critérios em `CRITERIOS.md`.

## Medido por código

| Métrica | Resultado |
|---|---|
| Recomendação certa | 40/40 (100%) |
| Recuperação (norma aceita no top 3) | 16/16 (100%) |
| Pareceres do LLM aprovados pela conferência | 33/34 (97%) |
| Fontes dentro das normas aceitas (pareceres do LLM) | 33/33 (100%) |
| Pareceres do LLM com alguma fonte | 15/33 (45%) |
| Pareceres do LLM com fonte específica da situação (sem contar lgpd-art20) | 11/33 (33%) |
| Recusas da conferência por palavra/atributo proibido | 0 |
| Sem palavra/atributo proibido | 40/40 (100%) |
| Mesma resposta nas 2 rodadas | 15/20 (75%) |
| Tempo médio do LLM | 2.0 s |

Casos com resposta diferente entre as rodadas: C01 (fontes ['cdc-art54b-1'] / ['cdc-art52-1']), C02 (fontes — / ['lgpd-art20-1']), C07 (fontes ['ref-p14-1', 'ref-p15-1'] / ['ref-p14-1']), C13 (fontes — / —), D02 (fontes ['cdc-art52-1'] / ['lgpd-art20-1']).

## Revisão humana (preencher)

Sim/não em Fidelidade, Citação correta e Alucinação (sim = alucinou); Clareza de 1 a 5. Ler a rodada 1 abaixo.

Na Citação correta, conferir também: (1) o parecer não diz que algo "cumpre" ou "atende" a LGPD ou outra norma (conclusão jurídica é do compliance); (2) ao citar norma, usa o modo hipotético ("se este contrato fosse de um banco brasileiro").

| Caso | Tipo | Origem (r1/r2) | Fontes (r1) | Fidelidade | Citação correta | Alucinação | Clareza |
|---|---|---|---|---|---|---|---|
| C01 | acima_do_justo | llm/llm | cdc-art54b-1 |  |  |  |  |
| C02 | acima_do_justo | llm/llm | — |  |  |  |  |
| C03 | acima_do_justo | llm/llm | lgpd-art20-1 |  |  |  |  |
| C04 | acima_do_justo | llm/llm | — |  |  |  |  |
| C05 | acima_do_justo | llm/llm | — |  |  |  |  |
| C06 | abaixo_do_justo | llm/llm | ref-p14-1 |  |  |  |  |
| C07 | abaixo_do_justo | llm/llm | ref-p14-1, ref-p15-1 |  |  |  |  |
| C08 | abaixo_do_justo | llm/llm | ref-p14-1 |  |  |  |  |
| C09 | abaixo_do_justo | llm/llm | ref-p14-1 |  |  |  |  |
| C10 | dentro_da_margem | llm/llm | — |  |  |  |  |
| C11 | dentro_da_margem | llm/llm | — |  |  |  |  |
| C12 | dentro_da_margem | llm/llm | — |  |  |  |  |
| C13 | dentro_da_margem | llm/template | — |  |  |  |  |
| C14 | revisao_manual | template/template | — |  |  |  |  |
| C15 | revisao_manual | template/template | — |  |  |  |  |
| D01 | difícil | llm/llm | — |  |  |  |  |
| D02 | difícil | llm/llm | cdc-art52-1 |  |  |  |  |
| D03 | difícil | llm/llm | — |  |  |  |  |
| D04 | difícil | template/template | — |  |  |  |  |
| D05 | difícil | llm/llm | — |  |  |  |  |

## Pareceres (rodada 1)

### C01 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** O juro cobrado está acima do limite superior da margem do juro justo. Trata-se de um indício a investigar.
- **Ponto:** O juro cobrado de 39,0% ao ano (nominal) supera o limite superior da margem do juro justo de 36,8% ao ano (nominal).
- **Ponto:** Recomenda-se revisar se este contrato fosse de um banco brasileiro, conforme o CDC, art. 6º, III.
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** cdc-art54b-1 (art. 6º, III)

### C02 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** O juro cobrado está acima do juro justo e ultrapassa o limite superior da margem do juro justo. Há indício a investigar na formação do preço.
- **Ponto:** O juro cobrado é de 30,9% ao ano (nominal), enquanto o limite superior da margem do juro justo é de 28,2% ao ano (nominal).
- **Ponto:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance.
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** nenhuma

### C03 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** O juro cobrado de 72,8% ao ano (nominal) está acima do limite superior da margem do juro justo de 45,9% ao ano (nominal). Há indício a investigar quanto à adequação da taxa aplicada à faixa de risco D.
- **Ponto:** O juro cobrado supera a margem esperada, o que constitui um indício a investigar.
- **Ponto:** Recomenda-se revisar o preço aplicado em relação ao risco estimado de inadimplência de 74,3%.
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** lgpd-art20-1 (Art. 20)

### C04 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** O juro cobrado: 26,6% ao ano (nominal) está acima do limite superior da margem do juro justo: 23,3% ao ano (nominal). Há indício de preço desalinhado em relação ao risco estimado.
- **Ponto:** Existe um indício de divergência entre o preço aplicado e a faixa esperada para a faixa de risco C.
- **Ponto:** Recomenda-se revisar o preço para verificar se a política comercial justifica o patamar adotado.
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** nenhuma

### C05 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** O juro cobrado está acima do juro justo e ultrapassa o limite superior da margem do juro justo. Recomenda-se revisar o preço.
- **Ponto:** Há um indício a investigar, pois a diferença não é explicada pelo risco estimado pelo modelo.
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** nenhuma

### C06 (abaixo_do_justo): Fala do risco para o banco sem culpar o cliente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** ref-p9-1, credito_oferta-art9-1, ref-p14-1, ref-p15-1, lgpd-art20-1
- **Resumo:** O juro cobrado de 31,0% ao ano (nominal) está abaixo do juro justo (valor central) de 40,1% ao ano (nominal). O preço pode não cobrir a perda esperada.
- **Ponto:** A chance de não pagar é de 78,8%, indicando que o preço pode não cobrir a perda esperada.
- **Ponto:** O juro cobrado de 31,0% ao ano (nominal) fica abaixo do limite inferior da margem do juro justo de 37,6% ao ano (nominal).
- **Recomendação:** Recomenda-se revisar o preço, pois o juro cobrado está abaixo da margem esperada e pode não cobrir os custos e a inadimplência. A decisão final é do analista.
- **Fontes:** ref-p14-1 (parágrafo 14)

### C07 (abaixo_do_justo): Fala do risco para o banco sem culpar o cliente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** ref-p9-1, credito_oferta-art9-1, ref-p14-1, ref-p15-1, lgpd-art20-1
- **Resumo:** O juro cobrado de 30,6% ao ano (nominal) está abaixo do juro justo de 33,7% ao ano (nominal), com chance de não pagar estimada em 81,5%. Se este contrato fosse de um banco brasileiro, o preço cobrado estaria abaixo do limite inferior da margem do juro justo de 30,58% ao ano (nominal).
- **Ponto:** O preço cobrado pode não cobrir a perda esperada e as despesas administrativas.
- **Ponto:** A inadimplência e o custo de captação fazem parte do custo do crédito.
- **Recomendação:** Recomenda-se revisar o preço. A decisão final é do analista.
- **Fontes:** ref-p14-1 (parágrafo 14), ref-p15-1 (parágrafo 15)

### C08 (abaixo_do_justo): Fala do risco para o banco sem culpar o cliente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** ref-p9-1, credito_oferta-art9-1, ref-p14-1, ref-p15-1, lgpd-art20-1
- **Resumo:** O juro cobrado de 18,6% ao ano (nominal) encontra-se abaixo do juro justo (valor central) de 40,8% ao ano (nominal). A chance de não pagar é de 91,5%.
- **Ponto:** O preço cobrado pode não cobrir as perdas decorrentes do não pagamento de dívidas ou juros, o que representa um ponto de atenção para o banco.
- **Ponto:** A inadimplência faz parte do custo do crédito e deve ser considerada na precificação.
- **Recomendação:** Recomenda-se revisar o preço, pois a taxa está abaixo do esperado para o nível de risco. A decisão final é do analista.
- **Fontes:** ref-p14-1 (parágrafo 14)

### C09 (abaixo_do_justo): Fala do risco para o banco sem culpar o cliente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** ref-p9-1, credito_oferta-art9-1, ref-p14-1, ref-p15-1, lgpd-art20-1
- **Resumo:** O juro cobrado de 43,1% ao ano (nominal) está abaixo do juro justo (valor central) de 61,3% ao ano (nominal). O preço pode não cobrir a perda esperada, o que é um ponto de atenção para o banco.
- **Ponto:** O juro cobrado fica abaixo do limite inferior da margem do juro justo de 51,6% ao ano (nominal).
- **Ponto:** A chance de não pagar é de 89,6%, indicando que a perda estimada é alta para o nível de preço definido.
- **Recomendação:** Recomenda-se revisar o preço, pois a taxa aplicada está abaixo do patamar adequado para o risco estimado da faixa E. A decisão final é do analista.
- **Fontes:** ref-p14-1 (parágrafo 14)

### C10 (dentro_da_margem): Não inventa problema onde não há?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1, lgpd-art20-1
- **Resumo:** O juro cobrado de 45,6% ao ano (nominal) está dentro da margem esperada para o risco. Os fatores de risco identificados foram prazo do empréstimo (reduz o risco), verificação da renda (reduz o risco) e primeiro empréstimo na plataforma (reduz o risco).
- **Recomendação:** Recomenda-se manter o preço, pois a taxa está alinhada com a faixa de risco B e o limite inferior da margem do juro justo de 44,4% ao ano (nominal) e o limite superior da margem do juro justo de 65,9% ao ano (nominal). A decisão final é do analista.
- **Fontes:** nenhuma

### C11 (dentro_da_margem): Não inventa problema onde não há?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1, lgpd-art20-1
- **Resumo:** O juro cobrado está dentro da margem esperada para o risco da operação. A recomendação é manter o preço.
- **Recomendação:** Recomenda-se manter o preço, pois a taxa está alinhada ao risco estimado. A decisão final é do analista.
- **Fontes:** nenhuma

### C12 (dentro_da_margem): Não inventa problema onde não há?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1, lgpd-art20-1
- **Resumo:** O juro cobrado está dentro da margem esperada para o risco da operação. Recomenda-se manter o preço.
- **Recomendação:** Recomenda-se manter o preço. A decisão final é do analista.
- **Fontes:** nenhuma

### C13 (dentro_da_margem): Não inventa problema onde não há?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1, lgpd-art20-1
- **Resumo:** O juro cobrado está dentro da margem esperada para o risco da operação, que se encontra na faixa de risco D. Recomenda-se manter o preço.
- **Recomendação:** Recomenda-se manter o preço, pois a taxa está alinhada com o risco estimado. A decisão final é do analista.
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
- **Ponto:** A taxa de juro aplicada passa da margem esperada para a faixa de risco D.
- **Ponto:** Recomenda-se revisar o preço para verificar se a política comercial justifica a diferença.
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** nenhuma

### D02 (difícil): Com um número chocante, mantém 'indício' e não usa palavra proibida (abusivo, ilegal)?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** O juro cobrado está acima do limite superior da margem do juro justo. Trata-se de um indício a investigar.
- **Ponto:** O juro cobrado de 240,0% ao ano (nominal) excede o limite superior da margem do juro justo de 36,8% ao ano (nominal).
- **Ponto:** Se este contrato fosse de um banco brasileiro, o fornecedor deveria prestar informações claras e adequadas sobre as taxas praticadas.
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** cdc-art52-1 (Art. 52, II)

### D03 (difícil): Não força uma citação que não sustenta o ponto (fontes vazias)?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** lgpd-art5-1
- **Resumo:** O juro cobrado está acima do juro justo, além da margem de incerteza. Trata-se de indício a investigar na formação do preço.
- **Ponto:** O juro cobrado de 39,0% ao ano (nominal) supera o limite superior da margem do juro justo de 36,8% ao ano (nominal).
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
- **Resumo:** O juro cobrado de 45,6% ao ano (nominal) encontra-se dentro da margem esperada para o risco da faixa B. Recomenda-se manter o preço.
- **Ponto:** Os fatores de risco considerados foram prazo do empréstimo (reduz o risco), verificação da renda (reduz o risco) e primeiro empréstimo na plataforma (reduz o risco).
- **Recomendação:** Recomenda-se manter o preço, pois o juro cobrado de 45,6% ao ano (nominal) está contido entre o limite inferior da margem do juro justo de 44,4% ao ano (nominal) e o limite superior da margem do juro justo de 65,9% ao ano (nominal). A decisão final é do analista.
- **Fontes:** nenhuma
