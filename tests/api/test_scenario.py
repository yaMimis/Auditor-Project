"""POST /contracts/{id}/scenario: Laboratório (o mesmo contrato com campos trocados → prever() de novo).

Banco e modelo são falsos aqui: o prever() falso muda a PD com o prazo e com a renda, e não com o
juro cobrado (como o real: o juro não é variável do modelo)."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("xgboost")
from fastapi.testclient import TestClient  # noqa: E402

import src.api.main as api  # noqa: E402
from src.api import scenario  # noqa: E402
from tests.api.test_contract_analysis import PACKAGE, ROW  # noqa: E402

LIMITS = {"valor_concedido": (500.0, 10000.0), "prazo_meses": (6.0, 60.0), "renda_total": (300.0, 8000.0)}
CALLS = []


def _prediction(row, package=None):
    """PD sobe com o prazo e desce com a renda; o juro cobrado só muda a situação."""
    CALLS.append(dict(row))
    pd_ = round(0.30 + (row["prazo_meses"] - 60) * 0.004 - (row["renda_total"] - 2100) * 0.00005, 4)
    fair = round(0.10 + pd_ * 0.40, 4)
    charged = round(row["juro_aa"] / 100, 4)
    situation = ("acima_do_justo" if charged > fair + 0.02 else
                 "abaixo_do_justo" if charged < fair - 0.02 else "dentro_da_margem")
    return {"contrato_id": row["loan_id"], "versao_modelo": "xgboost_teste", "juro_cobrado": charged,
            "pd": pd_, "pd_ic95": None, "faixa": "A", "juro_justo": fair, "juro_justo_min": round(fair - 0.02, 4),
            "juro_justo_max": round(fair + 0.02, 4), "diferenca_pp": None, "situacao_preco": situation,
            "juro_pares_mediana": None, "alerta_dados": False, "motivos": []}


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    CALLS.clear()
    monkeypatch.setattr(api.database, "load_contract", lambda cid: dict(ROW) if cid.lower() == ROW["loan_id"] else None)
    monkeypatch.setattr(api.modelo, "_pacote", lambda *a, **k: {**PACKAGE, "faixas_treino": LIMITS})
    monkeypatch.setattr(api, "prever", _prediction)


@pytest.fixture
def client():
    return TestClient(api.app)


def _url(cid=ROW["loan_id"]):
    return f"/contracts/{cid}/scenario"


def test_without_changes_returns_the_original_and_the_form(client):
    body = client.post(_url(), json={}).json()
    assert body["original"] == body["cenario"] and body["efeitos"] == [] and body["alteracoes"] == {}
    assert len(CALLS) == 1  # sem troca: o prever() roda uma vez só
    fields = {f["campo"]: f for f in body["campos"]}
    assert list(fields) == scenario.EDITABLE
    assert fields["prazo_meses"]["valor_atual"] == 60 and fields["prazo_meses"]["limite"] == "treino"
    assert (fields["prazo_meses"]["minimo"], fields["prazo_meses"]["maximo"]) == (6.0, 60.0)
    assert fields["passivos_total"]["limite"] == "treino" and fields["passivos_total"]["maximo"] == 3190.7
    assert "Retiree" not in fields["tempo_emprego_atual"]["opcoes"]
    assert fields["tipo_verificacao"]["opcoes"] == [1, 2, 3, 4]
    assert body["procedencia"]["modo"] == "ao_vivo" and body["procedencia"]["calculado_em"]


def test_changing_only_the_rate_keeps_pd_and_fair_rate(client):
    body = client.post(_url(), json={"juro_aa": 20.0}).json()
    original, new = body["original"], body["cenario"]
    assert new["pd"] == original["pd"] and new["juro_justo"] == original["juro_justo"]
    assert new["juro_cobrado"] == 0.2 and new["situacao_preco"] != original["situacao_preco"]
    assert body["parcela_cenario"] < body["parcela_original"]
    assert body["efeitos"] == []  # o juro não é variável do modelo: não entra no "O que mudou o risco"


def test_changing_the_term_runs_the_model_again(client):
    body = client.post(_url(), json={"prazo_meses": 36}).json()
    assert body["cenario"]["pd"] < body["original"]["pd"]
    assert CALLS[1]["prazo_meses"] == 36 and CALLS[1]["renda_total"] == ROW["renda_total"]
    (effect,) = body["efeitos"]
    assert effect["campo"] == "prazo_meses" and effect["efeito"] == "reduz" and effect["valor_original"] == 60


def test_each_field_is_also_measured_alone(client):
    body = client.post(_url(), json={"prazo_meses": 36, "renda_total": 1000.0}).json()
    effects = {e["campo"]: e["efeito"] for e in body["efeitos"]}
    assert effects == {"prazo_meses": "reduz", "renda_total": "aumenta"}
    assert len(CALLS) == 4  # original + cenário + um por campo
    assert CALLS[2]["renda_total"] == ROW["renda_total"] and CALLS[3]["prazo_meses"] == ROW["prazo_meses"]


def test_out_of_the_training_range_is_422(client):
    r = client.post(_url(), json={"prazo_meses": 120})
    assert r.status_code == 422 and "faixa vista no treino" in r.json()["detail"]
    assert CALLS == []  # nem chega ao modelo


def test_unknown_or_protected_fields_are_refused(client):
    for field in ("genero", "idade", "pais"):
        assert client.post(_url(), json={field: 1}).status_code == 422
    assert client.post(_url(), json={"tipo_verificacao": 9}).status_code == 422


def test_not_found_and_database_down(client, monkeypatch):
    assert client.post(_url("nao-existe"), json={}).status_code == 404

    def down(cid):
        raise api.database.DatabaseUnavailable("sem banco")
    monkeypatch.setattr(api.database, "load_contract", down)
    r = client.post(_url(), json={})
    assert r.status_code == 503 and "Laboratório precisa do banco" in r.json()["detail"]


def test_missing_model_is_503(client, monkeypatch):
    def missing(*a, **k):
        raise FileNotFoundError("pacote")
    monkeypatch.setattr(api.modelo, "_pacote", missing)
    assert client.post(_url(), json={}).status_code == 503


def test_installment_uses_the_batch_function():
    assert scenario.installment(1200, 0.0, 12) == 100.0
    assert scenario.installment(None, 0.2, 12) is None
