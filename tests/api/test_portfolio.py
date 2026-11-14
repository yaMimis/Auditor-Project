"""Lote da carteira servido pela API (src/api/portfolio.py), com dados sintéticos."""
import json

import pandas as pd
import pytest

from src.api import portfolio


def _row(cid, faixa, situation, charged, ano=2018, pais="EE", **extra):
    return {"contrato_id": cid, "ano": ano, "pais": pais, "pd": 0.3, "faixa": faixa,
            "juro_cobrado": charged, "juro_justo": 0.20, "juro_justo_min": 0.18,
            "juro_justo_max": 0.22, "situacao_preco": situation, **extra}


@pytest.fixture
def folder(tmp_path):
    df = pd.DataFrame([
        _row("A1", "A", "acima_do_justo", 0.30, excesso_eur=100.0, rentabilidade_realizada=0.10),
        _row("A2", "A", "dentro_da_margem", 0.20, excesso_eur=0.0, rentabilidade_realizada=0.05),
        _row("B1", "B", "abaixo_do_justo", 0.10, perda_nao_coberta_eur=50.0, rentabilidade_realizada=-0.02),
        _row("B2", "B", "acima_do_justo", 0.25, ano=2016, pais="ES", excesso_eur=30.0),
        _row("R1", "B", "acima_do_justo", 0.40, fora_da_auditoria=True),  # reestruturado
        {**_row("M1", None, "revisao_manual", 0.20), "pd": None, "juro_justo": None,
         "juro_justo_min": None, "juro_justo_max": None},
    ])
    df["fora_da_auditoria"] = df["fora_da_auditoria"].fillna(False).astype(bool)
    df.to_csv(tmp_path / portfolio.PORTFOLIO_FILE, index=False)
    (tmp_path / portfolio.FAIRNESS_FILE).write_text(json.dumps([
        {"atributo": "Gênero", "comparacao": "f × m", "diferenca_pp": 0.3, "ic95_min": -0.1, "ic95_max": 0.7},
        {"atributo": "País", "comparacao": "ES × EE", "diferenca_pp": 5.0, "ic95_min": 4.0, "ic95_max": 6.0},
    ]), encoding="utf-8")
    return tmp_path


def test_missing_files_return_none(tmp_path):
    assert portfolio.load_portfolio(tmp_path) is None
    assert portfolio.load_fairness(tmp_path) is None


def test_restructured_excluded_and_country_not_a_group(folder):
    df = portfolio.load_portfolio(folder)
    assert "R1" not in set(df["contrato_id"])
    assert [e["atributo"] for e in portfolio.load_fairness(folder)] == ["Gênero"]


def test_missing_required_column(tmp_path):
    pd.DataFrame([{"contrato_id": "X"}]).to_csv(tmp_path / portfolio.PORTFOLIO_FILE, index=False)
    with pytest.raises(ValueError, match="sem as colunas"):
        portfolio.load_portfolio(tmp_path)


def test_summary_and_filters(folder):
    df = portfolio.load_portfolio(folder)
    r = portfolio.summarize(df)
    assert r["auditados"] == 4 and r["revisao_manual"] == 1
    assert r["acima"] == 0.5 and r["abaixo"] == 0.25
    assert r["pago_a_mais_eur"] == 130.0 and r["perda_nao_coberta_eur"] == 50.0
    assert portfolio.summarize(portfolio.filter_portfolio(df, pais="ES"))["auditados"] == 1
    assert portfolio.summarize(portfolio.filter_portfolio(df, years=(2017, 2021)))["auditados"] == 3


def test_by_band_sums_to_one(folder):
    for row in portfolio.by_band(portfolio.load_portfolio(folder)):
        assert sum(row[s] for s in portfolio.PRICE_SITUATIONS) == pytest.approx(1.0)


def test_queue_sorted_by_distance(folder):
    queue = portfolio.list_contracts(portfolio.load_portfolio(folder), ["acima_do_justo", "abaixo_do_justo"])
    assert list(queue["distancia_pp"]) == [8.0, 8.0, 3.0]
    assert set(queue["contrato_id"][:2]) == {"A1", "B1"} and queue["contrato_id"].iloc[2] == "B2"


def test_backtest_by_band(folder):
    bt = portfolio.backtest(portfolio.load_portfolio(folder))
    assert bt.loc["A", "acima_do_justo"] == pytest.approx(0.10)
    assert bt.loc["B", "abaixo_do_justo"] == pytest.approx(-0.02)

def test_export_only_useful_columns(folder):
    content = portfolio.export_contracts(
        portfolio.list_contracts(portfolio.load_portfolio(folder), ["acima_do_justo", "abaixo_do_justo"]))
    assert content.startswith(b"\xef\xbb\xbf")  # BOM: o Excel abre os acentos certo
    rows = content.decode("utf-8-sig").splitlines()
    header = rows[0].split(",")
    assert header[:4] == ["contrato_id", "ano", "pais", "faixa"] and "distancia_pp" in header
    assert "rentabilidade_realizada" not in header
    assert len(rows) == 1 + 3  # A1, B1, B2 (fora da margem)


def test_list_contracts_by_situation(folder):
    df = portfolio.load_portfolio(folder)
    inside = portfolio.list_contracts(df, ["dentro_da_margem"])
    assert list(inside["contrato_id"]) == ["A2"] and inside["distancia_pp"].iloc[0] == 0.0
    every = portfolio.list_contracts(df, None)
    assert every["contrato_id"].iloc[-1] == "M1"  # revisão manual (sem distância) vai para o fim
    assert portfolio.list_contracts(df, ["situacao_inexistente"]).empty


def test_find_contract_by_exact_id(folder):
    df = portfolio.load_portfolio(folder)
    assert portfolio.find_contract(df, " a1 ")["juro_cobrado"] == 0.30
    assert portfolio.find_contract(df, "A") is None and portfolio.find_contract(df, "") is None


def test_cached_portfolio_rereads_when_the_file_changes(folder):
    first = portfolio.cached_portfolio(folder)
    assert first is portfolio.cached_portfolio(folder)  # mesma versão do arquivo: não relê
    assert list(first["distancia_pp"])[:2] == [8.0, 8.0]  # já vem ordenado pela distância
    import os
    path_ = folder / portfolio.PORTFOLIO_FILE
    os.utime(path_, (path_.stat().st_atime, path_.stat().st_mtime + 10))
    assert portfolio.cached_portfolio(folder) is not first


def test_overview_has_everything_the_home_shows(folder):
    df = portfolio.load_portfolio(folder)
    out = portfolio.overview(df, [{"atributo": "Idade", "diferenca_pp": 5.45}], years=(2016, 2021))
    assert out["anos"][0] <= out["anos"][1] and out["faixas"] == portfolio.BANDS
    assert out["resumo"]["auditados"] >= 1 and out["por_faixa"] and out["equidade"][0]["atributo"] == "Idade"
    assert out["backtest"][0]["faixa"] == "A"
    import json
    json.dumps(out)  # pronto para a resposta da API
