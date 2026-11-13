"""GET /contracts/{id}/analysis: contrato do banco → prever() ao vivo → tela de análise.

Banco, modelo e LLM são falsos aqui; o juro justo usa a função real do prever()."""
import json

import pandas as pd
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("xgboost")
from fastapi.testclient import TestClient  # noqa: E402

import src.api.main as api  # noqa: E402
from src.api import contract_analysis  # noqa: E402
from src.modelos import prever as modelo  # noqa: E402

ROW = {  # uma linha como o database.load_contract() devolve (nomes do banco, sem gênero e idade)
    "loan_id": "98ffaaa4-0b86-4bcc-a179-a68a00a9f09e", "data_emprestimo": "2016-05-10", "novo_cliente": False,
    "valor_solicitado": 5315.0, "valor_concedido": 5315.0, "juro_aa": 38.95, "prazo_meses": 60,
    "tipo_verificacao": 4, "pais": "FI", "escolaridade": 3, "tempo_emprego_atual": "MoreThan5Years",
    "tipo_moradia": 1, "renda_total": 2100.0, "renda_pensao": 0.0, "renda_auxilio_familiar": 0.0,
    "renda_assistencia_social": 0.0, "renda_pensao_alimenticia": 0.0, "n_emprestimos_anteriores": 2,
    "valor_emprestimos_anteriores": 3000.0, "pagamentos_anteriores": 1200.0, "quitacoes_antecipadas_valor": 0.0,
    "quitacoes_antecipadas_qtd": 0, "passivos_existentes": 8, "passivos_total": 900.0,
    "refinanciamento_passivos": 0, "divida_renda": 0.0, "caixa_livre": 0.0, "score_es_microl": None,
    "score_es_equifax": None, "score_fi_asiakastieto": "C", "score_ee_mini": None,
}
PACKAGE = {
    "referencia": pd.DataFrame({"pais": ["FI", "FI", "EE"], "ano": [2015, 2015, 2015],
                                "renda_total": [1800.0, 2200.0, 900.0]}),
    "euribor_12m": pd.Series([0.06, -0.01], index=pd.to_datetime(["2016-01-01", "2016-06-01"])),
}
PD = 0.6982


def _prediction(row, package=None):
    """Saída no formato do prever(), com o juro justo calculado pela função real."""
    margin = modelo.MARGEM_POR_SAFRA.get(2016, modelo.MARGEM_POR_SAFRA[max(modelo.MARGEM_POR_SAFRA)])
    fair = round(modelo.juro_justo(60, PD, modelo.LGD_POR_PAIS["FI"], 0.0006 + margin), 4)
    return {"contrato_id": row["loan_id"], "versao_modelo": "xgboost_teste", "juro_cobrado": 0.3895,
            "pd": PD, "pd_ic95": [0.6332, 0.7644], "faixa": "D", "juro_justo": fair,
            "juro_justo_min": round(fair - 0.02, 4), "juro_justo_max": round(fair + 0.02, 4),
            "diferenca_pp": round((0.3895 - fair) * 100, 1), "situacao_preco": "acima_do_justo",
            "juro_pares_mediana": 0.2676, "alerta_dados": False,
            "motivos": [{"variavel": "prazo_meses", "rotulo": "prazo do empréstimo",
                         "efeito": "aumenta_risco", "valor": 60.0, "peso": 0.339}]}


OUTCOME = {"inadimplente": True, "recebido_total": 2831.95, "resultado_eur": -2483.05,
           "retorno_realizado": -0.4672, "principal_perdido": 4100.0, "duracao_meses": 21.3}


@pytest.fixture(autouse=True)
def fakes(monkeypatch):
    monkeypatch.setattr(api.cadeia, "chamar_llm", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("sem LLM")))
    monkeypatch.setattr(api.cadeia, "buscar_trechos", lambda *a, **k: [])
    monkeypatch.setattr(api.database, "bc_rate", lambda *a, **k: None)
    monkeypatch.setattr(api.database, "load_contract", lambda cid: dict(ROW) if cid.lower() == ROW["loan_id"] else None)
    monkeypatch.setattr(api.database, "observed_outcome", lambda cid: dict(OUTCOME))
    monkeypatch.setattr(api.modelo, "_pacote", lambda *a, **k: PACKAGE)
    monkeypatch.setattr(api, "prever", _prediction)


@pytest.fixture
def client():
    return TestClient(api.app)


