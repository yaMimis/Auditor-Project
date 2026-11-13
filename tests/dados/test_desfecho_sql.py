"""O SQL da view de desfecho (db/06_view_desfecho_contrato.sql) tem que contar a mesma história que
o código e que a base de modelagem (db/03): LEFT JOIN na vw_retorno_realizado, os três motivos
combinados e nada de gênero, idade, estado civil ou dependentes. Sem banco: lê o texto do SQL.
"""
import re
from pathlib import Path

from src.dados import validacao as v

DB = Path(__file__).resolve().parents[2] / "db"
SQL = DB / "06_view_desfecho_contrato.sql"
SQL_MODELAGEM = DB / "03_view_modelagem.sql"


def _sem_comentarios(texto: str) -> str:
    return re.sub(r"--.*$", "", texto, flags=re.M)


def _sql() -> str:
    return _sem_comentarios(SQL.read_text(encoding="utf-8"))


def test_view_existe_e_e_idempotente():
    assert "CREATE OR REPLACE VIEW vw_desfecho_contrato AS" in _sql()


def test_usa_left_join_na_vw_retorno_realizado():
    """INNER JOIN deixaria só os 29.916 da base de modelagem; a view precisa de todos os contratos."""
    sql = _sql()
    assert re.search(r"LEFT JOIN\s+vw_retorno_realizado\b", sql)
    assert not re.search(r"(?<!LEFT )JOIN\s+vw_retorno_realizado\b", sql)
    assert re.search(r"FROM\s+emprestimo\b", sql)


def test_nao_cita_dados_sensiveis():
    sql = _sql().lower()
    for nome in ("genero", "idade", "estado_civil", "n_dependentes"):
        assert nome not in sql, f"{nome!r} não pode aparecer na view (a API lê esta view)"


def test_motivos_sao_os_combinados():
    motivos = re.findall(r"THEN\s+'([^']*)'", _sql())
    assert motivos == v.MOTIVOS_SEM_DESFECHO, f"SQL {motivos} x validacao.py {v.MOTIVOS_SEM_DESFECHO}"


def test_motivos_espelham_os_filtros_da_base_de_modelagem():
    """Os cortes do 06 têm que ser os mesmos do 03: fim de 2016, Eslováquia e 'Repaid' ou default."""
    sql, modelagem = _sql(), _sem_comentarios(SQL_MODELAGEM.read_text(encoding="utf-8"))
    assert "DATE '2016-12-31'" in modelagem and "e.data_emprestimo > DATE '2016-12-31'" in sql
    assert "c.pais <> 'SK'" in modelagem and "c.pais = 'SK'" in sql
    assert "e.status = 'Repaid' OR e.data_default IS NOT NULL" in modelagem
    assert re.search(r"e\.status IS DISTINCT FROM 'Repaid'\s+AND e\.data_default IS NULL", sql)


def test_colunas_do_sql_sao_as_do_esquema_de_validacao():
    corpo = _sql().split("AS\nSELECT", 1)[1].split("FROM emprestimo", 1)[0]
    colunas = set()
    for item in re.split(r",\s*\n", corpo):
        item = item.strip()
        apelido = re.search(r"\bAS\s+(\w+)\s*$", item)
        colunas.add(apelido.group(1) if apelido else item.split(".")[-1])
    esquema = set(v._regras_erro()["vw_desfecho_contrato"])
    assert colunas == esquema, f"só no SQL {sorted(colunas - esquema)}; só na validação {sorted(esquema - colunas)}"
