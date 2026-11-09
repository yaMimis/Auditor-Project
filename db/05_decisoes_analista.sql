-- ---------------------------------------------------------------------
-- 05_decisoes_analista.sql
-- Registro das decisões do analista: "Manter preço", "Revisar preço" e
-- "Encaminhar ao compliance". É a trilha de auditoria do projeto: cada decisão
-- fica guardada com o parecer, a justificativa e os números do momento, e quem
-- decide é sempre o analista (LGPD, art. 20).
--
-- Roda DEPOIS do 01 (o gatilho de inserção consulta a tabela emprestimo).
-- Os arquivos de db/ só rodam sozinhos na PRIMEIRA criação do banco. Quem já tem o
-- banco montado aplica este arquivo uma vez:
--   docker cp db\05_decisoes_analista.sql auditor_postgres:/tmp/05.sql
--   docker exec auditor_postgres psql -U postgres -d auditor_db -v ON_ERROR_STOP=1 -f /tmp/05.sql
-- Pode rodar de novo sem problema (CREATE ... IF NOT EXISTS / OR REPLACE).
--
-- REGRAS DESTA TABELA
--   * Só inclusão: UPDATE, DELETE e TRUNCATE são bloqueados por gatilho. Para
--     corrigir uma decisão, registre OUTRA: a mais recente vale (vw_decisao_atual).
--   * Quem registra não escolhe a data nem a origem: registrada_em é sempre a hora
--     do servidor, e origem é 'carteira' se o contrato_id existe em emprestimo
--     (loan_id) ou 'simulacao' (casos de exemplo, como EXEMPLO-1).
--   * Gênero e idade NÃO entram: não há coluna para eles, e o banco recusa um JSON
--     (prever_json ou parecer_json) que tenha as chaves genero, idade, gender ou age
--     no primeiro nível. Quem grava o JSON deve mandar só a RESPOSTA do prever() e o
--     parecer, nunca a solicitação (que carrega gênero e idade).
--   * Taxas em FRAÇÃO ao ano, como a API (0,249 = 24,9% ao ano, taxa nominal).
--   * Valores dos domínios iguais aos de src/api/schemas.py (há teste que confere).
--   * A justificativa é obrigatória. Evite dado pessoal no texto livre dela.
--   * Revisão manual (dados fora da faixa do treino): o prever() devolve situacao_preco = 'revisao_manual'
--     com pd, faixa e os juros justos nulos, e o analista ainda decide. Fora da revisão manual esses
--     números são obrigatórios (mesma regra do genai/src/checagem.py).
--
-- COMO A API GRAVA (a API não manda registrada_em nem origem):
--   INSERT INTO decisao_analista
--       (requisicao_id, contrato_id, analista, decisao, justificativa, taxa_proposta,
--        recomendacao_sistema, situacao_preco, pd, faixa, juro_cobrado, juro_justo,
--        juro_justo_min, juro_justo_max, versao_modelo, versao_parecer, origem_parecer,
--        prever_json, parecer_json)
--   VALUES (...)
--   ON CONFLICT (requisicao_id) DO NOTHING          -- o mesmo clique não grava duas vezes
--   RETURNING decisao_id, registrada_em, origem;
--
-- COMO O PAINEL LÊ
--   Registro de decisões:  SELECT * FROM decisao_analista ORDER BY registrada_em DESC;
--   De um contrato:        SELECT * FROM decisao_analista WHERE contrato_id = %s
--                          ORDER BY registrada_em DESC, decisao_id DESC;
--   Fila da carteira ("já decidido"):
--                          ... LEFT JOIN vw_decisao_atual d ON d.contrato_id = <loan_id da fila>
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS decisao_analista (
    decisao_id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    registrada_em        TIMESTAMPTZ NOT NULL DEFAULT now(),     -- sempre a hora do servidor (gatilho)
    requisicao_id        UUID UNIQUE,                            -- opcional: evita gravar o mesmo clique duas vezes
    contrato_id          TEXT NOT NULL,                          -- contrato_id da API; na carteira é o loan_id
    origem               TEXT NOT NULL DEFAULT 'simulacao'       -- definida pelo gatilho
                         CHECK (origem IN ('carteira', 'simulacao')),
    analista             TEXT NOT NULL CHECK (length(btrim(analista)) > 0),
    decisao              TEXT NOT NULL
                         CHECK (decisao IN ('manter_preco', 'revisar_preco', 'encaminhar_compliance')),
    justificativa        TEXT NOT NULL CHECK (length(btrim(justificativa)) > 0),
    taxa_proposta        DOUBLE PRECISION                        -- nova taxa, em fração ao ano (nominal)
                         CHECK (taxa_proposta > 0 AND taxa_proposta <= 10),
    recomendacao_sistema TEXT                                    -- a do parecer (vazia se não houve parecer)
                         CHECK (recomendacao_sistema IN ('manter_preco', 'revisar_preco', 'encaminhar_compliance', 'revisao_manual')),
    situacao_preco       TEXT NOT NULL
                         CHECK (situacao_preco IN ('acima_do_justo', 'abaixo_do_justo', 'dentro_da_margem', 'revisao_manual')),
    -- números do momento (resposta do prever()), em fração; só ficam vazios em revisao_manual
    pd                   DOUBLE PRECISION CHECK (pd BETWEEN 0 AND 1),
    faixa                TEXT CHECK (faixa IN ('A', 'B', 'C', 'D', 'E')),
    juro_cobrado         DOUBLE PRECISION NOT NULL CHECK (juro_cobrado BETWEEN 0 AND 10),
    juro_justo           DOUBLE PRECISION CHECK (juro_justo BETWEEN 0 AND 10),
    juro_justo_min       DOUBLE PRECISION CHECK (juro_justo_min BETWEEN 0 AND 10),
    juro_justo_max       DOUBLE PRECISION CHECK (juro_justo_max BETWEEN 0 AND 10),
    -- versões, para saber qual modelo e qual parecer estavam na tela
    versao_modelo        TEXT NOT NULL CHECK (length(btrim(versao_modelo)) > 0),
    versao_parecer       TEXT,                                   -- versao_prompt do parecer
    origem_parecer       TEXT CHECK (origem_parecer IN ('llm', 'template')),
    -- cópia do que o analista viu (sem gênero nem idade)
    prever_json          JSONB CHECK (prever_json IS NULL OR NOT (prever_json ?| ARRAY['genero', 'idade', 'gender', 'age'])),
    parecer_json         JSONB CHECK (parecer_json IS NULL OR NOT (parecer_json ?| ARRAY['genero', 'idade', 'gender', 'age'])),
    -- mesma regra do genai/src/checagem.py: fora da revisão manual, os números são obrigatórios
    CONSTRAINT decisao_analista_numeros_obrigatorios CHECK (
        situacao_preco = 'revisao_manual'
        OR (pd IS NOT NULL AND faixa IS NOT NULL AND juro_justo IS NOT NULL
            AND juro_justo_min IS NOT NULL AND juro_justo_max IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS ix_decisao_analista_contrato
    ON decisao_analista (contrato_id, registrada_em DESC);
CREATE INDEX IF NOT EXISTS ix_decisao_analista_data
    ON decisao_analista (registrada_em DESC);

-- ---------------------------------------------------------------------
-- Atualização (revisão manual). Em bancos que JÁ têm a tabela, o CREATE acima não muda nada;
-- estes comandos põem a tabela no mesmo formato e podem rodar quantas vezes quiser.
-- ---------------------------------------------------------------------
ALTER TABLE decisao_analista DROP CONSTRAINT IF EXISTS decisao_analista_situacao_preco_check;
ALTER TABLE decisao_analista ADD CONSTRAINT decisao_analista_situacao_preco_check
    CHECK (situacao_preco IN ('acima_do_justo', 'abaixo_do_justo', 'dentro_da_margem', 'revisao_manual'));
ALTER TABLE decisao_analista ALTER COLUMN pd DROP NOT NULL;
ALTER TABLE decisao_analista ALTER COLUMN faixa DROP NOT NULL;
ALTER TABLE decisao_analista ALTER COLUMN juro_justo DROP NOT NULL;
ALTER TABLE decisao_analista ALTER COLUMN juro_justo_min DROP NOT NULL;
ALTER TABLE decisao_analista ALTER COLUMN juro_justo_max DROP NOT NULL;
ALTER TABLE decisao_analista DROP CONSTRAINT IF EXISTS decisao_analista_numeros_obrigatorios;
ALTER TABLE decisao_analista ADD CONSTRAINT decisao_analista_numeros_obrigatorios CHECK (
    situacao_preco = 'revisao_manual'
    OR (pd IS NOT NULL AND faixa IS NOT NULL AND juro_justo IS NOT NULL
        AND juro_justo_min IS NOT NULL AND juro_justo_max IS NOT NULL));

-- ---------------------------------------------------------------------
-- Gatilho de inserção: data do servidor e origem do contrato
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION decisao_analista_antes_de_inserir() RETURNS trigger AS $$
BEGIN
    NEW.registrada_em := now();
    IF EXISTS (SELECT 1 FROM emprestimo WHERE loan_id = NEW.contrato_id) THEN
        NEW.origem := 'carteira';
    ELSE
        NEW.origem := 'simulacao';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_decisao_antes_de_inserir ON decisao_analista;
CREATE TRIGGER trg_decisao_antes_de_inserir
    BEFORE INSERT ON decisao_analista
    FOR EACH ROW EXECUTE FUNCTION decisao_analista_antes_de_inserir();

-- ---------------------------------------------------------------------
-- Gatilho de só inclusão: a trilha de auditoria não se altera nem se apaga
-- (para zerar o banco de desenvolvimento: DROP TABLE decisao_analista CASCADE e rode este arquivo de novo)
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION decisao_analista_somente_inclusao() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'decisao_analista é só de inclusão: % não é permitido (para corrigir, registre uma nova decisão)', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_decisao_somente_inclusao ON decisao_analista;
CREATE TRIGGER trg_decisao_somente_inclusao
    BEFORE UPDATE OR DELETE ON decisao_analista
    FOR EACH ROW EXECUTE FUNCTION decisao_analista_somente_inclusao();

DROP TRIGGER IF EXISTS trg_decisao_sem_truncate ON decisao_analista;
CREATE TRIGGER trg_decisao_sem_truncate
    BEFORE TRUNCATE ON decisao_analista
    FOR EACH STATEMENT EXECUTE FUNCTION decisao_analista_somente_inclusao();

-- ---------------------------------------------------------------------
-- Decisão atual de cada contrato da carteira (a mais recente). A fila da
-- carteira usa esta view para marcar "já decidido". Simulações ficam de fora.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_decisao_atual AS
SELECT DISTINCT ON (contrato_id)
       decisao_id,
       contrato_id,
       registrada_em,
       analista,
       decisao,
       justificativa,
       taxa_proposta,
       recomendacao_sistema,
       situacao_preco
FROM decisao_analista
WHERE origem = 'carteira'
ORDER BY contrato_id, registrada_em DESC, decisao_id DESC;
