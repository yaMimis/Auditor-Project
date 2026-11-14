"""POST /contracts/{id}/invariance: gênero e idade trocados não mudam o resultado do modelo.

Banco e modelo falsos. O prever() falso registra o que recebeu, para conferir que os atributos
chegaram mesmo trocados à segunda execução (o teste não é de faz de conta)."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("xgboost")
from fastapi.testclient import TestClient  # noqa: E402

import src.api.main as api  # noqa: E402
from src.api import invariance  # noqa: E402
from tests.api.test_contract_analysis import PACKAGE, ROW, _prediction  # noqa: E402

PROTECTED = {"genero": 1, "idade": 33}
SEEN = []


def _recording_prediction(row, package=None):
    SEEN.append({k: row.get(k) for k in invariance.PROTECTED_FIELDS})
    return _prediction(row, package)


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    SEEN.clear()
    monkeypatch.setattr(api.database, "load_contract",
                        lambda cid: dict(ROW) if cid.strip().lower() == ROW["loan_id"] else None)
    monkeypatch.setattr(api.database, "load_protected", lambda cid: dict(PROTECTED))
    monkeypatch.setattr(api.modelo, "_pacote", lambda *a, **k: PACKAGE)
    monkeypatch.setattr(api, "prever", _recording_prediction)


@pytest.fixture
def client():
    return TestClient(api.app)


def _url(cid=ROW["loan_id"]):
    return f"/contracts/{cid}/invariance"


def test_swapping_gender_and_age_keeps_the_result(client):
    body = client.post(_url()).json()
    assert body["identico"] is True and body["diferencas"] == []
    assert body["original"] == body["trocado"] and body["modelo_sem_atributos_protegidos"] is True
    assert body["atributos_trocados"] == ["gênero", "idade"] and body["contrato_id"] == ROW["loan_id"]
    # as duas execuções receberam mesmo valores diferentes
    assert SEEN == [{"genero": 1, "idade": 33}, {"genero": 0, "idade": 58}]


def _keys_and_leaves(obj, keys, leaves):
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(k)
            _keys_and_leaves(v, keys, leaves)
    elif isinstance(obj, list):
        for v in obj:
            _keys_and_leaves(v, keys, leaves)
    else:
        leaves.append(obj)
    return keys, leaves


def test_real_values_never_leave_the_api(client):
    keys, leaves = _keys_and_leaves(client.post(_url()).json(), set(), [])
    assert not keys & {"genero", "idade", "gender", "age"}  # nem como campo
    assert 33 not in leaves and 58 not in leaves  # nem como valor (idade real e trocada)


def test_a_model_that_used_gender_would_be_caught(client, monkeypatch):
    def biased(row, package=None):
        out = _prediction(row, package)
        out["pd"] = round(out["pd"] + 0.05 * row["genero"], 4)
        return out
    monkeypatch.setattr(api, "prever", biased)
    body = client.post(_url()).json()
    assert body["identico"] is False and body["diferencas"] == ["pd"]


def test_swap_rules():
    assert invariance.swapped({"genero": 0, "idade": 50}) == {"genero": 1, "idade": 25}
    assert invariance.swapped({"genero": 2, "idade": 70}) == {"genero": 0, "idade": 45}
    assert invariance.swapped({"genero": None, "idade": None}) == {"genero": 0, "idade": 60}
    assert invariance.swapped({"genero": 1, "idade": 60})["idade"] == 35


def test_errors(client, monkeypatch):
    assert client.post(_url("nao-existe")).status_code == 404

    def down(cid):
        raise api.database.DatabaseUnavailable("sem banco")
    monkeypatch.setattr(api.database, "load_contract", down)
    r = client.post(_url())
    assert r.status_code == 503 and "precisa do banco" in r.json()["detail"]
