# Roteiro da demo — Auditor de Preço Justo

**Versão:** 1.1 · **Data:** 14/11/2026 · **Responsável:** Yasmin (App e infraestrutura) · **Revisor:** grupo · **Status:** rascunho para o ensaio

Demo ao vivo de cerca de **8 minutos**, com ensaio em 15/11 e banca em 21/11, seguida da mesma sequência gravada em vídeo (plano B). Cada bloco diz o que mostrar na tela, a frase-chave e o ponto do guia que ele prova.

---

## 1. Antes de começar (no dia, 30 min antes)

- [ ] Docker Desktop aberto; rodar  `.\iniciar.ps1`, ou `docker compose up -d` e esperar o "Pronto".
- [ ] Em http://localhost:8000/: `modelo_carregavel: true`, `banco_disponivel: true` e o `pacote_hash` igual ao combinado com o Samuel.
- [ ] Rodar `python -m scripts.conferir_analise` (20 contratos reais batem com o lote). Se falhar, não apresentar a Análise ao vivo sem entender o porquê.
- [ ] **Abrir um contrato da base de aquecimento** (Contratos da base → busca): a 1ª chamada ao Gemini e à busca nas normas é a mais lenta.
- [ ] **Terminal aberto na raiz do projeto**, com o ambiente ativado, e rodar uma vez `python -m genai.avaliacao.demo_conferencia`. Esperado: parecer original APROVADO e as 4 sabotagens RECUSADAS.
- [ ] Preencher "Analista responsável" no topo da seção de auditoria.
- [ ] Navegador em tela cheia, zoom em 90% a 100%, abas abertas: painel (8501) e documentação da API (8000/docs).
- [ ] Vídeo gravado aberto em outra janela, pronto para o plano B.
- [ ] Print do `terraform plan` ("Plan: 5 to add") num slide, para mostrar a infraestrutura na nuvem sem depender da internet da sala.

## 2. Sequência

| # | Tempo | Na tela | Frase-chave | Prova |
|---|---|---|---|---|
| 1 | 0:00 | Capa do painel | "Para cada contrato: qual o risco, se o juro é justo para esse risco e se clientes de mesmo risco pagam diferente. Quem decide é o analista." | Ideia e enquadramento |
| 2 | 0:45 |  **Contratos da base** → clicar na busca e digitar o começo de um ID (a lista filtra a cada caractere) → escolher: abre a **Análise do contrato** com o selo "Calculado agora pelo modelo" e a **Procedência** | "A carteira inteira já foi pontuada pelo modelo em lote; o analista abre o contrato e confere. Gênero e idade não entram no modelo nem no parecer." | Governança: atributos sensíveis só auditam |
| 3 | 1:45 |  Cartões, régua, **Precificação** (parâmetros e juro justo com PD zero) e motivos SHAP | "O juro justo vem do fluxo de caixa: custo do dinheiro da época, perda esperada e margem da safra, com margem de incerteza do bootstrap." | Modelo e juro justo |
| 4 | 2:45 | Parecer "Gerado por IA", fontes e referência de mercado do BC | "A IA só escreve. Recomendação e números vêm do código, e cada número do texto é conferido; se falhar, entra o template." | GenAI com checagem |
| 5 | 3:45 |  **Contratos da base** → chip "Acima do justo" → **Abrir 98ffaaa4-0b86** (faixa D: cobrado 39,0%, justo 34,0%, margem 31,7%–36,8%) → **Resultado observado** | "Indício a investigar, não conclusão." | Linguagem de indício |
| 6 | 4:30 |  **Contratos da base** → chip "Revisão manual" → **Abrir 1cb66730-5f46** | "Dados fora da faixa de treino: o sistema não arrisca um número e devolve ao analista." | Revisão manual |
| 7 | 5:00 | Decisão do analista: justificativa + **Revisar preço** com nova taxa | "A decisão é humana e fica gravada no banco, com o parecer e a justificativa." | LGPD art. 20 |
| 8 | 5:45 | **Home → Panorama da carteira**: cartões, faixas e equidade | "Gênero: −0,53 pp; idade 18–25 × 35–44: +5,31 pp. Os dois intervalos não cruzam o zero: indício a investigar, com as ressalvas de proxies e qualidade do dado." | Auditoria de equidade |
| 9 | 7:00 |  **Laboratório**: mudar prazo e renda e ver o modelo recalcular (original × recalculado); mudar o juro e ver que só o preço muda; "Usar como proposta" | "O analista testa um juro e vê na hora se entra na margem; o risco não muda, porque o modelo não usa o preço." | Uso operacional |
| 10 | 7:30 |  Página **Registro** → contadores → Exportar | "Trilha completa: quem decidiu, o quê, por quê e se discordou do sistema." | Rastreabilidade |

## 3. Fora da sequência: "Tente enganar a IA" no terminal (~1 min)

