---
name: auditor-governanca
description: Use em qualquer tarefa do Auditor de Preço Justo que toque dados pessoais, atributos sensíveis, decisão sobre contratos, texto do parecer ou o que vai para o LLM — regras éticas e de LGPD que nenhum setor pode quebrar.
---

# Governança e ética (não negociável)

> Leia antes: `visao-geral`. Vale para **todos** os setores; envie sempre junto com o setor em que a IA vai trabalhar.

## Objetivo

Garantir que o sistema **apoia** a decisão sem discriminar, sem expor pessoas e sem afirmar conclusões jurídicas.

## Regras

1. **Atributos sensíveis só auditam, nunca decidem.** `genero`, `idade`, `estado_civil` e `n_dependentes` nunca entram no modelo de risco, no juro justo, nos motivos nem no parecer de um contrato. Servem só para a auditoria de equidade da carteira.
2. **País é controle, não grupo auditado.** Entra no modelo (o risco varia entre países), mas não aparece nos motivos nem no parecer, e não é linha da tabela de equidade.
3. **O sistema nunca decide sozinho.** O código escolhe uma **recomendação**; o analista decide e justifica. `encaminhar_compliance` existe, mas **nunca** é escolhida automaticamente. Toda decisão fica registrada com o parecer, a recomendação do sistema e a justificativa (LGPD art. 20, direito de revisão).
4. **Linguagem de indício.** O parecer fala em "indício" e "ponto de atenção", em modo hipotético ("se este contrato fosse de um banco brasileiro"). Nunca: ilegal, ilegalidade, ilícito, crime, fraude, viola, violação, abusivo, abusiva, discriminação, irregular.
5. **Números checados por código.** Todo número do parecer vem do `prever()` e é conferido contra a entrada. Falhou → template de reserva.
6. **Nada de identificador no LLM.** `contrato_id`, `versao_modelo`, `cliente_id` e qualquer dado pessoal não vão ao LLM; o código reinsere o que for preciso depois.
7. **Pseudonimização.** `cliente_id = HMAC-SHA256(UserName, CLIENTE_ID_SAL)` truncado em 16 caracteres, feito **só na carga**. A chave fica no `.env`, é igual para o grupo, e trocá-la exige recarregar o banco.
8. **Dados brutos e segredos fora do Git** (repositório público): CSVs, `.env`, chaves de API, `.joblib`.
9. **Nunca culpar o cliente.** "Abaixo do justo" é risco para o banco, não falha do cliente.
10. **Minimização.** A API aceita gênero e idade no formulário só para registro de auditoria e **não** os repassa ao modelo nem ao LLM. Nada além do necessário é gravado.

## Limitações que devem estar declaradas (README, DATA.md, slides)

- Dados europeus de 2009–2021, só empréstimos aprovados.
- Modelo usado fora da época de treino (carteira de 2017–2021 e contratos novos).
- Teste de 2016 mais arriscado que o treino; o modelo subestima o default em 2016 (55% previsto × 67% real).
- Análise jurídica hipotética.
- Possível erro de codificação de gênero em 2017–2019; gênero "2" (indefinido) tratado como ausente.
- Excluir atributos sensíveis do modelo não elimina **proxies**; controlar por renda pode esconder efeito de gênero.
- Margem por safra calibrada para a média do juro justo igualar a média do cobrado: por construção, a auditoria diz se cada contrato está caro ou barato **em relação aos outros da mesma safra**, não se o nível de preço da plataforma é justo.

## Pronto quando

- `tests/modelos/test_seguranca.py`: nenhuma coluna proibida no modelo; treino e teste sem clientes em comum.
- `tests/genai/test_regras.py`: palavras proibidas e atributos sensíveis rejeitados no parecer.
- `tests/modelos/test_contrato_prever.py`: motivos sem país, gênero ou idade.
- O painel não mostra gênero/idade no resultado de um contrato e não oferece decisão automática.
