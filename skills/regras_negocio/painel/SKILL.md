---
name: auditor-painel
description: Use para construir ou alterar o painel Streamlit do Auditor de Preço Justo — telas de revisão de contrato, auditoria da carteira e registro de decisões, formulário em etapas, blocos visuais, paleta e tipografia, chamada à API e regras do que pode ou não aparecer na tela.
---

# Painel do analista (Streamlit)

> Leia antes: `regras_negocio/governanca`, `regras_negocio/contratos_dados`, `regras_negocio/api`. Dono: Yasmin. Código: `src/app/main.py` (telas), `src/app/estilo.css` (todo o CSS; o `main.py` só injeta), `src/app/componentes.py` (formatação e HTML, sem Streamlit), `src/app/carteira.py` (leitura e resumo do lote); testes `tests/app/`.

## Objetivo

Dar ao analista, em uma tela, **o risco, o preço, o porquê e o parecer** de cada contrato, uma visão da carteira e um registro das decisões, sem que o painel calcule ou decida nada.

## Regras

1. O painel **só exibe**: todo número vem da API ou dos arquivos do lote. Nenhum cálculo de juro, PD ou equidade na tela.
2. Chama `POST {API_URL}/prever` e `POST {API_URL}/parecer`, `API_URL` padrão `http://localhost:8000`, **timeout 30 s** (cobre a busca, o LLM com 20 s e a queda para o template). Erros de conexão, timeout, 422 e 503 viram mensagens amigáveis.
3. Formatação pelo `componentes.py`: fração → "24,9%", nulo → "—", € com ponto de milhar, todo texto da API passa por `html.escape`. HTML compactado antes do `st.markdown` (linha indentada vira bloco de código no Markdown).
4. **Nunca** mostrar no resultado de um contrato: gênero, idade, rating ou PD do Bondora. País aparece só no cabeçalho do contrato, nunca como motivo.
5. A decisão é sempre do analista: três botões, **justificativa obrigatória**, nome do analista obrigatório, nova taxa opcional (só em "Revisar preço").
6. Estado em `st.session_state`; sidebar recolhida; widgets com chave própria para persistir entre etapas.

## Estrutura da página

- **Navbar fixa** (marca, links Home / Auditoria / Sobre, nome do analista) · **Hero** ("O preço acompanha o risco?") · **Faixa de 3 blocos** (juro justo por fluxo de caixa, modelo explicável, parecer com checagem).
- **Seção Auditoria:** indicador da API (no ar / sem modelo / fora do ar), campo "Analista responsável" e três abas:

### Aba 1 — Revisão de contrato

- Origem: **Novo contrato (formulário)** ou **Caso de exemplo**: os 8 casos reais de `docs/casos_de_teste.json` (reserva: `docs/exemplos_prever.json`), abertos com parecer via `/parecer`.
- **Formulário em 3 etapas travadas**, com "Confirmo que revisei" por etapa, barra de progresso REVISADO/PENDENTE e resumo do pedido:
  - uma etapa só abre com todas as anteriores revisadas (🔒 e botão desabilitado); voltar é sempre permitido; "Avançar para …" só com a caixa marcada;
  - mudar um campo depois de revisado **desmarca** a revisão daquela etapa; desmarcar uma etapa anterior leva de volta à primeira pendente;
  - 01 Dados pessoais: idade, gênero (0 Masculino · 1 Feminino · 2 Não informado; só auditoria), país (EE/FI/ES), renda mensal (€)
  - 02 Empréstimo: ID, valor (€), juro cobrado (% a.a.), prazo (3–60 meses), data de concessão (01/01/2009 até hoje; padrão hoje)
  - 03 Dívidas & histórico: total de dívidas (€); os demais campos seguem "sem informação"
  - Botão "⚖️ EXECUTAR AUDITORIA DE PREÇO" **desabilitado até as 3 caixas**, com o aviso "Falta revisar: …"; o código também confere antes de chamar a API.
- **Resultado:**
  - cabeçalho: contrato, país, data, valor, prazo, etiqueta da situação, chips ("Custo do dinheiro: Euribor da época", "Parecer: análise hipotética pela lei brasileira", versão do modelo, "Caso real da base", "Exemplo ilustrativo" ou "Aberto da carteira");
  - 4 cartões: risco de inadimplência (PD, IC 95% quando houver, faixa) · juro cobrado · juro justo com margem · situação do preço (cor da situação, pp além da margem);
  - **régua** "Juro cobrado × juro justo": faixa da margem, marca do justo acima, marca do cobrado abaixo, escala que cresce com juros > 100%; some em revisão manual (aparece um aviso no lugar);
  - **motivos** (SHAP): barras com o peso relativo, cor pelo efeito, rótulo + valor legível (`valor_legivel`: códigos viram texto, proporções da renda viram "6,1× a renda mensal", parcela vira "12% da renda", euros com ponto de milhar);
  - **parecer**: resumo, pontos de atenção, recomendação do sistema, fontes em chips (ou "Não encontrei base normativa para este caso."), origem ("Gerado por IA · revise antes de decidir" ou "Template de reserva · sem IA"), versão do texto;
  - **decisão do analista**; expander "Dados técnicos da consulta" (JSON enviado e recebido).

