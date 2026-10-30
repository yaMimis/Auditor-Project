-- =====================================================================
-- Auditor de Preço Justo · séries mensais do custo do dinheiro
-- PostgreSQL 14+ · idempotente (pode rodar mais de uma vez)
--
--   euribor_mensal  Euribor de 3 e de 12 meses (Portal de dados do BCE)
--   selic_mensal    Selic da leitura A do "modo Brasil" (Banco Central)
--
-- Chave: `mes` é sempre o 1º dia do mês. Os arquivos do BCE trazem o último
-- dia do mês, e a carga converte. A junção com os contratos é pelo mês de
-- `emprestimo.data_emprestimo`:
--
--   SELECT * FROM vw_custo_do_dinheiro;   -- uma linha por contrato, com as taxas do mês da concessão
--
-- Rodar DEPOIS de 01_schema_bondora.sql: a view abaixo lê a tabela `emprestimo`.
--
-- As tabelas guardam o histórico completo dos arquivos (euribor desde 1994,
-- Selic desde 1986). O recorte do projeto é 01/2009 a 07/2021 (DATA.md, seção 9).
-- Valores em % ao ano. A Euribor pode ser negativa (de 2015–2016 em diante).
-- =====================================================================

CREATE TABLE IF NOT EXISTS euribor_mensal (
    mes          DATE PRIMARY KEY,             -- 1º dia do mês
    euribor_3m   NUMERIC(10,7),                -- % a.a., média das observações do mês (FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA)
    euribor_12m  NUMERIC(10,7)                 -- % a.a., média das observações do mês (FM.M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA)
);

CREATE TABLE IF NOT EXISTS selic_mensal (
    mes            DATE PRIMARY KEY,           -- 1º dia do mês
    selic_aa       NUMERIC(10,2),              -- % a.a., Selic acumulada no mês anualizada base 252 (BCB, SGS 4189)
    selic_meta_aa  NUMERIC(6,2)                -- % a.a., meta Selic no 1º dia do mês (Dados de Mercado); só conferência
);

-- ---------------------------------------------------------------------
-- vw_custo_do_dinheiro: cada contrato ligado às taxas do mês da concessão.
-- LEFT JOIN de propósito: contrato sem taxa aparece com NULL em vez de sumir
-- (a carga confere que isso não acontece na janela 01/2009 a 07/2021).
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_custo_do_dinheiro AS
SELECT e.loan_id,
       e.data_emprestimo,
       date_trunc('month', e.data_emprestimo)::date AS mes,
       t.euribor_3m,
       t.euribor_12m,
       s.selic_aa
FROM emprestimo e
LEFT JOIN euribor_mensal t ON t.mes = date_trunc('month', e.data_emprestimo)::date
LEFT JOIN selic_mensal   s ON s.mes = date_trunc('month', e.data_emprestimo)::date;
