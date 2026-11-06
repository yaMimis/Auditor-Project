-- ---------------------------------------------------------------------
-- Teste da tabela decisao_analista (db/05_decisoes_analista.sql), no Postgres de verdade.
-- Tudo roda numa transação que é DESFEITA no fim: nada fica gravado.
--
--   docker cp db\05_decisoes_analista.sql auditor_postgres:/tmp/05.sql
--   docker cp db\testes\05_teste_decisoes.sql auditor_postgres:/tmp/05t.sql
--   docker exec auditor_postgres psql -U postgres -d auditor_db -v ON_ERROR_STOP=1 -f /tmp/05t.sql
--
-- Esperado: várias linhas "NOTICE: ok ..." e, no fim, a frase de sucesso. Qualquer
-- "ERRO" ou erro do psql significa que alguma regra do banco não está valendo.
-- Esta pasta (db/testes/) NÃO roda sozinha na criação do banco: o Docker ignora subpastas.
-- ---------------------------------------------------------------------
\set ON_ERROR_STOP on
\echo 'Teste de decisao_analista (transação desfeita no fim)'
BEGIN;

-- auxiliar: insere uma decisão com valores padrão válidos; cada teste muda só um campo
CREATE FUNCTION pg_temp.inserir(
    p_contrato      text DEFAULT 'TESTE-SIMULACAO',
    p_decisao       text DEFAULT 'manter_preco',
    p_justificativa text DEFAULT 'ok',
    p_situacao      text DEFAULT 'dentro_da_margem',
    p_faixa         text DEFAULT 'C',
    p_pd            double precision DEFAULT 0.18,
    p_prever        jsonb DEFAULT NULL
) RETURNS void AS $$
BEGIN
    INSERT INTO decisao_analista
        (contrato_id, analista, decisao, justificativa, situacao_preco, pd, faixa,
         juro_cobrado, juro_justo, juro_justo_min, juro_justo_max, versao_modelo, prever_json)
    VALUES
        (p_contrato, 'teste', p_decisao, p_justificativa, p_situacao, p_pd, p_faixa,
         0.249, 0.162, 0.141, 0.183, 'teste', p_prever);
END;
$$ LANGUAGE plpgsql;

-- auxiliar: o comando TEM que falhar; se passar, o teste acusa ERRO
CREATE FUNCTION pg_temp.deve_falhar(comando text, descricao text) RETURNS void AS $$
BEGIN
    BEGIN
        EXECUTE comando;
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'ok: % foi recusado', descricao;
        RETURN;
    END;
    RAISE EXCEPTION 'ERRO: % deveria ter sido recusado', descricao;
END;
$$ LANGUAGE plpgsql;

-- 1) simulação válida: origem vira 'simulacao' e a data é a do servidor (mesmo que a API mande outra)
INSERT INTO decisao_analista
    (contrato_id, analista, decisao, justificativa, situacao_preco, pd, faixa,
     juro_cobrado, juro_justo, juro_justo_min, juro_justo_max, versao_modelo, registrada_em, origem)
VALUES
    ('TESTE-SIMULACAO', 'teste', 'manter_preco', 'ok', 'dentro_da_margem', 0.18, 'C',
     0.249, 0.162, 0.141, 0.183, 'teste', '2000-01-01', 'carteira');

DO $$
DECLARE o text; r timestamptz;
BEGIN
    SELECT origem, registrada_em INTO o, r FROM decisao_analista WHERE contrato_id = 'TESTE-SIMULACAO';
    IF o <> 'simulacao' THEN
        RAISE EXCEPTION 'ERRO: origem deveria ser simulacao, veio %', o;
    END IF;
    IF r < now() - interval '1 minute' THEN
        RAISE EXCEPTION 'ERRO: registrada_em deveria ser a hora do servidor, veio %', r;
    END IF;
    RAISE NOTICE 'ok: simulação gravada com origem e data do servidor';
END $$;

