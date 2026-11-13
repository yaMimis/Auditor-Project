# Roteiro da demo — Auditor de Preço Justo

**Versão:** 1.0 · **Data:** 10/11/2026 · **Responsável:** Yasmin (App e infraestrutura) · **Revisor:** grupo · **Status:** rascunho para o ensaio

Demo ao vivo de cerca de **8 minutos**, no dia 15/11, seguida da mesma sequência gravada em vídeo (plano B). Cada bloco diz o que mostrar na tela, a frase-chave e o ponto do guia que ele prova.

---

## 1. Antes de começar (no dia, 30 min antes)

- [ ] Docker Desktop aberto; rodar  `.\iniciar.ps1`, ou `docker compose up -d` e esperar o "Pronto".
- [ ] Em http://localhost:8000/: `modelo_carregavel: true`, `banco_disponivel: true` e o `pacote_hash` igual ao combinado com o Samuel.
- [ ] Rodar `python -m scripts.conferir_analise` (20 contratos reais batem com o lote). Se falhar, não apresentar a Análise ao vivo sem entender o porquê.
- [ ] **Abrir um contrato da base de aquecimento** (Contratos da base → busca): a 1ª chamada ao Gemini e à busca nas normas é a mais lenta.
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
| 8 | 5:45 | **Home → Panorama da carteira**: cartões, faixas e equidade | "Gênero: −0,53 pp; idade 18–25 × 35–44: +5,45 pp. Os dois intervalos não cruzam o zero: indício a investigar, com as ressalvas de proxies e qualidade do dado." | Auditoria de equidade |
| 9 | 7:00 |  **Laboratório**: mudar prazo e renda e ver o modelo recalcular (original × recalculado); mudar o juro e ver que só o preço muda; "Usar como proposta" | "A carteira vira uma fila priorizada pela distância da margem. O analista testa um juro e vê na hora se entra na margem; o risco não muda, porque o modelo não usa o preço." | Uso operacional |
| 10 | 7:30 |  Página **Registro** → contadores → Exportar | "Trilha completa: quem decidiu, o quê, por quê e se discordou do sistema." | Rastreabilidade |

## 3. Plano B

| Problema na hora | O que fazer |
|---|---|
| Sem internet (Gemini fora) | Seguir: o parecer sai pelo **template de reserva** e o painel mostra isso. Usar como prova do fallback. |
| Modelo ou banco não responde | A API devolve sozinha os **valores do lote** (selo laranja, com o motivo em "Por que o lote"), sem motivos. Seguir a demo e citar o plano B. Se a **API** cair, a Home e a lista também param (o lote agora vem pela API): usar o vídeo. |
| Banco fora | A decisão **não é registrada**: a tela diz isso e guarda só um rascunho. Não registrar a decisão na demo; explicar que o sistema nunca finge ter gravado. Quando o banco voltar: Registro → "Tentar gravar de novo". |
| Docker não sobe | Passar o **vídeo gravado**. |

## 4. Perguntas prováveis da banca

- **"Por que dados da Estônia?"** Não há base pública brasileira de contratos individuais; o Bondora é substituto do comportamento de crédito, e a análise jurídica é hipotética.
- **"O juro justo é absoluto?"** Não: é relativo à safra (a margem iguala a mediana do justo à do cobrado em cada ano). Mede quem está caro ou barato **perto dos pares da mesma época**.
- **"O backtest confirma a auditoria?"** Resposta combinada com o Samuel (pendência abaixo).
- **"E se a IA inventar um número?"** A conferência por código recusa e entra o template. Na avaliação, 40/40 recomendações certas.
- **"O país entra no modelo? Por que não aparece nos motivos?"** Entra, como mercado da operação (Estônia, Finlândia ou Espanha: regras de cobrança e recuperação diferentes; a perda se não pagar muda por país), não como característica do cliente. Não é usado como justificativa no parecer, e a equidade é medida controlando por ele. A tela diz isso embaixo dos motivos.
- **"Por que país não está na equidade?"** País é controle de risco (o default varia muito entre EE, ES e FI), não grupo auditado.

## Pendências

- [ ] Ensaio cronometrado com o grupo
- [ ] Gravar o vídeo (resolução 1080p, com áudio)
- [ ] Combinar com o Samuel a resposta sobre o backtest
- [ ] Definir quem fala em cada bloco

## Histórico

| Versão | Data | Mudança |
|---|---|---|
| 1.0 | 11/11/2026 | Primeira versão do roteiro. |
