"""O SQL de db/ e o código da carga têm que contar a mesma história.

Sem banco: o DDL do Bondora roda em SQLite (só para ler as colunas) e as marcações
dos comentários ([LISTA NEGRA], [SÓ AUDITORIA], [INDISPONÍVEL APÓS 2017]) são comparadas
com as listas exportadas por src/dados/carga_bondora.py, que o teste antivazamento usa.
"""
import re
import sqlite3
from pathlib import Path

from src.dados.carga_bondora import (
    COLUNAS_INDISPONIVEIS_RECENTES,
    COLUNAS_LISTA_NEGRA,
    COLUNAS_SO_AUDITORIA,
    TABELAS,
)

SQL = Path(__file__).resolve().parents[2] / "db" / "01_schema_bondora.sql"
TIPOS = r"(?:TEXT|SMALLINT|INTEGER|DATE|BOOLEAN|CHAR|NUMERIC|DOUBLE)"


def _ddl() -> str:
    return SQL.read_text(encoding="utf-8").replace("CREATE EXTENSION IF NOT EXISTS vector;", "")


def test_colunas_do_sql_sao_as_da_carga():
    db = sqlite3.connect(":memory:")
    db.executescript(_ddl())
    for tabela, colunas in TABELAS.items():
        no_sql = {linha[1] for linha in db.execute(f"PRAGMA table_info({tabela})")}
        na_carga = {c.db for c in colunas}
        assert no_sql == na_carga, (f"{tabela}: só no SQL {sorted(no_sql - na_carga)}; "
                                    f"só na carga {sorted(na_carga - no_sql)}")


def _marcacoes() -> dict[str, set[str]]:
    achadas = {"LISTA NEGRA": set(), "SÓ AUDITORIA": set(), "INDISPONÍVEL APÓS 2017": set()}
    for linha in _ddl().splitlines():
        if linha.strip().startswith("--") or "--" not in linha:
            continue
        m = re.match(rf"\s{{4}}([a-z_0-9]+)\s+{TIPOS}", linha)
        if not m:
            continue
        comentario = linha.split("--", 1)[1]
        for chave in achadas:
            if f"[{chave}]" in comentario:
                achadas[chave].add(m.group(1))
    return achadas


def test_marcacoes_do_sql_batem_com_as_listas_do_codigo():
    achadas = _marcacoes()
    # estado_civil e n_dependentes são só auditoria E indisponíveis depois de 2017
    indisponiveis = set(COLUNAS_INDISPONIVEIS_RECENTES) | {"estado_civil", "n_dependentes"}
    esperado = {"LISTA NEGRA": set(COLUNAS_LISTA_NEGRA), "SÓ AUDITORIA": set(COLUNAS_SO_AUDITORIA),
                "INDISPONÍVEL APÓS 2017": indisponiveis}
    for chave, conjunto in esperado.items():
        assert achadas[chave] == conjunto, (f"[{chave}] SQL e código divergem: só no SQL "
                                            f"{sorted(achadas[chave] - conjunto)}; só no código "
                                            f"{sorted(conjunto - achadas[chave])}")


def test_listas_de_colunas_nao_se_misturam_sem_querer():
    """Uma coluna da lista negra não pode estar também em só auditoria ou indisponível."""
    assert not set(COLUNAS_LISTA_NEGRA) & set(COLUNAS_SO_AUDITORIA)
    assert not set(COLUNAS_LISTA_NEGRA) & set(COLUNAS_INDISPONIVEIS_RECENTES)
    assert not set(COLUNAS_SO_AUDITORIA) & set(COLUNAS_INDISPONIVEIS_RECENTES)