Sugestão: mostrar no trecho de **governança e ética** da apresentação (minutos 16 a 18), e não dentro da demo, para não disputar o tempo dela. Também serve como resposta ao vivo para "E se a IA inventar um número?".

| Na tela | Frase-chave | Prova |
|---|---|---|
| Terminal: `python -m genai.avaliacao.demo_conferencia` (parecer real do contrato 98ffaaa4, o mesmo do bloco 5, com 4 sabotagens). Depois, a banca dita uma frase: `python -m genai.avaliacao.demo_conferencia "frase da banca"` | "Este é o parecer real do Gemini para o contrato que vocês viram na demo, aprovado. Agora trocamos um número, colocamos 'cobrança abusiva', citamos um artigo que a busca não trouxe e falamos da idade do cliente. As quatro versões são recusadas pela mesma conferência que roda em todo parecer. E uma frase neutra passa: a conferência recusa só o que viola uma regra." | Proteção contra alucinação, ao vivo |

## 4. Plano B

| Problema na hora | O que fazer |
|---|---|
| Sem internet (Gemini fora) | Seguir: o parecer sai pelo **template de reserva** e o painel mostra isso. Usar como prova do fallback. |
| Modelo ou banco não responde | A API devolve sozinha os **valores do lote** (selo laranja, com o motivo em "Por que o lote"), sem motivos. Seguir a demo e citar o plano B. Se a **API** cair, a Home e a lista também param (o lote agora vem pela API): usar o vídeo. |
| Banco fora | A decisão **não é registrada**: a tela diz isso e guarda só um rascunho. Não registrar a decisão na demo; explicar que o sistema nunca finge ter gravado. Quando o banco voltar: Registro → "Tentar gravar de novo". |
| Rota, banco ou Gemini fora na hora de mostrar a conferência | O script `python -m genai.avaliacao.demo_conferencia` funciona mesmo assim: não depende de nenhum dos três. |
| Docker não sobe | Passar o **vídeo gravado**. |

## 5. Perguntas prováveis da banca

- **"Por que dados da Estônia?"** Não há base pública brasileira de contratos individuais; o Bondora é substituto do comportamento de crédito, e a análise jurídica é hipotética.
- **"O juro justo é absoluto?"** Não: é relativo à safra (a margem iguala a mediana do justo à do cobrado em cada ano). Mede quem está caro ou barato **perto dos pares da mesma época**.
- **"O backtest confirma a auditoria?"** (responde o Samuel; o Marcos completa os números) Não confirma, e mostramos isso. Em 2016, os contratos "acima do justo" tiveram o pior retorno (−22,7%) e os "abaixo", o melhor (−9,2%). A hipótese só vale nas faixas B e C. Como o modelo subestima o default de 2016, parte do juro alto cobrado reflete um risco que ele não captura. Por isso o sistema trata "acima do justo" como indício para o analista revisar, nunca como conclusão, e a decisão final é humana. O próximo passo seria calibrar o modelo por safra. (2016, 7.141 contratos encerrados, sem reestruturados; `src/dados/roi_backtest.py`)
- **"E se a IA inventar um número?"** A conferência por código compara cada número do texto com os que vieram do modelo e recusa o parecer se algum não bater; aí entra o template. Na avaliação (20 casos × 2 rodadas), a revisão humana encontrou zero alucinações e fidelidade em 17 de 17 pareceres. O parecer é fiel ao modelo, não à realidade: a conferência garante que o texto não inventa nem distorce o que o modelo calculou. Dá para ver ao vivo com o script da seção 3.
- **"O país entra no modelo? Por que não aparece nos motivos?"** Entra, como mercado da operação (Estônia, Finlândia ou Espanha: regras de cobrança e recuperação diferentes; a perda se não pagar muda por país), não como característica do cliente. Não é usado como justificativa no parecer, e a equidade é medida controlando por ele. A tela diz isso embaixo dos motivos.
- **"Por que país não está na equidade?"** País é controle de risco (o default varia muito entre EE, ES e FI), não grupo auditado.

## Pendências

- [ ] Ensaio cronometrado com o grupo
- [ ] Gravar o vídeo (resolução 1080p, com áudio)
- [x] Combinar com o Samuel a resposta sobre o backtest (14/11)
- [ ] Decidir o que cortar: a sequência soma cerca de 8 minutos e o guia da banca reserva 6 para a demo ao vivo
- [ ] Definir quem fala em cada bloco

## Histórico

| Versão | Data | Mudança |
|---|---|---|
| 1.0 | 11/11/2026 | Primeira versão do roteiro. |
| 1.1 | 14/11/2026 | Maria: "Tente enganar a IA" no terminal (seção 3), linha no plano B, resposta nova para "E se a IA inventar um número?", resposta do backtest combinada com o Samuel, frase do bloco 9 e data da banca. |
