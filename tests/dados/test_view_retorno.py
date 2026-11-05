"""A definição da view vw_retorno_realizado (db/04_view_retorno_realizado.sql), sem banco de verdade.

Roda o SQL num SQLite em memória, com contratos inventados e contas feitas à mão. O que
mais importa aqui: as recuperações JÁ estão dentro dos pagamentos e não podem ser somadas de novo.
"""
import sqlite3
from pathlib import Path

SQL = Path(__file__).resolve().parents[2] / "db" / "04_view_retorno_realizado.sql"


def _banco():
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE emprestimo (loan_id TEXT, valor_concedido REAL, prazo_meses INTEGER, juro_aa REAL,
            principal_pago REAL, juros_multas_pagos REAL, recuperacao_principal REAL, recuperacao_juros REAL,
            data_emprestimo TEXT, data_ultimo_pagamento TEXT);
        CREATE TABLE vw_base_modelagem (loan_id TEXT, ano INTEGER, pais TEXT, conjunto TEXT,
            reestruturado INTEGER, inadimplente INTEGER);
    """)
    contratos = [
        # id,  valor, prazo, juro, principal, juros, rec.princ., rec.juros
        ("A", 1000, 12, 30, 1000, 200, None, None),     # pago em dia
        ("B", 1000, 12, 30, 400, 50, 150, 10),          # default com recuperação (já dentro de 400 e 50)
        ("C", 500, 12, 30, 0, 0, 0, 0),                 # perda total
        ("D", 300, 12, 30, None, None, None, None),     # pagamentos vazios
        ("E", 260, 12, 30, 260, 8, None, None),         # valores inteiros (divisão inteira não pode truncar)
    ]
    for c in contratos:
        db.execute("INSERT INTO emprestimo VALUES (?,?,?,?,?,?,?,?,'2014-03-01','2015-03-01')", c)
        db.execute("INSERT INTO vw_base_modelagem VALUES (?,2014,'EE','treino',0,?)", (c[0], 1 if c[0] in "BCD" else 0))
    db.executescript(SQL.read_text(encoding="utf-8").replace("CREATE OR REPLACE VIEW", "CREATE VIEW"))
    db.row_factory = sqlite3.Row
    return {linha["loan_id"]: dict(linha) for linha in db.execute("SELECT * FROM vw_retorno_realizado")}


def _perto(a, b, tol=1e-6):
    return abs(a - b) <= tol


def test_contrato_pago_em_dia():
    a = _banco()["A"]
    assert a["recebido_total"] == 1200 and a["resultado_eur"] == 200
    assert _perto(a["retorno_realizado"], 0.2) and a["principal_perdido"] == 0


def test_recuperacao_nao_e_somada_duas_vezes():
    b = _banco()["B"]
    assert b["recebido_total"] == 450                  # 400 + 50, e NÃO 400 + 50 + 150 + 10
    assert b["resultado_eur"] == -550
    assert _perto(b["retorno_realizado"], -0.55)
    assert b["principal_perdido"] == 600
    assert b["recuperado_eur"] == 160                  # só informativo


def test_perda_total_e_pagamentos_vazios():
    v = _banco()
    assert _perto(v["C"]["retorno_realizado"], -1.0) and v["C"]["principal_perdido"] == 500
    assert v["D"]["recebido_total"] == 0 and _perto(v["D"]["retorno_realizado"], -1.0)
    assert v["D"]["principal_perdido"] == 300


def test_divisao_nao_trunca_valores_inteiros():
    e = _banco()["E"]
    assert _perto(e["retorno_realizado"], 8 / 260)     # 0,0308, e não 0


def test_a_view_cobre_os_mesmos_contratos_da_base_de_modelagem():
    assert set(_banco()) == {"A", "B", "C", "D", "E"}


def test_retorno_nunca_passa_de_menos_100_por_cento():
    assert all(c["retorno_realizado"] >= -1.0 for c in _banco().values())
