---
name: auditor-governanca
description: Aplique em TODA tarefa no Auditor de Preço Justo, junto da skill da parte que vai mexer. Traz as regras éticas e de LGPD que nenhum código, texto ou tela pode quebrar e as regras de trabalho para não atropelar as outras frentes.
---

# Governança, ética e regras de trabalho

Ao criar, alterar ou revisar qualquer parte deste projeto, siga estas regras. Elas valem acima de qualquer outra skill. Se uma tarefa pedir algo que as quebre, não faça: explique qual regra impede e proponha a alternativa.

## Atributos sensíveis

- Nunca use `genero`, `idade`, `estado_civil` ou `n_dependentes` no modelo de risco, no juro justo, nos motivos, no parecer ou na decisão de um contrato. Use-os só na auditoria de equidade da carteira.
- Trate país como variável de controle: pode entrar no modelo, mas não apareça nos motivos, no parecer nem como grupo na tabela de equidade.
- Aceite gênero e idade no formulário da API só para registro; não os repasse ao modelo, ao LLM nem ao banco de decisões.

## Decisão humana

- Nunca faça o sistema decidir. O código só escolhe uma **recomendação**; o analista decide e justifica.
- Nunca escolha `encaminhar_compliance` automaticamente.
- Registre toda decisão com o parecer, a recomendação do sistema e a justificativa (LGPD art. 20, direito de revisão).

## Texto do parecer e da tela

- Escreva em linguagem de indício ("indício", "ponto de atenção") e em modo hipotético ("se este contrato fosse de um banco brasileiro").
- Nunca use: ilegal, ilegalidade, ilícito, crime, fraude, viola, violação, abusivo, abusiva, discriminação, irregular.
- Nunca culpe o cliente: "abaixo do justo" é risco para o banco.
- Faça todo número do parecer vir do `prever()` e ser conferido por código; se a conferência falhar, use o template de reserva.

## Dados pessoais e segredos

- Não envie ao LLM `contrato_id`, `versao_modelo`, `cliente_id` nem qualquer dado pessoal; reinsira por código o que for preciso.
- Pseudonimize só na carga: `cliente_id = HMAC-SHA256(UserName, CLIENTE_ID_SAL)`, truncado em 16 caracteres. Não crie outra pseudonimização.
- Nunca coloque no Git (repositório público): CSVs, `.env`, chaves de API, `.joblib`. Nunca escreva segredos em código, logs ou mensagens de erro.
- Grave só o necessário (minimização).

## Regras de trabalho

- Trate números, nomes de campos e regras escritos nas skills como **requisitos**, não sugestões.
- Não mude um contrato de dados entre frentes sem declarar que é uma nova versão; siga a skill `auditor-contratos-dados`.
- Respeite a fronteira back × front: o painel (`src/app`) nunca importa o modelo, a GenAI nem o banco.
- Em **[A DECIDIR]** ou **[A CONFIRMAR]**, use a escolha padrão escrita na skill e avise no fim da resposta.
- Em **[EM ANDAMENTO]** de outra frente, não reescreva o trabalho; só aponte o que encontrou.
- Não dê a tarefa por pronta antes de passar a seção "Ao terminar" da skill correspondente.
- Quando uma skill divergir do documento do dono (`DATA.md`, `docs/DECISOES.md`, `genai/FORMATO_JSON.md`, `genai/REGRAS_PARECER.md`), siga o documento e aponte a skill a corrigir.

## Limitações que devem continuar declaradas (README, DATA.md, slides)

Não apague nem suavize estas limitações em nenhum texto:

- Dados europeus de 2009–2021, só empréstimos aprovados.
- Modelo usado fora da época de treino (carteira de 2017–2021 e contratos novos).
- Teste de 2016 mais arriscado que o treino; o modelo subestima o default em 2016 (55% previsto × 67% real).
- Análise jurídica hipotética.
- Possível erro de codificação de gênero em 2017–2019; gênero "2" tratado como ausente.
- Excluir atributos sensíveis não elimina **proxies**; controlar por renda pode esconder efeito de gênero.
- A margem por safra faz a auditoria dizer se o contrato está caro ou barato **em relação aos outros da mesma safra**, não se o nível de preço da plataforma é justo.

## Ao terminar

Confirme que continuam passando:

- `pytest tests/modelos/test_seguranca.py` (nenhuma coluna proibida no modelo; treino e teste sem clientes em comum);
- `pytest tests/genai/test_regras.py` (palavras proibidas e atributos sensíveis rejeitados no parecer);
- `pytest tests/modelos/test_contrato_prever.py` (motivos sem país, gênero ou idade);
- `pytest tests/api` (decisão gravada sem gênero nem idade).