def test_analysis_runs_model_and_returns_everything(client):
    r = client.get(f"/contracts/{ROW['loan_id'].upper()}/analysis")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["resultado"]["pd"] == PD and body["resultado"]["parecer_ia"]["origem"] == "template"
    assert body["contrato"] == {"pais": "FI", "data_emprestimo": "2016-05-10", "valor_concedido": 5315.0,
                                "valor_solicitado": 5315.0, "prazo_meses": 60, "juro_cobrado": 0.3895}
    assert body["procedencia"]["versao_modelo"] == "xgboost_teste"
    assert body["procedencia"]["fora_do_dominio"] is False and body["procedencia"]["tempo_ms"] >= 0
    assert body["procedencia"]["incerteza"] == "bootstrap"  # o prever() devolveu pd_ic95
    assert body["resultado_observado"]["inadimplente"] is True


def test_considered_data_has_all_model_variables_split_by_origin(client):
    variables = {v["variavel"]: v for v in client.get(f"/contracts/{ROW['loan_id']}/analysis").json()["dados_considerados"]}
    assert set(variables) == set(contract_analysis.MODEL_FEATURES) and len(variables) == 21
    assert variables["renda_total"]["origem"] == "fornecida" and variables["renda_total"]["valor"] == 2100.0
    assert variables["divida_sobre_renda"]["origem"] == "derivada"
    assert variables["divida_sobre_renda"]["valor"] == pytest.approx(900 / 2100, abs=1e-6)
    assert variables["renda_relativa"]["valor"] == pytest.approx(2100 / 2000, abs=1e-6)  # mediana FI 2015
    assert variables["pais"]["tipo"] == "categorica" and variables["escolaridade"]["valor"] == 3


def test_no_protected_attribute_anywhere(client):
    text = json.dumps(client.get(f"/contracts/{ROW['loan_id']}/analysis").json())
    for word in ("genero", "idade", "estado_civil", "n_dependentes"):
        assert f'"{word}"' not in text  # como chave ou variável ("escolaridade" contém "idade")
    selected = {col for cols in api.database.CONTRACT_COLUMNS.values() for col in cols}
    assert not selected & contract_analysis.PROTECTED  # o banco nem devolve esses campos


def test_pricing_parameters_reproduce_fair_rate(client):
    pricing = client.get(f"/contracts/{ROW['loan_id']}/analysis").json()["precificacao"]
    assert pricing["lgd"] == modelo.LGD_POR_PAIS["FI"] and pricing["euribor_12m"] == 0.0006  # Euribor de jan/16
    assert pricing["juro_justo_sem_risco"] < pricing["custo_anual"] + 0.01
    assert pricing["efeito_do_risco_pp"] > 0  # o risco encarece o juro justo


def test_pricing_uses_the_same_parameters_as_prever():
    """Os parâmetros vêm de prever.parametros_preco(): com eles a função juro_justo() reproduz a taxa do prever()."""
    pricing = contract_analysis.pricing_parameters(ROW, _prediction(ROW), PACKAGE)
    fair = modelo.juro_justo(pricing["prazo_meses"], PD, pricing["lgd"], pricing["custo_anual"])
    assert round(fair, 4) == _prediction(ROW)["juro_justo"]
    manual = {**_prediction(ROW), "pd": None, "juro_justo": None}
    assert contract_analysis.pricing_parameters(ROW, manual, PACKAGE) is None


def test_contract_without_outcome(client, monkeypatch):
    monkeypatch.setattr(api.database, "observed_outcome", lambda cid: None)
    assert client.get(f"/contracts/{ROW['loan_id']}/analysis").json()["resultado_observado"] is None


def test_unknown_contract_is_404(client):
    assert client.get("/contracts/nao-existe/analysis").status_code == 404


def test_database_down_is_503(client, monkeypatch):
    def down(cid):
        raise api.database.DatabaseUnavailable("sem banco")
    monkeypatch.setattr(api.database, "load_contract", down)
    assert client.get(f"/contracts/{ROW['loan_id']}/analysis").status_code == 503


def test_missing_model_is_503(client, monkeypatch):
    def missing(*a, **k):
        raise FileNotFoundError("pacote")
    monkeypatch.setattr(api.modelo, "_pacote", missing)
    r = client.get(f"/contracts/{ROW['loan_id']}/analysis")
    assert r.status_code == 503 and "modelos_salvos" in r.json()["detail"]


def test_without_bootstrap_provenance_says_standard_margin(client, monkeypatch):
    monkeypatch.setattr(api, "prever", lambda row, package=None: {**_prediction(row), "pd_ic95": None})
    body = client.get(f"/contracts/{ROW['loan_id']}/analysis").json()
    assert body["procedencia"]["incerteza"] == "margem_padrao"
