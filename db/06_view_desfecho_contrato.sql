-- ---------------------------------------------------------------------
-- 06_view_desfecho_contrato.sql
-- Desfecho por contrato: uma linha para CADA contrato de `emprestimo` (179.235),
-- dizendo o que aconteceu com ele (inadimplente, resultado em euros, principal
-- perdido) ou, quando não há desfecho, por quê. Serve à tela "Análise do contrato".
--
-- Roda DEPOIS do 04 (lê a vw_retorno_realizado). Idempotente (CREATE OR REPLACE).
--
-- Quem tem desfecho: os contratos da vw_retorno_realizado, que são os da
-- vw_base_modelagem (29.916). Os outros recebem um motivo, testado na MESMA ordem
-- e com os MESMOS filtros do db/03_view_modelagem.sql:
--   1. data_emprestimo depois de 31/12/2016      -> 'concedido depois de 2016'
--   2. pais = 'SK'                               -> 'Eslováquia (fora da base)'
--   3. nem status = 'Repaid' nem data_default    -> 'não encerrado até o corte de 20/07/2021'
-- Se a regra do 03 mudar, mude aqui também (o tests/dados/test_desfecho_sql.py
-- confere os textos; a validacao.py confere que todo contrato sem desfecho tem motivo).
--
-- Colunas do desfecho vêm da vw_retorno_realizado por LEFT JOIN: ficam vazias
-- quando não há desfecho. Definições delas no cabeçalho do 04.
--
-- PRIVACIDADE: sem gênero, idade, estado civil e dependentes (a API lê esta view).
--
-- Consulta da API (o loan_id fica em minúsculas no banco: normalizar o ID digitado
-- com .strip().lower() no Python, nunca lower(loan_id) na coluna, que desliga o índice):
--   SELECT * FROM vw_desfecho_contrato WHERE loan_id = %s;
-- Depois da busca, o loan_id que VOLTOU do banco vira o contrato_id em todo o fluxo
-- (prever, parecer, taxa do BC e decisão); as simulações mantêm o nome digitado.
-- O db/07 normaliza também no gatilho das decisões, como segunda barreira.
--
-- Números esperados (banco completo):
--   179.235 linhas · 29.916 com desfecho · 147.978 concedidos depois de 2016 ·
--   1.045 não encerrados · 296 da Eslováquia · soma de resultado_eur ≈ −0,01 mi €.
--
-- Aplicar em banco existente (PowerShell, na raiz):
--   docker cp db\06_view_desfecho_contrato.sql auditor_postgres:/tmp/06.sql
--   docker exec auditor_postgres psql -U postgres -d auditor_db -v ON_ERROR_STOP=1 -f /tmp/06.sql
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_desfecho_contrato AS
SELECT e.loan_id,
       EXTRACT(YEAR FROM e.data_emprestimo)::int AS ano,
       c.pais,
       (r.loan_id IS NOT NULL)                   AS tem_desfecho,
       CASE
           WHEN r.loan_id IS NOT NULL                          THEN NULL
           WHEN e.data_emprestimo > DATE '2016-12-31'          THEN 'concedido depois de 2016'
           WHEN c.pais = 'SK'                                  THEN 'Eslováquia (fora da base)'
           WHEN e.status IS DISTINCT FROM 'Repaid'
                AND e.data_default IS NULL                     THEN 'não encerrado até o corte de 20/07/2021'
       END                                       AS motivo_sem_desfecho,
       r.inadimplente,
       r.valor_concedido,
       r.recebido_total,
       r.resultado_eur,
       r.retorno_realizado,
       r.principal_perdido,
       r.conjunto,
       r.reestruturado
FROM emprestimo e
LEFT JOIN cliente c              ON c.loan_id = e.loan_id
LEFT JOIN vw_retorno_realizado r ON r.loan_id = e.loan_id;
