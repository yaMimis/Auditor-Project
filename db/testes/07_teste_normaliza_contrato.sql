-- ---------------------------------------------------------------------
-- Teste do gatilho de normalização do contrato (db/07_normaliza_contrato_decisao.sql),
-- no Postgres de verdade. Tudo roda numa transação que é DESFEITA no fim: nada fica gravado.
--
--   docker cp db\07_normaliza_contrato_decisao.sql auditor_postgres:/tmp/07.sql
--   docker cp db\testes\07_teste_normaliza_contrato.sql auditor_postgres:/tmp/07t.sql
--   docker exec auditor_postgres psql -U postgres -d auditor_db -v ON_ERROR_STOP=1 -f /tmp/07t.sql
--
-- O próprio teste aplica o db/07 dentro da transação (\i /tmp/07.sql) e o aplica DUAS vezes,
-- para conferir que é idempotente. Depois reaplica o db/05, como o iniciar.ps1 faz a cada
-- subida, e confere que a proteção continua valendo.
-- Esperado: várias linhas "NOTICE: ok ..." e, no fim, a frase de sucesso.
-- ---------------------------------------------------------------------
\set ON_ERROR_STOP on
\echo 'Teste do gatilho de normalização do contrato (transação desfeita no fim)'
BEGIN;
\i /tmp/07.sql
\i /tmp/07.sql

CREATE FUNCTION pg_temp.inserir(p_contrato text) RETURNS TABLE (contrato text, origem text) AS $$
    INSERT INTO decisao_analista
        (contrato_id, analista, decisao, justificativa, situacao_preco, pd, faixa,
         juro_cobrado, juro_justo, juro_justo_min, juro_justo_max, versao_modelo)
    VALUES
        (p_contrato, 'teste', 'manter_preco', 'ok', 'dentro_da_margem', 0.18, 'C',
         0.249, 0.162, 0.141, 0.183, 'teste')
    RETURNING contrato_id, origem;
$$ LANGUAGE sql;

CREATE FUNCTION pg_temp.conferir(p_digitado text, p_contrato text, p_origem text, p_caso text) RETURNS void AS $$
DECLARE c text; o text;
BEGIN
    SELECT contrato, origem INTO c, o FROM pg_temp.inserir(p_digitado);
    IF c IS DISTINCT FROM p_contrato OR o IS DISTINCT FROM p_origem THEN
        RAISE EXCEPTION 'ERRO (%): esperado (%, %), veio (%, %)', p_caso, p_contrato, p_origem, c, o;
    END IF;
    RAISE NOTICE 'ok: %', p_caso;
END;
$$ LANGUAGE plpgsql;

CREATE FUNCTION pg_temp.casos() RETURNS void AS $$
DECLARE v_id text;
BEGIN
    SELECT loan_id INTO v_id FROM emprestimo ORDER BY loan_id LIMIT 1;
    IF v_id IS NULL THEN
        RAISE NOTICE 'pulado: a tabela emprestimo está vazia (carregue o Bondora para testar a carteira)';
        RETURN;
    END IF;
    PERFORM pg_temp.conferir(v_id, v_id, 'carteira', 'ID igual ao do banco continua igual e da carteira');
    PERFORM pg_temp.conferir(upper(v_id), v_id, 'carteira', 'ID em maiúsculas vira o loan_id e fica na carteira');
    PERFORM pg_temp.conferir('  ' || v_id || ' ', v_id, 'carteira', 'ID com espaços vira o loan_id e fica na carteira');
    PERFORM pg_temp.conferir('EXEMPLO-1', 'EXEMPLO-1', 'simulacao', 'simulação mantém o nome digitado');
    PERFORM pg_temp.conferir(' Exemplo-2 ', ' Exemplo-2 ', 'simulacao', 'simulação com espaços e maiúsculas não é alterada');
    IF NOT EXISTS (SELECT 1 FROM vw_decisao_atual WHERE contrato_id = v_id) THEN
        RAISE EXCEPTION 'ERRO: a decisão do contrato digitado em maiúsculas deveria aparecer na vw_decisao_atual';
    END IF;
    RAISE NOTICE 'ok: a decisão aparece na vw_decisao_atual com o loan_id do banco';
END;
$$ LANGUAGE plpgsql;

SELECT pg_temp.casos();

-- o iniciar.ps1 reaplica o db/05 a cada subida: a proteção tem que sobreviver
\echo 'Reaplicando o db/05, como o iniciar.ps1 faz a cada subida...'
\i /tmp/05.sql
SELECT pg_temp.casos();

ROLLBACK;
\echo 'Sucesso: o gatilho de normalização está valendo (e nada ficou gravado).'
