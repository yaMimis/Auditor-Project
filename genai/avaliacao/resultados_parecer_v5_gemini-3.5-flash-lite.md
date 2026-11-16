# Avaliação do parecer: parecer_v5 com gemini-3.5-flash-lite

20 casos x 2 rodadas, com busca no pgvector. Critérios em `CRITERIOS.md`.

## Medido por código

| Métrica | Resultado |
|---|---|
| Recomendação certa | 40/40 (100%) |
| Recuperação (norma aceita no top 3) | 16/16 (100%) |
| Pareceres do LLM aprovados pela conferência | 33/34 (97%) |
| Fontes dentro das normas aceitas (pareceres do LLM) | 33/33 (100%) |
| Pareceres do LLM com alguma fonte | 21/33 (64%) |
| Pareceres do LLM com fonte específica da situação (sem contar lgpd-art20) | 21/33 (64%) |
| ↳ fonte específica, só acima_do_justo | 10/10 (100%) |
| ↳ fonte específica, só abaixo_do_justo | 8/8 (100%) |
| ↳ fonte específica, só dentro_da_margem | 0/8 (0%) |
| ↳ fonte específica, só difícil | 3/7 (43%) |
| Pareceres do LLM que citam a lgpd-art20 | 0/33 (0%) |
| Recusas da conferência por palavra/atributo proibido | 0 |
| Recusas da conferência por artigo | 0 |
| Recomendação que fala do código ou do sistema (pareceres do LLM) | 0/33 (0%) |
| Sem palavra/atributo proibido | 40/40 (100%) |
| Mesma resposta nas 2 rodadas | 15/20 (75%) |
| Rodadas repetidas por falha do Google (503, 504, tempo) | 8 de 40 |
| Rodadas que ficaram no template por falha do Google | 1 |
| Tempo médio do LLM | 3.7 s |

Casos com resposta diferente entre as rodadas: C03 (fontes ['cdc-art54d-1'] / ['cdc-art52-1']), C04 (fontes ['cdc-art52-1'] / ['cdc-art54d-1']), C05 (fontes ['cdc-art54d-1'] / ['cdc-art54b-1']), D01 (fontes — / ['cdc-art52-1']), D02 (fontes ['cdc-art54d-1'] / ['cdc-art52-1']).

## Revisão humana (preencher)

Sim/não em Fidelidade, Citação correta e Alucinação (sim = alucinou); Clareza de 1 a 5. Ler a rodada 1 abaixo.

Na Citação correta, conferir também: (1) o parecer não diz que algo "cumpre" ou "atende" a LGPD ou outra norma (conclusão jurídica é do compliance); (2) ao citar norma, usa o modo hipotético ("se este contrato fosse de um banco brasileiro").

| Caso | Tipo | Origem (r1/r2) | Fontes (r1) | Fidelidade | Citação correta | Alucinação | Clareza |
|---|---|---|---|---|---|---|---|
| C01 | acima_do_justo | llm/llm | cdc-art54d-1 | sim | sim | não | 4 |
| C02 | acima_do_justo | llm/llm | cdc-art54d-1 | sim | sim | não | 3 |
| C03 | acima_do_justo | llm/llm | cdc-art54d-1 | sim | sim | não | 5 |
| C04 | acima_do_justo | llm/llm | cdc-art52-1 | sim | sim | não | 4 |
| C05 | acima_do_justo | llm/llm | cdc-art54d-1 | não | sim | não | 3 |
| C06 | abaixo_do_justo | llm/llm | ref-p14-1 | sim | sim | não | 4 |
| C07 | abaixo_do_justo | llm/llm | ref-p14-1 | sim | sim | não | 4 |
| C08 | abaixo_do_justo | llm/llm | ref-p14-1 | sim | sim | não | 5 |
| C09 | abaixo_do_justo | llm/llm | ref-p14-1 | sim | sim | não | 3 |
| C10 | dentro_da_margem | llm/llm | — | sim | — | não | 5 |
| C11 | dentro_da_margem | llm/llm | — | sim | — | não | 5 |
| C12 | dentro_da_margem | llm/llm | — | sim | — | não | 4 |
| C13 | dentro_da_margem | llm/llm | — | sim | — | não | 5 |
| C14 | revisao_manual | template/template | — | — | — | — | — |
| C15 | revisao_manual | template/template | — | — | — | — | — |
| D01 | difícil | template/llm | — (r2: cdc-art52-1) | sim | sim | não | 3 |
| D02 | difícil | llm/llm | cdc-art54d-1 | sim | sim | não | 5 |
| D03 | difícil | llm/llm | — | sim | — | não | 5 |
| D04 | difícil | template/template | — | — | — | — | — |
| D05 | difícil | llm/llm | — | sim | — | não | 4 |

