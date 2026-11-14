-- ---------------------------------------------------------------------
-- 08_view_contrato_modelo.sql
-- Contrato no formato do prever(): uma linha por contrato (179.235), com exatamente as
-- colunas que src/modelos/prever.py e src/modelos/variaveis.py leem. A rota
-- GET /contracts/{id}/analysis lê uma linha pronta e chama prever(dict(linha)), sem
-- montar o join no Python. O prever() aceita a linha do banco como vem (Decimal e date
-- do psycopg; PR #81 do Samuel).
--
-- COLUNAS (levantadas lendo o código, não adivinhadas):
--   * do prever(): loan_id (vira o contrato_id da resposta), data_emprestimo (DATE: safra,
--     custo do dinheiro e margem), juro_aa (juro cobrado, em %), pais, prazo_meses e a checagem
--     de faixa do treino (valor_concedido, prazo_meses, renda_total);
--   * as 21 variáveis do modelo (variaveis.NUMERICAS + CATEGORICAS): 17 vêm direto do banco e
--     4 são calculadas pelo criar_variaveis() (parcela_neutra_sobre_renda, valor_sobre_renda,
--     divida_sobre_renda e renda_relativa), por isso entra também passivos_total.
--   Total: 21 colunas (loan_id, data_emprestimo, juro_aa, passivos_total e as 17 diretas).
--   Fora de propósito: as colunas que só alimentam variáveis descartadas (valor_solicitado,
--   caixa_livre, divida_renda etc.); o criar_variaveis() as preenche com vazio, e elas não
--   entram no modelo. tests/dados/test_contrato_modelo_sql.py confere a lista contra o código.
--
-- RESTRIÇÕES:
--   * nenhuma coluna da COLUNAS_LISTA_NEGRA, com UMA exceção: juro_aa, que é o preço
--     auditado. O prever() o lê como juro cobrado para comparar com o justo; ele não é
--     variável do modelo (variaveis.PROIBIDAS o barra). Confirmado pelo Samuel no PR #81.
--   * nada de COLUNAS_SO_AUDITORIA (genero, idade, estado_civil, n_dependentes) nem cliente_id.
--
-- Consulta da API (normalizar o ID no Python, nunca lower(loan_id) na coluna):
--   SELECT * FROM vw_contrato_modelo WHERE loan_id = %s;
--
-- Roda DEPOIS do 01. Idempotente (CREATE OR REPLACE VIEW).
-- Aplicar em banco existente (PowerShell, na raiz):
--   docker cp db\08_view_contrato_modelo.sql auditor_postgres:/tmp/08.sql
--   docker exec auditor_postgres psql -U postgres -d auditor_db -v ON_ERROR_STOP=1 -f /tmp/08.sql
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_contrato_modelo AS
SELECT e.loan_id,
       e.data_emprestimo,
       e.juro_aa,
       e.valor_concedido,
       e.prazo_meses,
       e.novo_cliente,
       e.tipo_verificacao,
       c.pais,
       c.renda_total,
       c.tempo_emprego_atual,
       c.escolaridade,
       c.tipo_moradia,
       h.passivos_total,
       h.n_emprestimos_anteriores,
       h.valor_emprestimos_anteriores,
       h.passivos_existentes,
       h.quitacoes_antecipadas_qtd,
       h.score_ee_mini,
       h.score_fi_asiakastieto,
       h.score_es_equifax,
       h.score_es_microl
FROM emprestimo e
LEFT JOIN cliente c           ON c.loan_id = e.loan_id
LEFT JOIN historico_credito h ON h.loan_id = e.loan_id;
