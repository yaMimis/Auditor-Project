-- ---------------------------------------------------------------------
-- 07_normaliza_contrato_decisao.sql
-- Proteção do registro de decisões contra ID digitado em maiúsculas ou com espaços.
--
-- O problema: o gatilho do db/05 marca origem = 'carteira' só se o contrato_id for
-- IGUAL a um loan_id (que o banco guarda em minúsculas), e a fila da carteira junta
-- pela igualdade também. Uma decisão gravada com '0010881B-…' ou ' 0010881b-… ' viraria
-- 'simulacao' e sumiria da fila. Como a decisao_analista é só de inclusão, essa linha
-- nunca mais poderia ser corrigida.
--
-- Combinado com Samuel e Yasmin: a API usa, depois da busca, o loan_id que voltou do
-- banco como contrato_id em todo o fluxo (prever, parecer, taxa do BC e decisão). Este
-- gatilho é a segunda barreira, no banco:
--   * se lower(btrim(contrato_id)) é um loan_id, grava o contrato_id normalizado e
--     origem = 'carteira';
--   * se não é (simulações como 'EXEMPLO-1'), não mexe em nada: a simulação mantém o
--     nome digitado e continua 'simulacao'.
--
-- Por que um gatilho NOVO, e não trocar a função do db/05: o iniciar.ps1 reaplica o
-- db/05 a cada subida e recriaria o gatilho antigo. Este tem nome e função próprios,
-- que o db/05 não toca. Os dois são BEFORE INSERT e o resultado é o mesmo em qualquer
-- ordem (o Postgres roda em ordem alfabética: primeiro o do 05, depois este).
--
-- A comparação é loan_id = <valor normalizado>, e nunca lower(loan_id) = ...: assim a
-- consulta usa a chave primária (índice) de emprestimo.
--
-- Roda DEPOIS do 05. Idempotente (CREATE OR REPLACE / DROP TRIGGER IF EXISTS).
-- Aplicar em banco existente (PowerShell, na raiz):
--   docker cp db\07_normaliza_contrato_decisao.sql auditor_postgres:/tmp/07.sql
--   docker exec auditor_postgres psql -U postgres -d auditor_db -v ON_ERROR_STOP=1 -f /tmp/07.sql
-- Teste (transação desfeita no fim): db/testes/07_teste_normaliza_contrato.sql
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION decisao_analista_normaliza_contrato() RETURNS trigger AS $$
DECLARE
    normalizado text := lower(btrim(NEW.contrato_id));
BEGIN
    IF EXISTS (SELECT 1 FROM emprestimo WHERE loan_id = normalizado) THEN
        NEW.contrato_id := normalizado;
        NEW.origem := 'carteira';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_decisao_normaliza_contrato ON decisao_analista;
CREATE TRIGGER trg_decisao_normaliza_contrato
    BEFORE INSERT ON decisao_analista
    FOR EACH ROW EXECUTE FUNCTION decisao_analista_normaliza_contrato();