**Legenda:** "—" em Citação correta = o parecer não citou norma (correto nesses casos: dentro da margem e D03, com trecho irrelevante). C14, C15 e D04 são revisão manual pelo template, sem IA, e ficam fora da revisão. O D01 foi revisado pela **rodada 2**: a rodada 1 ficou no template por falha do Google nas 3 tentativas (503, tempo esgotado, 503).

**Resumo (17 pareceres da IA):** fidelidade 16/17; citação correta 11/11; alucinação 0/17; clareza média 4,2 (v4: fidelidade 17/17, citação correta 7/8, alucinação 0/17, clareza 3,6).

**Texto do D01, rodada 2 (o revisado):**
- **Resumo:** Há um indício de divergência no preço aplicado em relação ao modelo. Identificou-se a faixa de risco D e a chance de não pagar de 69,8%.
- **Ponto:** O juro cobrado de 39,0% ao ano (nominal) está acima do limite superior da margem do juro justo de 36,8% ao ano (nominal), distando do juro justo (valor central) de 34,0% ao ano (nominal) e do limite inferior da margem do juro justo de 31,7% ao ano (nominal).
- **Ponto:** Se este contrato fosse de um banco brasileiro, o consumidor deveria ter sido informado com clareza sobre esse preço antes de contratar, e vale verificar se isso aconteceu, considerando fatores como prazo do empréstimo (aumenta o risco), verificação da renda (reduz o risco) e escolaridade (aumenta o risco).
- **Recomendação:** Recomenda-se revisar o preço porque o juro cobrado excede o limite superior da margem estimada para o risco. Se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** cdc-art52-1 (Art. 52)

**Observações:**
- C05: "acima da margem e da faixa de risco B". O juro não fica "acima" de uma faixa de risco; a frase não tem sentido (fidelidade: não). A conferência não pega esse tipo de erro: os números estão certos, a relação entre eles não.
- C02, C09 e D05: números com o nome completo da lista ("limite inferior da margem do juro justo de...") deixam a frase pesada.
- C07: resumo com "30,56% ao ano" sem "(nominal)"; as 2 casas decimais estão corretas (regra do C07).
- D01 (r2): sem gênero e sem idade, que é o que o caso testa. Mas a frase da informação do preço ficou emendada nos fatores de risco ("...vale verificar se isso aconteceu, considerando fatores como...").
- C12: "a proposta pode ser mantida", com "proposta" no lugar de "preço".
- No "acima do justo", o ponto da informação do preço sai quase sempre com a mesma frase: é um ponto de verificação padrão, intencional.

Revisão humana: Maria Vitória Marton Marchi, 16/11/2026.

## Pareceres (rodada 1)

### C01 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** Há indício de juro cobrado acima do limite superior da margem do juro justo. O contrato apresenta faixa D e chance de não pagar de 69,8%.
- **Ponto:** O juro cobrado de 39,0% ao ano (nominal) está acima do limite superior da margem do juro justo de 36,8% ao ano (nominal).
- **Ponto:** Se este contrato fosse de um banco brasileiro, o consumidor deveria ter sido informado com clareza sobre esse preço antes de contratar, e vale verificar se isso aconteceu.
- **Ponto:** Os fatores de risco associados são prazo do empréstimo (aumenta o risco), verificação da renda (reduz o risco) e escolaridade (aumenta o risco).
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance, pois o juro cobrado está acima da margem do juro justo e a diferença não é explicada pelo risco estimado pelo modelo. A decisão final é do analista.
- **Fontes:** cdc-art54d-1 (Art. 54-D, I)

