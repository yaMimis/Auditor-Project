# REGRAS_PARECER.md — Regras para o parecer gerado pela IA

**Projeto:** Auditor de Preço Justo · **Frente:** IA Generativa (Maria) · **Versão:** 1.5 · **Data:** 09/11/2026
**Status:** v1.2 aprovada pela Maria em 03/11/2026; v1.3 acrescenta a regra sobre os números do REF (seção 5); v1.4 traz a unidade nominal, a referência de mercado do BC, os nomes de países e as correções do primeiro teste real do LLM, aguardando o grupo.

## 1. Finalidade

Estas regras dizem como o parecer deve ser escrito e o que ele nunca pode fazer. Elas são usadas em dois lugares:

- **No prompt** (`genai/prompts/parecer_v3.md`; a v1 e a v2 continuam no repositório), como instruções ao LLM.
- **Na checagem por código** (`genai/src/checagem.py`), que rejeita o parecer que as descumprir.

O formato dos dados (campos, tipos, exemplos) está só em `FORMATO_JSON.md`. Este documento não o repete.

---

## 2. Quem decide o quê

| Quem                      | Responsabilidade                                                                                                                                                 |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `prever()` (Samuel)     | Calcula os números: risco, faixa, juro justo, margem de incerteza, situação do preço e motivos com rótulo legível. Marca os casos de revisão manual.      |
| Código da cadeia (Maria) | Escolhe a recomendação pela tabela da seção 7, decide se chama o LLM ou o template, formata os números para o texto, busca as normas e confere o resultado. |
| LLM                       | Só escreve: resumo, pontos de atenção, texto da recomendação e escolha das fontes entre os trechos recebidos.                                               |
| Analista                  | Toma a decisão final. Pode manter, revisar ou encaminhar ao compliance. Só o analista encaminha ao compliance.                                                 |

O LLM nunca calcula números, nunca escolhe a recomendação e nunca decide no lugar do analista.

---

## 3. Linguagem

- Português do Brasil, frases curtas, vocabulário simples. Evitar jargão jurídico.
- O resumo tem no máximo 2 frases. No máximo 3 pontos de atenção.
- **Modo hipotético:** os contratos são do Bondora (Europa) e a análise jurídica é uma simulação. Sempre que o parecer relacionar o contrato a uma norma brasileira, usar a forma "se este contrato fosse de um banco brasileiro", com o verbo no condicional ("estaria", "deveria"). Sem norma citada, essa forma não é usada.
- **Usar:** "indício", "ponto de atenção", "recomenda-se revisar", "recomenda-se encaminhar ao compliance".
- Não começar frases com "Ponto de atenção:"; a frase é escrita diretamente.
- **Nunca usar:** "ilegal", "ilegalidade", "ilícito", "crime", "fraude", "violação", "viola", "abusivo", "abusiva", "discriminação", "irregular". Essas palavras afirmam uma conclusão jurídica que só o compliance pode tirar.
- Os fatores de risco são citados pelo `rotulo` que vem do `prever()` (ex.: "dívidas em relação à renda"), nunca pelo nome técnico da variável. O nome é copiado exatamente, sem acrescentar ou trocar palavras. Um fator de risco, sozinho, não é ponto de atenção: ele só explica o risco estimado.
- O texto da recomendação sempre termina lembrando que a decisão final é do analista.

---

## 4. Ética e privacidade

- **Nada que identifique o cliente vai para o LLM:** nem `UserName`, nem `contrato_id`. O código insere o `contrato_id` no parecer depois da resposta.
- **Gênero, idade e país nunca aparecem no parecer de um contrato.** Esses dados servem só para a auditoria de equidade da carteira, de forma agregada. Isso segue o princípio da não discriminação da LGPD (art. 6º, IX). O país já não vem na lista de motivos do `prever()`. O nome dos países do Bondora (Estônia, Finlândia, Espanha, Eslováquia) também conta como país.
- Se algum motivo vier ligado a esses atributos, o parecer não o menciona. Se só o rótulo trouxer o país entre parênteses (ex.: "score de crédito (Estônia)"), o código retira o país e mantém o fator.
- O parecer nunca culpa o cliente. Quando o juro está abaixo do justo, o ponto de atenção é o risco para o banco.
- O parecer apoia a decisão humana, nunca a substitui (direito de revisão de decisões automatizadas, LGPD art. 20).

---

## 5. Números

