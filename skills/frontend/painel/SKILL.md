---
name: auditor-painel
description: Aplique ao criar, alterar ou revisar o front-end do Auditor de Preço Justo (painel Streamlit em src/app) — telas de revisão de contrato, auditoria da carteira e registro de decisões, formulário em etapas travadas, chamadas à API, estilo em estilo.css, ícones e o que pode ou não aparecer na tela.
---

# Front-end: painel do analista (Streamlit)

Ao criar, alterar ou revisar código em `src/app/` ou em `tests/app/`, siga estas regras. O painel **coleta e mostra**: quem calcula e grava é a API. Siga também as skills `auditor-governanca`, `auditor-contratos-dados` e `auditor-api`.

## Antes de começar

- Lembre que o Streamlit roda o `main.py` inteiro a cada clique: guarde o que precisa sobreviver em `st.session_state` e use `@st.cache_data` para leitura pesada.
- Localize a seção certa do `main.py` (numeradas no código): 1 configuração e API · 2 estilo · 3 estado da sessão · 4 comunicação com a API · 5 navbar e home · 6 auditoria (6.1 formulário, 6.2 resultado, 6.3 a 6.5 abas) · 7 sobre a equipe.

## Onde colocar cada coisa

- Telas e chamadas à API em `src/app/main.py`.
- Todo CSS em `src/app/estilo.css`. Não escreva `<style>` no `main.py`.
- Formatação e blocos HTML em `src/app/componentes.py`, **sem importar Streamlit**, para poder testar sozinho.
- Leitura, filtros e resumos do lote em `src/app/carteira.py`.
- Testes em `tests/app/` (`test_componentes.py`, `test_carteira.py`).

## Fronteira com o back-end

- Nunca importe `src.api`, `src.modelos` ou `genai.src` no front. Importe só `src.app.*`, `streamlit`, `requests` e `pandas`.
- Fale com a API só pelas funções da seção 4 (`status_api`, `chamar_api`, `consultar_lista`) e pelo `registrar_decisao`. O endereço vem de `API_URL` (Docker: `http://api:8000`; local: `http://localhost:8000`).
- Rotas usadas: `GET /` (status, cache de 20 s), `POST /prever` (formulário, timeout 30 s), `POST /parecer` (exemplos e carteira), `POST /decisoes`, `GET /decisoes`, `GET /decisoes/atuais`.
- Transforme todo erro técnico (sem conexão, tempo esgotado, 422, 503) em frase em português. Nunca mostre JSON cru na tela.
- Não calcule PD, juro, situação ou equidade no front. A única conta permitida é contar e agrupar o lote da carteira, que já vem calculado.

## Regras de tela

- Formate tudo pelo `componentes.py`: fração → "24,9%", nulo → "—", € com ponto de milhar, juros com "a.a. nominal". Passe todo texto vindo da API por `html.escape`.
- Nunca mostre no resultado de um contrato: gênero, idade, rating ou PD do Bondora. Mostre país só no cabeçalho, nunca como motivo.
- Exija para registrar uma decisão: justificativa e nome do analista. Aceite nova taxa só em "Revisar preço". Gere um `requisicao_id` novo a cada clique.
- Se o banco estiver fora (503), guarde a decisão em `st.session_state` e avise; não perca a decisão.
- Não use emoji. Use `componentes.icone()` (SVG branco) no HTML e `icon=":material/...:"` nos botões.

## Formulário (aba Revisão de contrato)

- Mantenha as 3 etapas travadas (Dados pessoais · Empréstimo · Dívidas & histórico): uma etapa só abre com as anteriores marcadas em "Confirmo que revisei"; voltar é sempre permitido.
- Ao mudar um campo depois de revisado, desmarque a revisão daquela etapa.
- Mantenha "EXECUTAR AUDITORIA DE PREÇO" desabilitado até as 3 caixas, com o aviso "Falta revisar: …", e confira de novo no código antes de chamar a API.
- Campos: idade (18–100) e gênero (só auditoria), país (EE/FI/ES), renda (€) · ID, valor (€), juro cobrado (% a.a., 0–500), prazo (3–60 meses), data de concessão (01/01/2009 até hoje) · total de dívidas (€).

## Visual (`estilo.css`)

Use estes valores; não introduza outras cores:

| Elemento | Valor |
|---|---|
| Fundo / cartão | `#121315` / gradiente `#1f2025 → #17181c`, borda dourada translúcida, raio 16 px |
| Dourado / destaque | `#c89a58` / `#e4bd7d` |
| Texto / secundário | `#f0f2f4` / `#9aa5b5` |
| Fontes | títulos Playfair Display; texto DM Sans |
| Abas principais | cartões de 104 px, raio 16 px, borda e texto dourados; ativa com gradiente dourado, texto `#171315` e brilho |
| Botões principais | gradiente dourado `#c89a58 → #e4bd7d`, texto `#171315` |
| Executar auditoria | branco, borda dourada de 2 px, texto `#171315` |
| Etapas do formulário | abas de texto pequenas, à esquerda, sem caixa; hover só muda a cor; ativa dourada com traço de 2 px; travada com opacidade 38% |
| Situações | acima `#e8a462` · abaixo `#c3a6f0` · dentro `#8cc7a1` · revisão manual `#9aa5b5` |
| Motivos | aumenta risco `#d9825b` · reduz `#7fa7d9` |

## Ao terminar

- Rode `pytest tests/app -v` e confirme que passa.
- No navegador: abra as 4 situações pelos exemplos; confirme que a revisão manual mostra aviso sem quebrar; rode uma auditoria pelo formulário (só libera com as 3 caixas); registre uma decisão e veja no registro; abra a aba da carteira com e sem arquivos.
- Atualize a "Situação atual" abaixo se entregou algo.

## Situação atual (11/11/2026)

- Já existe (não refaça): três abas, formulário com etapas travadas, casos reais, decisões no banco com queda para a sessão, "Decisão atual" na fila, mediana dos pares, referência do BC no parecer, CSS em `estilo.css`, ícones sem emoji, paleta dourada nos botões.
- Decidido: sem tela de login; o nome do analista é digitado e obrigatório para decidir.
- A confirmar (Marcos): rótulos dos códigos de escolaridade, moradia e verificação (`CODIGOS` em `componentes.py`). Até lá, use os do dicionário do Bondora.