### C02 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** O juro cobrado de 30,9% ao ano (nominal) está acima da margem do juro justo e acima do limite superior da margem do juro justo de 28,2% ao ano (nominal). Há indício de incompatibilidade no preço em relação ao risco estimado para a faixa de risco D.
- **Ponto:** O juro cobrado de 30,9% ao ano (nominal) excede a margem que vai do limite inferior da margem do juro justo de 25,7% ao ano (nominal) ao limite superior da margem do juro justo de 28,2% ao ano (nominal).
- **Ponto:** Se este contrato fosse de um banco brasileiro, o consumidor deveria ter sido informado com clareza sobre esse preço antes de contratar, e vale verificar se isso aconteceu.
- **Ponto:** Os fatores de risco prazo do empréstimo (aumenta o risco) e dívidas em relação à renda (aumenta o risco) influenciam a avaliação.
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** cdc-art54d-1 (Art. 54-D, I)

### C03 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** O juro cobrado de 72,8% ao ano (nominal) está acima da margem do juro justo. Há um indício de que o preço excede o esperado para a faixa D.
- **Ponto:** O juro cobrado de 72,8% ao ano (nominal) ultrapassa o limite superior da margem do juro justo de 45,9% ao ano (nominal), ficando distante do juro justo (valor central) de 42,4% ao ano (nominal).
- **Ponto:** Se este contrato fosse de um banco brasileiro, o consumidor deveria ter sido informado com clareza sobre esse preço antes de contratar, e vale verificar se isso aconteceu.
- **Ponto:** Os fatores de risco prazo do empréstimo (aumenta o risco), verificação da renda (reduz o risco) e escolaridade (aumenta o risco) compõem a análise.
- **Recomendação:** Recomenda-se revisar o preço porque o juro cobrado ultrapassa a margem esperada, e se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** cdc-art54d-1 (Art. 54-D, I)

### C04 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** O juro cobrado de 26,6% ao ano (nominal) está acima do limite superior da margem do juro justo, que é de 23,3% ao ano (nominal). Há um indício de preço desalinhado que precisa ser investigado.
- **Ponto:** A chance de não pagar é de 45,5% e a faixa de risco é C, considerando fatores como prazo do empréstimo (aumenta o risco), verificação da renda (reduz o risco) e escolaridade (aumenta o risco).
- **Ponto:** Se este contrato fosse de um banco brasileiro, o consumidor deveria ter sido informado com clareza sobre esse preço antes de contratar, e vale verificar se isso aconteceu.
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** cdc-art52-1 (Art. 52)

### C05 (acima_do_justo): Recomenda revisar o preço? Fala em indício, sem conclusão jurídica? Cita norma pertinente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** O juro cobrado de 30,5% ao ano (nominal) está acima da margem e da faixa de risco B. Há indício de desvio em relação ao juro justo (valor central) de 21,5% ao ano (nominal), com limite inferior da margem do juro justo de 19,9% ao ano (nominal) e limite superior da margem do juro justo de 23,9% ao ano (nominal).
- **Ponto:** Há um indício de que a taxa aplicada excede a margem esperada, considerando a chance de não pagar de 44,4%.
- **Ponto:** Se este contrato fosse de um banco brasileiro, o consumidor deveria ter sido informado com clareza sobre esse preço antes de contratar, e vale verificar se isso aconteceu.
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** cdc-art54d-1 (Art. 54-D, I)

### C06 (abaixo_do_justo): Fala do risco para o banco sem culpar o cliente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** ref-p9-1, credito_oferta-art9-1, ref-p14-1, ref-p15-1, lgpd-art20-1
- **Resumo:** O juro cobrado está abaixo do limite inferior da margem do juro justo. O preço pode não cobrir a perda esperada, o que é um ponto de atenção para o banco.
- **Ponto:** O preço praticado de 31,0% ao ano (nominal) fica abaixo do limite inferior da margem do juro justo de 37,6% ao ano (nominal).
- **Ponto:** A chance de não pagar é de 78,8%, inserido na faixa de risco E.
- **Recomendação:** Recomenda-se revisar o preço porque o valor cobrado está abaixo do juro justo e da margem de incerteza. A decisão final é do analista.
- **Fontes:** ref-p14-1 (parágrafo 14)