### Aba 2 — Auditoria da carteira

- Lê `docs/resultados/carteira_auditoria.csv` e `equidade.json` (`contratos_dados`, seção 5); reestruturados fora; país nunca como grupo.
- Filtros: período, país, faixa. Cartões: contratos auditados (+ revisão manual), % acima, % abaixo, pago a mais (€, soma de `excesso_eur`), perda não coberta (€, soma de `perda_nao_coberta_eur` dos abaixo do justo; só encerrados).
- Barras empilhadas da situação por faixa; tabela de equidade (diferença, IC 95%, leitura "Sem indício" / "Indício · investigar" e ressalvas); backtest por faixa × situação quando houver `rentabilidade_realizada`.
- Fila de revisão ordenada pela distância da margem, 50 na tela, exportação CSV completa, "Revisar" abre o contrato na aba 1 com parecer.
- Sem arquivos: campos entre colchetes (`[N]`, `[X%]`, `€ [VALOR]`) e a lista mostra os contratos auditados na sessão.

### Aba 3 — Registro de decisões

Cartões (decisões, diferentes da recomendação, encaminhadas ao compliance), tabela, exportação CSV e JSON. Campos em `contratos_dados`, seção 6.

- **Sobre o projeto:** texto do bootcamp e cartões da equipe com **iniciais** (sem fotos de banco de imagens).

## Design

| Token | Valor |
|---|---|
| Fundo | `#121315` (faixa `#0b0c0e`) |
| Cartão | gradiente `#1f2025 → #17181c`, borda `rgba(200,154,88,.24)`, raio 16 px |
| Dourado | `#c89a58` (destaque `#e4bd7d`) |
| Texto / secundário | `#f0f2f4` / `#9aa5b5` |
| Botão principal | rosé `#d7b9b8 → #c8a2a0`, texto `#171315` |
| Acima do justo | `#e8a462` · Abaixo `#c3a6f0` · Dentro `#8cc7a1` · Revisão manual `#9aa5b5` |
| Aumenta / reduz risco | `#d9825b` / `#7fa7d9` |
| Fontes | títulos Playfair Display; texto DM Sans |
| Abas principais (Revisão · Carteira · Registro) | cartões de 104 px, gradiente escuro; aba ativa com gradiente dourado `#c89a58 → #e4bd7d` e texto `#171315` |
| Etapas do formulário (Dados pessoais · Empréstimo · Dívidas) | abas de texto pequenas, alinhadas à esquerda, sem caixa: cinza `#9aa5b5`, hover só muda a cor, ativa dourada `#e4bd7d` com traço de 2 px `#c89a58`; travada com opacidade 38% |
| Ícones | nada de emoji: ícones de linha brancos (`componentes.icone()`, SVG) no HTML e Material (`icon=":material/...:"`) nos botões; etapa revisada `check_circle`, travada `lock` |

Tema do Streamlit (`.streamlit/config.toml`): `base="dark"`, `primaryColor="#D4AD70"`, `backgroundColor="#080D16"`, `secondaryBackgroundColor="#101A2A"`, `textColor="#F1F0EB"`, `headless=true`, `gatherUsageStats=false`.

## Pronto quando

- `pytest tests/app -v` passa (formatação, régua, motivos, parecer com escape, equidade, leitura e resumo da carteira).
- No navegador: as 4 situações abrem pelos exemplos sem erro; revisão manual mostra aviso sem quebrar; uma decisão é registrada e exportada; a aba da carteira funciona com e sem arquivos.

## Estado em 06/11/2026 e pendências

- **[PRONTO]** as três abas, formulário, casos reais, valores legíveis dos motivos, decisão na sessão.
- **[A CONFIRMAR] (Marcos)** rótulos dos códigos de escolaridade, moradia e verificação (`CODIGOS` em `componentes.py`, tirados do dicionário do Bondora).
- **[PENDENTE] (Yasmin)** mostrar "a.a. nominal" ao lado dos juros.
- **[PENDENTE] (depende de outras frentes)** `juro_pares_mediana` como referência ao lado do juro justo ("Mediana dos pares: X%", oculto quando `null`; até 09/11); `contexto_mercado` do BC no parecer; decisões gravadas no banco e marcação "já decidido" na fila; dados reais da carteira (08/11 e 09/11).

## Estado em 10/11/2026

- **[PRONTO]** emojis trocados por ícones brancos; CSS separado em `estilo.css`; abas principais como cartões e etapas como abas de texto pequenas; etapas travadas e execução só com as 3 confirmações.
- **[DECIDIDO]** sem tela de login: o sistema roda no PC de cada pessoa e o nome do analista é digitado (obrigatório para decidir). Login só faria sentido com o site publicado.