-- 2) contrato da carteira: origem 'carteira' e aparece na vw_decisao_atual (a simulação, não)
DO $$
DECLARE v_id text; o text;
BEGIN
    SELECT loan_id INTO v_id FROM emprestimo LIMIT 1;
    IF v_id IS NULL THEN
        RAISE NOTICE 'pulado: a tabela emprestimo está vazia (carregue o Bondora para testar a carteira)';
        RETURN;
    END IF;
    PERFORM pg_temp.inserir(p_contrato => v_id, p_decisao => 'manter_preco');
    PERFORM pg_temp.inserir(p_contrato => v_id, p_decisao => 'revisar_preco');
    SELECT origem INTO o FROM decisao_analista WHERE contrato_id = v_id LIMIT 1;
    IF o <> 'carteira' THEN
        RAISE EXCEPTION 'ERRO: origem deveria ser carteira, veio %', o;
    END IF;
    IF (SELECT count(*) FROM vw_decisao_atual WHERE contrato_id = v_id) <> 1 THEN
        RAISE EXCEPTION 'ERRO: vw_decisao_atual deveria ter 1 linha para o contrato';
    END IF;
    IF (SELECT decisao FROM vw_decisao_atual WHERE contrato_id = v_id) <> 'revisar_preco' THEN
        RAISE EXCEPTION 'ERRO: vw_decisao_atual deveria trazer a decisão mais recente';
    END IF;
    IF EXISTS (SELECT 1 FROM vw_decisao_atual WHERE contrato_id = 'TESTE-SIMULACAO') THEN
        RAISE EXCEPTION 'ERRO: simulação não deveria aparecer na vw_decisao_atual';
    END IF;
    RAISE NOTICE 'ok: carteira com origem certa; a view traz só a decisão mais recente e ignora simulações';
END $$;

-- 3) o mesmo clique (mesmo requisicao_id) não grava duas vezes
DO $$
DECLARE n int;
BEGIN
    FOR i IN 1..2 LOOP
        INSERT INTO decisao_analista
            (requisicao_id, contrato_id, analista, decisao, justificativa, situacao_preco, pd, faixa,
             juro_cobrado, juro_justo, juro_justo_min, juro_justo_max, versao_modelo)
        VALUES
            ('00000000-0000-4000-8000-000000000001', 'TESTE-DEDUPE', 'teste', 'manter_preco', 'ok',
             'dentro_da_margem', 0.18, 'C', 0.249, 0.162, 0.141, 0.183, 'teste')
        ON CONFLICT (requisicao_id) DO NOTHING;
    END LOOP;
    SELECT count(*) INTO n FROM decisao_analista WHERE contrato_id = 'TESTE-DEDUPE';
    IF n <> 1 THEN
        RAISE EXCEPTION 'ERRO: o mesmo requisicao_id gravou % linhas', n;
    END IF;
    RAISE NOTICE 'ok: requisicao_id repetido não duplica';
END $$;

-- 4) o que o banco tem que recusar
SELECT pg_temp.deve_falhar($q$SELECT pg_temp.inserir(p_decisao => 'foo')$q$,                      'decisão fora do domínio');
SELECT pg_temp.deve_falhar($q$SELECT pg_temp.inserir(p_justificativa => '   ')$q$,                'justificativa vazia');
SELECT pg_temp.deve_falhar($q$SELECT pg_temp.inserir(p_situacao => 'barato')$q$,                  'situacao_preco fora do domínio');
SELECT pg_temp.deve_falhar($q$SELECT pg_temp.inserir(p_faixa => 'F')$q$,                          'faixa fora de A a E');
SELECT pg_temp.deve_falhar($q$SELECT pg_temp.inserir(p_pd => 1.5)$q$,                             'pd maior que 1');
SELECT pg_temp.deve_falhar($q$SELECT pg_temp.inserir(p_prever => '{"gender": 1}'::jsonb)$q$,      'JSON com gender');
SELECT pg_temp.deve_falhar($q$SELECT pg_temp.inserir(p_prever => '{"idade": 30}'::jsonb)$q$,      'JSON com idade');
SELECT pg_temp.deve_falhar($q$UPDATE decisao_analista SET justificativa = 'alterada'$q$,          'UPDATE (só inclusão)');
SELECT pg_temp.deve_falhar($q$DELETE FROM decisao_analista$q$,                                    'DELETE (só inclusão)');
SELECT pg_temp.deve_falhar($q$TRUNCATE decisao_analista$q$,                                       'TRUNCATE (só inclusão)');

ROLLBACK;
\echo 'Fim. Se nenhuma linha acima disse ERRO, todas as regras da decisao_analista estao valendo. Nada foi gravado.'