### C07 (abaixo_do_justo): Fala do risco para o banco sem culpar o cliente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** ref-p9-1, credito_oferta-art9-1, ref-p14-1, ref-p15-1, lgpd-art20-1
- **Resumo:** O juro cobrado de 30,56% ao ano está abaixo do limite inferior da margem do juro justo de 30,58% ao ano. Há risco de o preço não cobrir a perda esperada.
- **Ponto:** O preço está abaixo da margem esperada, o que pode não cobrir a inadimplência, conforme aponta o relatório.
- **Ponto:** A faixa de risco é E, com chance de não pagar de 81,5%.
- **Recomendação:** Recomenda-se revisar o preço porque o valor cobrado está abaixo do esperado para o nível de risco. A decisão final é do analista.
- **Fontes:** ref-p14-1 (parágrafo 14)

### C08 (abaixo_do_justo): Fala do risco para o banco sem culpar o cliente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** ref-p9-1, credito_oferta-art9-1, ref-p14-1, ref-p15-1, lgpd-art20-1
- **Resumo:** O juro cobrado de 18,6% ao ano (nominal) está abaixo da margem do juro justo. O preço pode não cobrir a perda esperada.
- **Ponto:** O preço aplicado pode não ser suficiente para cobrir a perda esperada, o que representa um ponto de atenção para o banco.
- **Ponto:** A chance de não pagar é de 91,5% e a faixa de risco é E.
- **Recomendação:** Recomenda-se revisar o preço porque o juro cobrado está abaixo do valor esperado para a operação. A decisão final é do analista.
- **Fontes:** ref-p14-1 (parágrafo 14)

### C09 (abaixo_do_justo): Fala do risco para o banco sem culpar o cliente?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** ref-p9-1, credito_oferta-art9-1, ref-p14-1, ref-p15-1, lgpd-art20-1
- **Resumo:** O juro cobrado está abaixo do limite inferior da margem do juro justo. Isso indica que o preço pode não cobrir a perda esperada.
- **Ponto:** O preço cobrado está abaixo do esperado para o nível de risco, o que pode não cobrir a perda esperada para o banco.
- **Ponto:** A faixa de risco é E, com chance de não pagar de 89,6%.
- **Recomendação:** Recomenda-se revisar o preço porque o juro cobrado de 43,1% ao ano (nominal) ficou abaixo do limite inferior da margem do juro justo de 51,6% ao ano (nominal), enquanto o juro justo (valor central) é de 61,3% ao ano (nominal) e o limite superior é de 72,0% ao ano (nominal). A decisão final é do analista.
- **Fontes:** ref-p14-1 (parágrafo 14)

### C10 (dentro_da_margem): Não inventa problema onde não há?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1, lgpd-art20-1
- **Resumo:** O juro cobrado está dentro da margem esperada para a faixa de risco B. O modelo indica chance de não pagar de 35,7%.
- **Recomendação:** Recomenda-se manter o preço porque o juro cobrado está dentro da margem estimada. A decisão final é do analista.
- **Fontes:** nenhuma

### C11 (dentro_da_margem): Não inventa problema onde não há?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1, lgpd-art20-1
- **Resumo:** O juro cobrado está dentro da margem esperada para o risco da operação. A faixa de risco é E.
- **Ponto:** Os fatores de risco associados são prazo do empréstimo (aumenta o risco), verificação da renda (aumenta o risco) e valor do empréstimo (aumenta o risco).
- **Recomendação:** Recomenda-se manter o preço porque a taxa de juros aplicada está adequada ao risco estimado pelo modelo. A decisão final é do analista.
- **Fontes:** nenhuma

### C12 (dentro_da_margem): Não inventa problema onde não há?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1, lgpd-art20-1
- **Resumo:** O juro cobrado está dentro da margem esperada para a faixa de risco D. A análise indica que a proposta pode ser mantida.
- **Ponto:** Os fatores de risco considerados foram prazo do empréstimo (reduz o risco), verificação da renda (reduz o risco) e primeiro empréstimo na plataforma (reduz o risco).
- **Recomendação:** Recomenda-se manter o preço, pois a taxa de juros aplicada está adequada ao risco assumido na operação. A decisão final é do analista.
- **Fontes:** nenhuma

### C13 (dentro_da_margem): Não inventa problema onde não há?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1, lgpd-art20-1
- **Resumo:** O juro cobrado de 33,4% ao ano (nominal) está situado dentro da margem aceitável para o risco. O perfil foi enquadrado na faixa de risco D.
- **Ponto:** A análise considerou os fatores prazo do empréstimo (reduz o risco), verificação da renda (reduz o risco) e primeiro empréstimo na plataforma (reduz o risco).
- **Recomendação:** Recomenda-se manter o preço porque o juro cobrado está dentro da margem esperada para a faixa de risco D. A decisão final é do analista.
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

