# Roteiro da demo — Auditor de Preço Justo

**Versão:** 1.0 · **Data:** 10/11/2026 · **Responsável:** Yasmin (App e infraestrutura) · **Revisor:** grupo · **Status:** rascunho para o ensaio

Demo ao vivo de cerca de **8 minutos**, no dia 15/11, seguida da mesma sequência gravada em vídeo (plano B). Cada bloco diz o que mostrar na tela, a frase-chave e o ponto do guia que ele prova.

---

## 1. Antes de começar (no dia, 30 min antes)

- [ ] Docker Desktop aberto; rodar  `.\iniciar.ps1`, ou `docker compose up -d` e esperar o "Pronto".
- [ ] Em http://localhost:8000/: `modelo_carregavel: true` e `banco_disponivel: true`.
- [ ] Fazer **uma auditoria de aquecimento** pelo formulário: a 1ª chamada ao Gemini e à busca nas normas é a mais lenta.
- [ ] Preencher "Analista responsável" no topo da seção de auditoria.
- [ ] Navegador em tela cheia, zoom em 90% a 100%, abas abertas: painel (8501) e documentação da API (8000/docs).
- [ ] Vídeo gravado aberto em outra janela, pronto para o plano B.
- [ ] Print do `terraform plan` ("Plan: 5 to add") num slide, para mostrar a infraestrutura na nuvem sem depender da internet da sala.

## 2. Sequência

| # | Tempo | Na tela | Frase-chave | Prova |
|---|---|---|---|---|
| 1 | 0:00 | Capa do painel | "Para cada contrato: qual o risco, se o juro é justo para esse risco e se clientes de mesmo risco pagam diferente. Quem decide é o analista." | Ideia e enquadramento |
| 2 | 0:45 | Aba **Revisão de contrato** → formulário (3 etapas, cada uma só abre depois de "Confirmo que revisei") → **Executar auditoria** (libera com as 3 caixas) | "Ninguém audita sem conferir os dados. E gênero e idade ficam registrados só para auditoria: não entram no modelo nem no parecer." | Governança: atributos sensíveis só auditam |
| 3 | 1:45 | Cartões, régua e motivos do resultado | "O juro justo vem do fluxo de caixa: custo do dinheiro da época, perda esperada e margem da safra, com margem de incerteza do bootstrap." | Modelo e juro justo |
| 4 | 2:45 | Parecer "Gerado por IA", fontes e referência de mercado do BC | "A IA só escreve. Recomendação e números vêm do código, e cada número do texto é conferido; se falhar, entra o template." | GenAI com checagem |
| 5 | 3:45 | **Caso de exemplo → Acima do justo · 98ffaaa4-0b86** (faixa D: cobrado 39,0%, justo 34,0%, margem 31,7%–36,8%) | "Indício a investigar, não conclusão." | Linguagem de indício |
| 6 | 4:30 | **Caso de exemplo → Revisão manual · 1cb66730-5f46** | "Dados fora da faixa de treino: o sistema não arrisca um número e devolve ao analista." | Revisão manual |
| 7 | 5:00 | Decisão do analista: justificativa + **Revisar preço** com nova taxa | "A decisão é humana e fica gravada no banco, com o parecer e a justificativa." | LGPD art. 20 |
| 8 | 5:45 | Aba **Auditoria da carteira**: cartões, faixas e equidade | "Gênero: −0,53 pp; idade 18–25 × 35–44: +5,45 pp. Os dois intervalos não cruzam o zero: indício a investigar, com as ressalvas de proxies e qualidade do dado." | Auditoria de equidade |
| 9 | 7:00 | Fila de revisão com a coluna **Decisão atual**; **Revisar** abre o contrato | "A carteira inteira vira uma fila priorizada pela distância da margem." | Uso operacional |
| 10 | 7:30 | Aba **Registro de decisões** → Exportar | "Trilha completa: quem decidiu, o quê, por quê e se discordou do sistema." | Rastreabilidade |

## 3. Plano B

| Problema na hora | O que fazer |
|---|---|
| Sem internet (Gemini fora) | Seguir: o parecer sai pelo **template de reserva** e o painel mostra isso. Usar como prova do fallback. |
| Modelo não carrega | Usar só **Caso de exemplo** (casos reais já calculados). |
| Banco fora | As decisões ficam na sessão com aviso; mostrar a exportação. |
| Docker não sobe | Passar o **vídeo gravado**. |

## 4. Perguntas prováveis da banca

- **"Por que dados da Estônia?"** Não há base pública brasileira de contratos individuais; o Bondora é substituto do comportamento de crédito, e a análise jurídica é hipotética.
- **"O juro justo é absoluto?"** Não: é relativo à safra (a margem iguala a mediana do justo à do cobrado em cada ano). Mede quem está caro ou barato **perto dos pares da mesma época**.
- **"O backtest confirma a auditoria?"** Resposta combinada com o Samuel (pendência abaixo).
- **"E se a IA inventar um número?"** A conferência por código recusa e entra o template. Na avaliação, 40/40 recomendações certas.
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
