"""Rotas do lote da carteira (Home e lista de contratos), com um lote sintético."""
import pandas as pd
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("xgboost")
from fastapi.testclient import TestClient  # noqa: E402

import src.api.main as api  # noqa: E402
from src.api import portfolio  # noqa: E402

ROWS = [
    {"contrato_id": "A1", "ano": 2016, "pais": "EE", "faixa": "A", "pd": 0.05, "juro_cobrado": 0.30,
     "juro_justo": 0.20, "juro_justo_min": 0.18, "juro_justo_max": 0.22, "situacao_preco": "acima_do_justo"},
    {"contrato_id": "B1", "ano": 2017, "pais": "FI", "faixa": "B", "pd": 0.10, "juro_cobrado": 0.20,
     "juro_justo": 0.20, "juro_justo_min": 0.18, "juro_justo_max": 0.22, "situacao_preco": "dentro_da_margem"},
    {"contrato_id": "M1", "ano": 2018, "pais": "ES", "faixa": None, "pd": None, "juro_cobrado": 0.25,
     "juro_justo": None, "juro_justo_min": None, "juro_justo_max": None, "situacao_preco": "revisao_manual"},
]


@pytest.fixture
def client(tmp_path, monkeypatch):
    pd.DataFrame(ROWS).to_csv(tmp_path / portfolio.PORTFOLIO_FILE, index=False)
    monkeypatch.setattr(portfolio, "PORTFOLIO_DIR", tmp_path)
    return TestClient(api.app)


def test_overview(client):
    out = client.get("/portfolio/overview").json()
    assert out["anos"] == [2016, 2018] and out["resumo"]["auditados"] >= 2 and out["equidade"] is None
    assert client.get("/portfolio/overview", params={"country": "EE"}).status_code == 200


def test_list_is_sorted_and_filtered(client):
    out = client.get("/contracts").json()
    assert out["total"] == 3 and out["itens"][0]["contrato_id"] == "A1" and out["itens"][-1]["contrato_id"] == "M1"
    only = client.get("/contracts", params={"situation": "dentro_da_margem"}).json()
    assert only["total"] == 1 and only["itens"][0]["contrato_id"] == "B1"
    assert client.get("/contracts", params={"situation": "inventada"}).status_code == 422


def test_fixed_routes_are_not_taken_as_ids(client):
    assert client.get("/contracts/ids").json() == ["A1", "B1", "M1"]
    csv = client.get("/contracts/export", params={"situation": "acima_do_justo"})
    assert csv.status_code == 200 and csv.content.startswith(b"\xef\xbb\xbf") and b"A1" in csv.content


def test_one_row_of_the_batch(client):
    assert client.get("/contracts/a1").json()["juro_cobrado"] == 0.30
    assert client.get("/contracts/X9").status_code == 404


def test_503_without_the_batch(tmp_path, monkeypatch):
    monkeypatch.setattr(portfolio, "PORTFOLIO_DIR", tmp_path)
    c = TestClient(api.app)
    for route in ("/portfolio/overview", "/contracts", "/contracts/ids", "/contracts/A1"):
        assert c.get(route).status_code == 503
