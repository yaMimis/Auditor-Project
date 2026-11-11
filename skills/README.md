# Skills do Auditor de Preço Justo

Instruções para uma IA trabalhar neste projeto. Cada `SKILL.md` fala direto com a IA: diz quando aplicar (`description`), o que fazer, o que não fazer e como conferir no fim. Para uma tarefa, entregue à IA **a skill da parte que vai mudar + `auditor-governanca`** (que vale sempre e traz as regras de trabalho).

## Mapa

| Pasta | Skill (`name`) | Aplique ao… | Dono |
|---|---|---|---|
| `projeto/visao-geral` | `auditor-visao-geral` | começar uma tarefa ou explicar o projeto | grupo |
| `projeto/governanca` | `auditor-governanca` | **qualquer tarefa** (ética, LGPD, regras de trabalho) | grupo |
| `projeto/contratos-dados` | `auditor-contratos-dados` | mexer em dado que passa entre frentes | Maria (documento) |
| `projeto/estrutura` | `auditor-estrutura` | criar, mover ou procurar arquivos; back × front | Yasmin |
| `projeto/boas-praticas-python` | `auditor-boas-praticas-python` | escrever qualquer código, teste, commit ou documento | grupo |
| `dados/base-de-dados` | `auditor-base-de-dados` | cargas, tabelas, views, qualidade dos dados | Marcos |
| `modelo/risco` | `auditor-modelo-risco` | modelo de PD, variáveis, faixas, motivos | Samuel |
| `modelo/juro-justo` | `auditor-juro-justo` | juro justo, margem, incerteza, pares | Samuel |
| `modelo/auditoria-carteira` | `auditor-auditoria-carteira` | lote da carteira, equidade, backtest | Samuel |
| `genai/normas-rag` | `auditor-normas-rag` | normas, trechos, indexação, busca | Maria |
| `genai/parecer` | `auditor-parecer` | texto do parecer, prompt, Gemini, checagem | Maria |
| `genai/avaliacao-parecer` | `auditor-avaliacao-parecer` | medir o parecer antes de trocar prompt ou modelo | Maria |
| `backend/api` | `auditor-api` | rotas, schemas, banco, erros da API | Yasmin |
| `frontend/painel` | `auditor-painel` | telas, formulário, visual, chamadas à API | Yasmin |
| `infra/ambiente-docker-ci` | `auditor-infra` | requirements, Docker, `iniciar.ps1`, CI | Yasmin (Terraform: Marcos) |

## Formato de cada skill

- **Frontmatter:** `name` (`auditor-...`) e `description` começando por "Aplique ao/em...": é o que a IA lê para decidir usar a skill.
- **Abertura:** "Ao criar, alterar ou revisar X, siga estas regras" + as outras skills que valem junto, pelo `name`.
- **Seções no imperativo:** onde colocar cada coisa, regras, o que não fazer.
- **Ao terminar:** comandos e conferências antes de dar a tarefa por pronta.
- **Situação atual (data):** o que já existe (não refazer), o que está em andamento com outra pessoa (não alterar) e o que está a decidir (usar o padrão). É a única seção que muda a cada entrega: atualize no mesmo PR.

Organização atualizada em **11/11/2026**.