- Todo número do parecer vem do `prever()`. O LLM **não recalcula, não estima e não arredonda**.
- O código entrega os números já formatados (ex.: "24,9% ao ano (nominal)", "18,4%") e o LLM os copia exatamente como recebeu. Os juros são **nominais** (taxa ao mês = anual ÷ 12), a convenção do Bondora e do `prever()` (DATA.md, seção 8).
- Os únicos números que podem aparecer no texto são: chance de não pagar (`pd`), juro cobrado, juro justo e os limites da margem de incerteza. A faixa (A a E) também pode aparecer.
- Os campos extras do `prever()` (`pd_ic95`, `diferenca_pp`, `valor` e `peso` dos motivos) não aparecem no parecer.
- Todo número citado no texto entra em `numeros_citados`, com o valor exato da entrada. Um campo que veio `null` nunca é citado.
- O parecer não fala de CET, tarifas ou encargos: esses dados não existem na base.
- **Média do BC (série 20742):** aparece só no campo `contexto_mercado`, numa frase fixa **escrita pelo código**, convertida para nominal [12 × ((1 + efetiva)^(1/12) − 1)] e com a efetiva entre parênteses. O LLM não recebe esse número e não pode citar "média do mercado"; se citar um número que não veio do `prever()`, a checagem recusa o parecer. Antes de 03/2011 não há dado, e a frase não aparece. É contexto do mercado brasileiro, nunca medida do preço justo.
- Os números dos trechos do Relatório de Estabilidade Financeira (REF) descrevem o mercado de crédito brasileiro, não o contrato, e nunca aparecem no parecer. Esses trechos servem só para explicar do que é feito o custo do crédito (custo de captação, inadimplência, despesas administrativas, tributos e margem).

---

## 6. Normas (RAG)

- O parecer só cita uma norma se ela estiver entre os trechos recuperados no pgvector e entregues no prompt.
- Cada norma citada no texto aparece em `fontes`, com `norma`, `artigo` e `trecho_id` iguais aos do trecho recebido.
- O LLM nunca cita normas que conhece de memória, mesmo que pareçam corretas.
- Se nenhum trecho recuperado for pertinente, `fontes` fica vazia e o texto não cita nenhuma norma. A tela mostra "Não encontrei base normativa para este caso."
- A citação precisa dizer o que o trecho diz. Se o trecho não sustenta o ponto, não cite.

---

## 7. Recomendação

A recomendação é escolhida **pelo código**, a partir da saída do `prever()`, nesta ordem:

| Ordem | Condição                                                                           | Recomendação            | Quem escreve                     | O que o texto deve dizer                                                                                                                    |
| ----- | ------------------------------------------------------------------------------------ | ------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | `situacao_preco` é `revisao_manual` **ou** `alerta_dados` é verdadeiro | `revisao_manual`        | template (o LLM não é chamado) | Os dados estão fora da faixa conhecida pelo modelo; o analista deve analisar o caso manualmente. Não opinar sobre o preço.               |
| 2     | `situacao_preco` é `acima_do_justo`                                             | `revisar_preco`         | LLM                              | O juro cobrado passa da margem do juro justo e a diferença não é explicada pelo risco estimado pelo modelo. Indício a investigar: se a política de preço não justificar a diferença, recomenda-se encaminhar ao compliance. |
| 3     | `situacao_preco` é `abaixo_do_justo`                                            | `revisar_preco`         | LLM                              | O preço pode não cobrir a perda esperada. Ponto de atenção para o banco, sem culpar o cliente.                                          |
| 4     | `situacao_preco` é `dentro_da_margem`                                           | `manter_preco`          | LLM                              | O juro está dentro da margem esperada para o risco. Não inventar problema: os pontos de atenção podem ficar vazios.                                                                |

Por que a linha 2 recomenda revisar o preço, e não encaminhar direto ao compliance:

- o juro justo vem do nosso modelo, que não enxerga tudo o que o credor enxergava (dados internos, bureaus completos). Uma diferença acima da margem é um **indício**, não uma prova de que o risco não a explica;
- se todo contrato acima da margem fosse ao compliance, ele receberia uma parte grande da carteira e o alerta perderia valor;
- por isso o primeiro passo é revisar o preço. O encaminhamento ao compliance continua possível, mas é decisão do analista, quando a política de preço não justificar a diferença.

`encaminhar_compliance` segue válida no formato do parecer (`FORMATO_JSON.md`), mas não é escolhida automaticamente pelo código.

Na linha 1, o LLM não é chamado porque não há risco nem juro justo para comentar: qualquer texto livre seria opinião sem dado.

