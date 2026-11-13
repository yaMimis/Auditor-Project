"""O gatilho de normalização do contrato (db/07_normaliza_contrato_decisao.sql), sem banco: lê o SQL.

O que importa: normaliza com lower(btrim(...)) só quando o contrato existe, compara pela chave
(loan_id = valor, nunca lower(loan_id)), e não recria o gatilho do db/05, que o iniciar.ps1
reaplica a cada subida.
"""
import re
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "db"
SQL = DB / "07_normaliza_contrato_decisao.sql"
SQL_05 = DB / "05_decisoes_analista.sql"


def _sem_comentarios(texto: str) -> str:
    return re.sub(r"--.*$", "", texto, flags=re.M)


def _sql() -> str:
    return _sem_comentarios(SQL.read_text(encoding="utf-8"))


def test_gatilho_proprio_antes_de_inserir_e_idempotente():
    sql = _sql()
    assert "CREATE OR REPLACE FUNCTION decisao_analista_normaliza_contrato()" in sql
    assert "DROP TRIGGER IF EXISTS trg_decisao_normaliza_contrato ON decisao_analista;" in sql
    assert re.search(r"CREATE TRIGGER trg_decisao_normaliza_contrato\s+BEFORE INSERT ON decisao_analista\s+"
                     r"FOR EACH ROW EXECUTE FUNCTION decisao_analista_normaliza_contrato\(\)", sql)


def test_nao_mexe_no_gatilho_nem_na_funcao_do_db05():
    """O iniciar.ps1 reaplica o db/05: se o 07 trocasse a função ou o gatilho de lá, a proteção sumiria."""
    sql, sql05 = _sql(), _sem_comentarios(SQL_05.read_text(encoding="utf-8"))
    assert "trg_decisao_antes_de_inserir" not in sql
    assert "decisao_analista_antes_de_inserir" not in sql
    assert "trg_decisao_normaliza_contrato" not in sql05      # nomes não podem colidir


def test_normaliza_e_compara_pela_chave():
    sql = _sql()
    assert re.search(r"lower\(btrim\(NEW\.contrato_id\)\)", sql)
    assert re.search(r"WHERE loan_id = normalizado", sql)
    assert not re.search(r"lower\(\s*loan_id\s*\)", sql, flags=re.I), "lower(loan_id) desliga o índice"


def test_so_altera_quando_o_contrato_existe():
    """Dentro do IF EXISTS: troca o contrato_id e marca carteira. Fora dele, nada (simulações intactas)."""
    corpo = _sql().split("BEGIN", 1)[1].split("END;", 1)[0]
    bloco_if = re.search(r"IF EXISTS \(SELECT 1 FROM emprestimo WHERE loan_id = normalizado\) THEN(.*?)END IF;",
                         corpo, flags=re.S)
    assert bloco_if, "o gatilho precisa testar se o contrato existe antes de mudar algo"
    dentro = bloco_if.group(1)
    assert "NEW.contrato_id := normalizado;" in dentro and "NEW.origem := 'carteira';" in dentro
    fora = corpo.replace(bloco_if.group(0), "")
    assert ":=" not in fora, "fora do IF o gatilho não pode alterar a linha"
    assert "ELSE" not in bloco_if.group(0), "não pode haver ELSE: quem marca simulação é o gatilho do db/05"
