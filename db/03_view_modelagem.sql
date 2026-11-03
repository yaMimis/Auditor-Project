-- =====================================================================
-- Auditor de Preço Justo · base de modelagem
-- PostgreSQL 14+ · idempotente (CREATE OR REPLACE)
--
-- Rodar DEPOIS de 01_schema_bondora.sql (a view lê `emprestimo` e `cliente`).
--
-- Aplica a regra do Samuel (docs/DECISOES.md, seções 1, 2 e 4):
--   * contratos concedidos de 2009 a 2016 e encerrados:
--     status = 'Repaid' OU data_default preenchida;
--   * fora a Eslováquia (pais = 'SK');
--   * alvo `inadimplente` = 1 quando data_default está preenchida;
--   * conjunto 'treino' = 2009 a 2015;
--   * conjunto 'teste'  = 2016, só de clientes que NÃO aparecem no treino;
--   * conjunto 'fora_cliente_repetido' = 2016 de clientes que já estavam
--     no treino (saem do teste para não haver o mesmo cliente nos dois lados).
--
-- Os reestruturados NÃO são excluídos aqui: o texto do DECISOES.md manda
-- excluir, mas o notebook do Samuel não aplica. A coluna `reestruturado`
-- vem só para o filtro, caso o Samuel decida excluí-los
-- (WHERE NOT reestruturado). Ela está na lista negra e nunca vira variável.
--
-- Números esperados (conferir após a carga):
--   treino 20.011 (52,4% de default) · teste 7.311 (67,1%) ·
--   fora_cliente_repetido 2.594 · total 29.916.
--
-- Uso: esta view define QUAIS contratos e QUAL conjunto. As variáveis do
-- modelo vêm de joins com `emprestimo`, `cliente` e `historico_credito`,
-- respeitando as listas de colunas do DATA.md (seção 6).
-- =====================================================================

CREATE OR REPLACE VIEW vw_base_modelagem AS
WITH base AS (
    SELECT e.loan_id,
           c.cliente_id,
           c.pais,
           EXTRACT(YEAR FROM e.data_emprestimo)::int AS ano,
           (e.data_default IS NOT NULL)::int         AS inadimplente,   -- ALVO: nunca é variável
           e.reestruturado                                             -- só para filtro
    FROM emprestimo e
    JOIN cliente c ON c.loan_id = e.loan_id
    WHERE e.data_emprestimo BETWEEN DATE '2009-01-01' AND DATE '2016-12-31'
      AND (e.status = 'Repaid' OR e.data_default IS NOT NULL)
      AND c.pais <> 'SK'
),
clientes_treino AS (
    SELECT DISTINCT cliente_id
    FROM base
    WHERE ano <= 2015
)
SELECT b.loan_id,
       b.cliente_id,
       b.pais,
       b.ano,
       b.inadimplente,
       b.reestruturado,
       CASE
           WHEN b.ano <= 2015 THEN 'treino'
           WHEN NOT EXISTS (SELECT 1 FROM clientes_treino t WHERE t.cliente_id = b.cliente_id)
                THEN 'teste'
           ELSE 'fora_cliente_repetido'
       END AS conjunto
FROM base b;