---

## 8. Template de reserva

O parecer é montado pelo `genai/src/template.py`, sem IA, quando:

- o caso é de revisão manual (seção 7, linha 1);
- a API do LLM falha;
- a resposta demora mais de 20 segundos;
- o JSON vem inválido;
- a checagem (seção 9) rejeita o parecer.

O template usa a faixa, a situação do preço, os números formatados e os rótulos dos motivos. Exemplo: "Risco faixa C. O juro cobrado está acima do juro justo além da margem de incerteza. Principais fatores: dívidas em relação à renda (aumenta o risco)."
Em revisão manual, o template cita só o juro cobrado, que é o único número disponível.
O parecer do template tem `origem: "template"`, `versao_prompt: "template_v1"`, `fontes` vazia e a mesma recomendação da tabela da seção 7.

---

## 9. O que a checagem confere

| Regra                | Como `checagem.py` confere                                                                                                                        |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Entrada              | A saída do `prever()` passa na validação pydantic (`EntradaPrever`), inclusive a regra de que só a revisão manual pode ter números nulos. |
| Formato              | O JSON do LLM passa na validação pydantic (`RespostaLLM`).                                                                                      |
| Números             | Cada valor de `numeros_citados` é igual ao da entrada, e cada número do texto corresponde a um valor formatado recebido.                        |
| Fontes               | Cada `trecho_id` de `fontes` está entre os trechos recuperados.                                                                                |
| Vocabulário         | O texto não contém nenhuma palavra proibida da seção 3.                                                                                         |
| Atributos sensíveis | O texto não menciona gênero, idade ou país, inclusive pelo nome dos países do Bondora.                                                                                                      |
| Tamanho              | Resumo com até 2 frases; no máximo 3 pontos de atenção.                                                                                         |

Se a entrada for inválida, o erro é registrado e o contrato vai para revisão manual. Se qualquer outro item falhar, entra o template de reserva.

---

## 10. Como estas regras são avaliadas

Nos 20 casos de avaliação (critérios em `genai/avaliacao/CRITERIOS.md`), além de recuperação, fidelidade, consistência numérica, citação, alucinação e clareza, o critério "Regras" confere se cada parecer seguiu este documento. Os 2 casos de revisão manual conferem se o sistema usou o template sem chamar o LLM.

## 11. Histórico

| Versão | Data       | Mudança                                                                                                                                                                                                                                              |
| ------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.0     | 29/10/2026 | Primeira versão.                                                                                                                                                                                                                                     |
| 1.1     | 30/10/2026 | Revisão manual pelo template, sem LLM, quando `situacao_preco` é `revisao_manual` ou `alerta_dados` é verdadeiro. Motivos citados pelo `rotulo`. Campos extras do `prever()` fora do parecer. Checagem da entrada com `EntradaPrever`. |
| 1.2     | 31/10/2026 | Seção 7: acima do justo passa de `encaminhar_compliance` para `revisar_preco`, com encaminhamento ao compliance como decisão do analista; texto "não é explicada pelo risco estimado pelo modelo". (Proposta do Samuel em 31/10; aprovada pela Maria em 03/11.)
| 1.3     | 03/11/2026 | Seção 5: números dos trechos do REF nunca aparecem no parecer; esses trechos só explicam a composição do custo do crédito. |
| 1.4     | 08/11/2026 | Juros nominais ("ao ano (nominal)"). Seção 5: média do BC só no `contexto_mercado`, escrita pelo código e convertida para nominal. Seção 4: nomes dos países do Bondora contam como país; país entre parênteses sai do rótulo. Seção 3 e 7 (após o primeiro teste real do LLM): frase hipotética só com norma citada e no condicional; sem "Ponto de atenção:"; nome dos fatores copiado exatamente; no caso "dentro", os pontos podem ficar vazios. Prompt passa para `parecer_v2`. |
| 1.5     | 09/11/2026 | Após a avaliação dos 20 casos (v2): citar a norma sempre que um trecho sustentar um ponto; a busca traz também a LGPD art. 20 (revisão de decisões automatizadas), que pode ser citada em qualquer situação; o REF pode ser citado no caso "abaixo" para explicar que a inadimplência compõe o custo do crédito (sem números); valor central ≠ margem; a recomendação não se repete nos pontos. Prompt passa para `parecer_v3`. |

Qualquer mudança nestas regras gera nova versão do prompt (`parecer_v2`, `parecer_v3`...) com o motivo anotado.