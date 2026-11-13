---
name: auditor-painel
description: Use para construir ou alterar o painel Streamlit do Auditor de Preço Justo — páginas Home, Contratos da base, Análise do contrato, Laboratório, Auditoria, Registro e Sobre, chamadas à API, estilo, ícones e o que pode ou não aparecer na tela.
---

# Painel do analista (Streamlit)

> Leia antes: `regras_negocio/governanca`, `regras_negocio/contratos_dados`, `regras_negocio/api`. Dono: Yasmin. Código: `src/app/main.py` (páginas e chamadas à API), `src/app/styles.css` (todo o CSS; o `main.py` só injeta), `src/app/components.py` (formatação e HTML, sem Streamlit); testes `tests/app/test_components.py`.

## Objetivo

Dar ao analista, para cada contrato da base, **o risco, o preço, o porquê, o parecer e um lugar para testar cenários**, mais o panorama da carteira e o registro das decisões, sem que o painel calcule, leia arquivo ou decida nada.

## Regras

1. O painel **só pede e mostra**. Nenhum cálculo de juro, PD, parcela, situação ou equidade, e nem leitura de `docs/resultados/`: o lote vem da API (`/portfolio/overview`, `/contracts...`). Os filtros vão como parâmetros para a API.
2. Não importe `src.api`, `src.modelos` nem `genai.src` no painel. Fale com a API só pelas funções da seção 4 do `main.py` (`api_status`, `post_api`, `get_api`, `get_list`) e por `post_decision`. Endereço em `API_URL` (Docker `http://api:8000`; local `http://localhost:8000`); timeout de 30 s para análise e cenário.
3. Todo erro técnico vira frase em português; nunca JSON cru na tela. Todo texto vindo da API passa por `html.escape`; HTML compactado antes do `st.markdown`.
4. **Nunca** mostrar na Análise nem no Laboratório: gênero, idade, rating ou PD do Bondora. Gênero e idade só na Auditoria, em números agregados (ou no teste de invariância, sem os valores reais).
5. **País:** aparece no cabeçalho e em "Dados considerados" (é dado de entrada). Não aparece entre os motivos: o cartão diz que o modelo considera o mercado do contrato (país), que ele fica fora da lista por regra do projeto e que os pesos foram calculados sem ele.
6. **Procedência e selos honestos:** "Calculado agora pelo modelo" só quando `procedencia.modo == "ao_vivo"`; com `modo == "lote"`, selo "Valores do lote", aviso no topo e a linha "Por que o lote". A incerteza mostra o número de reamostragens; sem bootstrap, diz "PD sem intervalo" e que os ±2 p.p. são margem do juro justo.
7. **Decisão:** justificativa e nome do analista obrigatórios; nova taxa só em "Revisar preço"; `requisicao_id` novo a cada clique. Banco fora = **"Decisão NÃO registrada"** (erro, não aviso), rascunho em `st.session_state.pending_decisions` e "Tentar gravar de novo" no Registro (mesmo `requisicao_id`). O Registro conta e exporta só o que veio do banco. Nunca mostrar como concluída uma decisão que só existe na memória da tela.
8. Sem emoji: `components.line_icon()` (SVG) no HTML e `icon=":material/...:"` nos botões.

## Páginas

Menu do topo com botões (não `st.tabs`, porque o painel troca de página sozinho); a página aberta fica em `st.session_state.page` e troca por callback (`go_to`).

- **Home:** hero, faixa explicativa e Panorama da carteira (filtros, cartões, situação por faixa, equidade, backtest).
- **Contratos da base:** busca única (filtra a cada caractere; escolher ou digitar um ID abre), chips de situação, "Exportar CSV" e lista com **Abrir** por linha.
- **Análise do contrato** (`GET /contracts/{id}/analysis`): cabeçalho e selos → Procedência → alerta de revisão manual → cartões → régua → Precificação → motivos (SHAP) | parecer com o selo "Simulação normativa pela lei brasileira" → Dados considerados (17 fornecidas × 4 derivadas, com a nota de que o valor total das dívidas só entra na conta de "dívidas em relação à renda") → Resultado observado → decisão. Botão **"Abrir no Laboratório"** (desligado no modo lote).
- **Laboratório** (`POST /contracts/{id}/scenario`): ao abrir, pede o original e os campos (`{}`); formulário com valor, prazo, renda, valor e número de dívidas, empréstimos anteriores, tempo no emprego e verificação da renda (limites da API: do treino ou provisórios, com a fonte no "?" do campo) e o **juro cobrado à parte** (não é variável do modelo). "Recalcular com o modelo" manda só o que mudou. Mostra **Original × recalculado** (PD, faixa, juro justo, margem, juro cobrado, parcela, situação; o que mudou em dourado) e **O que mudou o risco** (cada campo trocado sozinho). Com erro, nenhum cenário anterior fica na tela. **"Usar como proposta"** (só se o juro mudou) leva o juro para "Nova taxa proposta" na Análise, **sem registrar nada**. "Voltar aos valores do contrato" limpa o formulário.
- **Auditoria:** equidade agregada (teste de invariância na Etapa 3). **Registro:** contadores, tabela, exportação CSV e JSON, rascunhos pendentes à parte. **Sobre:** equipe e onde cada parte do estudo aparece.

## Design

| Token | Valor |
|---|---|
| Fundo / cartão | `#121315` / gradiente `#1f2025 → #17181c`, borda dourada translúcida, raio 16 px |
| Dourado / destaque | `#c89a58` / `#e4bd7d` (também marca o que mudou no Laboratório) |
| Texto / secundário | `#f0f2f4` / `#9aa5b5` |
| Fontes | títulos Playfair Display; texto DM Sans |
| Selos da Análise | "Calculado agora" fundo `#c89a58` · "Valores do lote" fundo `#f2b48a`, texto `#121315` |
| Situações | acima `#e8a462` · abaixo `#c3a6f0` · dentro `#8cc7a1` · revisão manual `#9aa5b5` |
| Motivos e efeitos | aumenta risco `#d9825b` · reduz `#7fa7d9` |

## Pronto quando

- `pytest tests/app -v` passa.
- No navegador: abrir um contrato pela busca e outro pela lista; conferir procedência, precificação, motivos, dados considerados e resultado observado; desligar o banco e ver o plano B ("Por que o lote"); abrir um contrato em revisão manual; no Laboratório, mudar só o juro (PD e juro justo iguais, situação e parcela mudam) e depois o prazo (o modelo recalcula a PD); "Usar como proposta" preenche a taxa na Análise; registrar uma decisão e vê-la no Registro; com o banco fora, a decisão aparece como não registrada.

## Estado em 13/11/2026

- **[EM ANDAMENTO] (Yasmin)** Etapas 1 e 2 implementadas, com simulação do painel e testes locais; **não concluídas** até a conferência com o pacote oficial (`scripts/conferir_analise.py` 20/20).
- **[DECIDIDO]** sem formulário de contrato novo e sem "caso de exemplo": o analista trabalha com contratos da base. Sem tela de login; o nome do analista é digitado.
- **[PENDENTE] (Yasmin)** Etapa 3: teste de invariância na Auditoria.
- **[A CONFIRMAR] (Marcos)** rótulos dos códigos de escolaridade, moradia e verificação (`CODE_LABELS` em `components.py`, do dicionário do Bondora).