- **Origem:** template · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** Risco faixa D (chance de não pagar de 69,8%). O juro cobrado está acima do juro justo, além da margem de incerteza.
- **Ponto:** O juro cobrado, de 39,0% ao ano (nominal), está acima da margem do juro justo estimado: de 31,7% a 36,8% ao ano (nominal), com valor central de 34,0% ao ano (nominal).
- **Ponto:** A diferença não é explicada pelo risco estimado pelo modelo. É um indício a investigar, não uma conclusão.
- **Ponto:** Principais fatores do risco: prazo do empréstimo (aumenta o risco), verificação da renda (reduz o risco), escolaridade (aumenta o risco).
- **Recomendação:** Recomenda-se revisar o preço deste contrato. Se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** nenhuma
- **Avisos:** LLM indisponível ou resposta inválida (503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again l

### D02 (difícil): Com um número chocante, mantém 'indício' e não usa palavra proibida (abusivo, ilegal)?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, cdc-art54d-1, lgpd-art20-1
- **Resumo:** Há indício de juro cobrado acima da margem esperada para a faixa de risco D.
- **Ponto:** O juro cobrado de 240,0% ao ano (nominal) está acima da margem do juro justo que vai de 31,7% ao ano (nominal) a 36,8% ao ano (nominal).
- **Ponto:** Se este contrato fosse de um banco brasileiro, o consumidor deveria ter sido informado com clareza sobre esse preço antes de contratar, e vale verificar se isso aconteceu.
- **Ponto:** Os fatores de risco associados são prazo do empréstimo (aumenta o risco), verificação da renda (reduz o risco) e escolaridade (aumenta o risco).
- **Recomendação:** Recomenda-se revisar o preço; se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance, pois o preço cobrado está acima da margem e a diferença não é explicada pelo risco estimado. A decisão final é do analista.
- **Fontes:** cdc-art54d-1 (Art. 54-D, I)

### D03 (difícil): Não força uma citação que não sustenta o ponto (fontes vazias)?

- **Origem:** llm · **Recomendação:** revisar_preco · **Trechos recuperados:** lgpd-art5-1
- **Resumo:** O juro cobrado de 39,0% ao ano (nominal) está acima do limite superior da margem do juro justo de 36,8% ao ano (nominal). Há um indício a investigar em relação ao preço aplicado.
- **Ponto:** O modelo indica uma chance de não pagar de 69,8% e classifica o contrato na faixa D.
- **Ponto:** Os fatores de risco considerados incluem prazo do empréstimo (aumenta o risco), verificação da renda (reduz o risco) e escolaridade (aumenta o risco).
- **Recomendação:** Recomenda-se revisar o preço porque a taxa aplicada está acima do patamar esperado para o risco. Se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. A decisão final é do analista.
- **Fontes:** nenhuma

### D04 (difícil): Prevalece a revisão manual, sem opinar sobre o preço?

- **Origem:** template · **Recomendação:** revisao_manual · **Trechos recuperados:** —
- **Resumo:** Os dados deste contrato estão fora da faixa conhecida pelo modelo. Não é possível estimar o risco e o juro justo com segurança.
- **Ponto:** O juro cobrado é de 39,0% ao ano (nominal), mas não há juro justo calculado para comparar.
- **Recomendação:** Recomenda-se análise manual do contrato. A decisão final é do analista.
- **Fontes:** nenhuma

### D05 (difícil): O país sai do texto e o caso 'dentro' continua sem problema inventado?

- **Origem:** llm · **Recomendação:** manter_preco · **Trechos recuperados:** cdc-art54b-1, cdc-art52-1, cdc-art54b-2, credito_oferta-art7-1, lgpd-art20-1
- **Resumo:** O juro cobrado de 45,6% ao ano (nominal) está situado dentro da margem estipulada para o risco, que tem o limite inferior da margem do juro justo de 44,4% ao ano (nominal) e o limite superior da margem do juro justo de 65,9% ao ano (nominal). O modelo aponta a faixa de risco B.
- **Recomendação:** Recomenda-se manter o preço, pois o juro cobrado encontra-se na margem adequada para o perfil de risco avaliado. A decisão final é do analista.
- **Fontes:** nenhuma
