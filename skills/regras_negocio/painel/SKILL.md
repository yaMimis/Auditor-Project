---
name: auditor-painel
description: Use para construir ou alterar o painel Streamlit do CredFlare — páginas Início, Contratos, Análise, Laboratório, Auditoria, Registro e Sobre, chamadas à API, estilo, ícones e o que pode ou não aparecer na tela.
---

# Painel do analista (Streamlit)

> Leia antes: `regras_negocio/governanca`, `regras_negocio/contratos_dados`, `regras_negocio/api`. Dono: Yasmin. Código: `src/app/main.py` (moldura: estilo, sessão, menu e despacho), `src/app/nucleo.py` (chamadas à API, cache do lote, navegação), `src/app/paginas/*.py` (uma página por arquivo), `src/app/components/` (formatação e HTML por página, sem Streamlit), `src/app/styles/*.css` (visual por parte, carregado em ordem); testes `tests/app/test_components.py`.

## Objetivo

Dar ao analista, para cada contrato da base, **o risco, o preço, o porquê, o parecer e um lugar para testar cenários**, mais o panorama da carteira e o registro das decisões, sem que o painel calcule, leia arquivo ou decida nada.

## Regras

1. O painel **só pede e mostra**. Nenhum cálculo de juro, PD, parcela, situação ou equidade, e nem leitura de `docs/resultados/`: o lote vem da API (`/portfolio/overview`, `/contracts...`). Os filtros vão como parâmetros para a API.
2. Não importe `src.api`, `src.modelos` nem `genai.src` no painel. Fale com a API só pelas funções da seção 4 do `main.py` (`api_status`, `post_api`, `get_api`, `get_list`) e por `post_decision`. Endereço em `API_URL` (Docker `http://api:8000`; local `http://localhost:8000`); timeout de 30 s para análise e cenário.
3. Todo erro técnico vira frase em português; nunca JSON cru na tela. Todo texto vindo da API passa por `html.escape`; HTML compactado antes do `st.markdown`.
4. **Nunca** mostrar na Análise nem no Laboratório: gênero, idade, rating ou PD do Bondora. Gênero e idade só na Auditoria, em números agregados (ou no teste de invariância, sem os valores reais).
5. **País:** aparece no cabeçalho e em "Dados direto do contrato" (é dado de entrada). Não aparece entre os motivos: o cartão diz que o modelo considera o mercado do contrato (país), que ele fica fora da lista por regra do projeto e que os pesos foram calculados sem ele.
6. **Procedência e selos honestos:** "Calculado agora pelo modelo" só quando `procedencia.modo == "ao_vivo"`; com `modo == "lote"`, selo "Valores do lote", aviso no topo e a linha "Por que o lote". A incerteza mostra o número de reamostragens; sem bootstrap, diz "PD sem intervalo" e que os ±2 p.p. são margem do juro justo.
7. **Decisão:** justificativa e nome do analista obrigatórios; nova taxa só em "Revisar preço"; `requisicao_id` novo a cada clique. Banco fora = **"Decisão NÃO registrada"** (erro, não aviso), rascunho em `st.session_state.pending_decisions` e "Tentar gravar de novo" no Registro (mesmo `requisicao_id`). O Registro conta e exporta só o que veio do banco. Nunca mostrar como concluída uma decisão que só existe na memória da tela.
8. Sem emoji: `components.line_icon()` (SVG) no HTML e `icon=":material/...:"` nos botões.

## Páginas

Menu do topo com botões (não `st.tabs`, porque o painel troca de página sozinho); a página aberta fica em `st.session_state.page` e troca por callback (`go_to`).

