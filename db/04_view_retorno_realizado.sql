-- ---------------------------------------------------------------------
-- 04_view_retorno_realizado.sql
-- Retorno realizado por contrato: quanto o Bondora recebeu de volta, em euros,
-- comparado com o que emprestou. Serve para o backtest ("os contratos abaixo do
-- justo deram mais prejuízo?") e para o ROI da carteira.
--
-- Roda DEPOIS do 03 (parte da vw_base_modelagem, então herda os mesmos filtros:
-- concessões 2009–2016, só encerrados, sem a Eslováquia). Se a regra da coorte
-- mudar no 03, esta view acompanha sozinha.
--
-- As colunas de pagamento são PÓS-CONCESSÃO: ficam na lista negra do modelo.
-- Aqui elas só medem o resultado; nunca entram como variável.
--
-- DEFINIÇÕES (conferidas nos dados):
--   recebido_total = principal_pago + juros_multas_pagos.
--     As RECUPERAÇÕES JÁ ESTÃO DENTRO desses dois campos: para os contratos em
--     default, valor_concedido = principal_pago + principal_baixado + saldo_principal
--     fecha em 98% dos casos, e subtrair a recuperação quebra a conta (36%).
--     Somar a recuperação de novo contaria o mesmo dinheiro duas vezes (o retorno
--     médio iria de +2,4% para +21,7%). Por isso recuperado_eur é só informativo.
--   resultado_eur  = recebido_total - valor_concedido (euros; negativo = prejuízo).
--   retorno_realizado = resultado_eur / valor_concedido (nunca menor que -1).
--   principal_perdido = parte do valor concedido que não voltou.
--   duracao_meses  = meses da concessão até o último pagamento (pode ser vazio).
--
-- LIMITES: não desconta o tempo (sem taxa de desconto) e só vale para contratos
-- encerrados; contratos ainda ativos não têm retorno final.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_retorno_realizado AS
SELECT b.loan_id,
       b.ano,
       b.pais,
       b.conjunto,
       b.reestruturado,
       b.inadimplente,
       e.valor_concedido,
       e.prazo_meses,
       e.juro_aa,
       CAST((e.data_ultimo_pagamento - e.data_emprestimo) / 30.44 AS DOUBLE PRECISION) AS duracao_meses,
       COALESCE(e.principal_pago, 0)                                   AS principal_recebido,
       COALESCE(e.juros_multas_pagos, 0)                               AS juros_recebidos,
       COALESCE(e.principal_pago, 0) + COALESCE(e.juros_multas_pagos, 0) AS recebido_total,
       COALESCE(e.principal_pago, 0) + COALESCE(e.juros_multas_pagos, 0)
           - e.valor_concedido                                         AS resultado_eur,
       CAST(COALESCE(e.principal_pago, 0) + COALESCE(e.juros_multas_pagos, 0)
            - e.valor_concedido AS DOUBLE PRECISION)
           / NULLIF(e.valor_concedido, 0)                              AS retorno_realizado,
       CASE WHEN e.valor_concedido > COALESCE(e.principal_pago, 0)
            THEN e.valor_concedido - COALESCE(e.principal_pago, 0)
            ELSE 0 END                                                 AS principal_perdido,
       COALESCE(e.recuperacao_principal, 0) + COALESCE(e.recuperacao_juros, 0) AS recuperado_eur
FROM vw_base_modelagem b
JOIN emprestimo e ON e.loan_id = b.loan_id;