- **Menu do topo:** nomes curtos (Início, Contratos, Análise, Laboratório, Auditoria, Registro, Sobre) para caberem inteiros; o título de cada página traz o nome completo.
- **Início (Home):** hero, faixa explicativa e Panorama da carteira: título, filtros e botão "Ver os contratos", cartões, e lado a lado "Situação do preço por faixa" e "Backtest 2016". A equidade fica só na Auditoria. Cada cartão tem um ícone "i" (aparece ao passar o mouse; clicar abre a explicação, textos em `INFO` em `src/app/components/base.py`).
- **Contratos da base:** busca única (filtra a cada caractere; escolher ou digitar um ID abre), chips de situação, "Exportar CSV" e lista com **Abrir** por linha.
- **Análise do contrato** (`GET /contracts/{id}/analysis`): cabeçalho e selos → Procedência (recolhida, clique para abrir) → alerta de revisão manual → cartões → régua → lado a lado "Dados direto do contrato" (aberto, à esquerda) e Precificação (à direita) → botão dourado "Ver resultado observado", embaixo da Precificação (abre ali mesmo) → lado a lado parecer (esquerda) e "O que mais pesou" (direita) → decisão. O parecer traz o selo "Simulação normativa pela lei brasileira"; os dados mostram 17 fornecidas e 4 calculadas; o Resultado observado mostra "Sem desfecho" com o motivo da `vw_desfecho_contrato` quando o contrato não terminou. No fim, antes da decisão, o cartão "E se o contrato fosse diferente?" com o botão **"Abrir no Laboratório"** (desligado no modo lote).
- **Laboratório** (`POST /contracts/{id}/scenario`): ao abrir, pede o original e os campos (`{}`); formulário com valor, prazo, renda mensal, parcelas mensais das dívidas (`passivos_total`, **não** o saldo devedor), número de dívidas, empréstimos anteriores, tempo no emprego (sem `Retiree` e `Other`, que não aparecem no treino) e verificação da renda (limites da API: faixa vista no treino, 0,5% a 99,5%) e o **juro cobrado à parte** (não é variável do modelo). "Recalcular com o modelo" manda só o que mudou. Mostra **Original × recalculado** (PD, faixa, juro justo, margem, juro cobrado, parcela, situação; o que mudou em dourado) e **O que mudou o risco** (cada campo trocado sozinho). Com erro, nenhum cenário anterior fica na tela. **"Usar como proposta"** (só se o juro mudou) leva o juro para "Nova taxa proposta" na Análise, **sem registrar nada**. "Voltar aos valores do contrato" limpa o formulário.
- **Auditoria:** abre explicando as duas perguntas (o preço trata grupos de forma diferente a risco igual? → equidade agregada; o nosso modelo usa gênero ou idade? → invariância). Equidade agregada e **teste de invariância**: resumo em lote (`invariancia_lote` do `/portfolio/overview`; sem o arquivo, mostra o comando para gerá-lo) e o teste de um contrato (`POST /contracts/{id}/invariance`): campo do ID (começa com o contrato aberto na Análise), "Rodar o teste", veredito ("Resultado idêntico" em verde ou "Resultado diferente em: …" em laranja) e a tabela Original × Gênero e idade trocados. Diz que não prova que o preço é justo e nunca mostra o gênero nem a idade reais. **Registro:** contadores, tabela, exportação CSV e JSON, rascunhos pendentes à parte. **Sobre:** equipe (com foto, se houver em `src/app/imagens/equipe/`) e onde cada parte do estudo aparece. A capa da Home usa `src/app/imagens/capa.jpg`, se existir.

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
- No navegador: abrir um contrato pela busca e outro pela lista; conferir procedência, precificação, motivos, dados direto do contrato e resultado observado; desligar o banco e ver o plano B ("Por que o lote"); abrir um contrato em revisão manual; no Laboratório, mudar só o juro (PD e juro justo iguais, situação e parcela mudam) e depois o prazo (o modelo recalcula a PD); "Usar como proposta" preenche a taxa na Análise; registrar uma decisão e vê-la no Registro; com o banco fora, a decisão aparece como não registrada; na Auditoria, o teste de invariância dá "Resultado idêntico".

## Estado em 16/11/2026

- **[CONCLUÍDO] (Yasmin, 14/11)** Etapas 1 e 2: conferência com dados reais 20/20 (`scripts/conferir_analise.py`, pacote `48784ba3742d`).
- **[DECIDIDO]** sem formulário de contrato novo e sem "caso de exemplo": o analista trabalha com contratos da base. Sem tela de login; o nome do analista é digitado.
- **[PRONTO] (Yasmin)** Etapa 3: página Auditoria com a equidade agregada e o teste de invariância (um contrato na hora e 500 contratos em lote: 500 de 500 idênticos, `docs/resultados/invariancia_lote.json`).
- **[PRONTO]** rótulos dos códigos de escolaridade, moradia e verificação tirados do dicionário do Bondora (`CODE_LABELS` em `src/app/components/analise.py`).

## Logo (17/11)

- **CredFlare:** a linha de um gráfico que sobe e termina numa estrela dourada, e o nome Cred (creme `#F2EFE8`) + Flare (dourado `#D6AC6E`). `html_logo()` em `components/base.py` desenha em SVG/HTML, sem arquivo externo: pequeno no menu do topo, grande e animado na capa da Início (a linha se desenha, a estrela acende e pisca duas vezes, o nome aparece; CSS em `styles/10_logo.css`). Ícone da aba: `imagens/credflare_icone.png`. Versões para slides e documentos: `docs/figuras/logo/` (fundo escuro, fundo claro e ícone, em SVG e PNG).

## Auditoria e Registro (16/11)

- **Auditoria:** lado a lado, equidade agregada (esquerda, gráfico com ponto = diferença e barra = IC 95% em torno do zero) e teste de invariância (direita: anel "500 de 500" do lote e o teste de um contrato com a coluna "Igual?").
- **Registro:** botões CSV e JSON no canto direito, ao lado do título.
