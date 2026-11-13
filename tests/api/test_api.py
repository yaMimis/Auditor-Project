"""Testes da API sem o modelo real: o prever() é trocado por respostas de exemplo
(docs/exemplos_prever.json), então rodam na CI sem o .joblib.

O Gemini, a busca nas normas e o banco também são trocados por versões falsas: nenhum
teste chama o LLM de verdade (mesmo com a GOOGLE_API_KEY no .env) nem depende do banco."""
import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("xgboost")
from fastapi.testclient import TestClient  # noqa: E402

import src.api.main as api  # noqa: E402

EXAMPLES = json.loads((Path(__file__).resolve().parents[2] / "docs" / "exemplos_prever.json")
                      .read_text(encoding="utf-8"))
BY_SITUATION = {e["situacao_preco"]: e for e in EXAMPLES}
_CASES_FILE = Path(__file__).resolve().parents[2] / "docs" / "casos_de_teste.json"
REAL_CASES = ([c for items_list in json.loads(_CASES_FILE.read_text(encoding="utf-8")).values() for c in items_list]
               if _CASES_FILE.exists() else [])

PAYLOAD = {
    "loan_id": "EMP-TESTE", "amount": 5000, "income_total": 2500, "loan_duration": 36,
    "country": "EE(Estônia)", "interest_cobrado": 24.5, "liabilities_total": 450,
    "gender": 1, "age": 35,
}


@pytest.fixture(autouse=True)
def no_llm_no_database(monkeypatch):
    """Sem LLM e sem banco: o gerar_parecer() cai no template, como manda a regra."""
    def no_llm(*a, **k):
        raise RuntimeError("LLM desligado nos testes")
    monkeypatch.setattr(api.cadeia, "chamar_llm", no_llm)
    monkeypatch.setattr(api.cadeia, "buscar_trechos", lambda *a, **k: [])
    monkeypatch.setattr(api.database, "bc_rate", lambda *a, **k: None)


@pytest.fixture
def client():
    return TestClient(api.app)


def _stub_prever(monkeypatch, output, captured=None):
    def fake(contract):
        if captured is not None:
            captured.update(contract)
        return output
    monkeypatch.setattr(api, "prever", fake)


def test_contract_sent_to_prever(client, monkeypatch):
    sent = {}
    _stub_prever(monkeypatch, BY_SITUATION["acima_do_justo"], sent)
    assert client.post("/predict", json=PAYLOAD).status_code == 200
    assert sent["pais"] == "EE"
    assert sent["prazo_meses"] == 36
    assert sent["juro_aa"] == 24.5          # em %, o prever() converte
    assert sent["passivos_total"] == 450
    assert "genero" not in sent and "idade" not in sent
    for decision_key in ("passivos_existentes", "novo_cliente", "tipo_verificacao"):
        assert decision_key in sent                 # as chaves precisam existir


@pytest.mark.parametrize("situation", sorted(BY_SITUATION))
def test_all_four_situations_pass_schema(client, monkeypatch, situation):
    _stub_prever(monkeypatch, BY_SITUATION[situation])
    r = client.post("/predict", json=PAYLOAD)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["situacao_preco"] == situation
    assert body["parecer_ia"]["origem"] == "template"
    assert "juro_risco" not in body
    if situation == "revisao_manual":
        assert body["pd"] is None and body["parecer_ia"]["recomendacao"] == "revisao_manual"


@pytest.mark.parametrize("situation", sorted(BY_SITUATION))
def test_opinion_from_ready_prediction(client, situation):
    r = client.post("/opinion", json=BY_SITUATION[situation])
    assert r.status_code == 200, r.text
    expected = {"acima_do_justo": "revisar_preco", "abaixo_do_justo": "revisar_preco",
                "dentro_da_margem": "manter_preco", "revisao_manual": "revisao_manual"}
    assert r.json()["recomendacao"] == expected[situation]


def test_default_date_is_today_and_never_future(client, monkeypatch):
    from datetime import date, timedelta
    sent = {}
    _stub_prever(monkeypatch, BY_SITUATION["dentro_da_margem"], sent)
    assert client.post("/predict", json=PAYLOAD).status_code == 200
    assert sent["data_emprestimo"] == date.today().isoformat()
    future = (date.today() + timedelta(days=1)).isoformat()
    assert client.post("/predict", json={**PAYLOAD, "data_emprestimo": future}).status_code == 422


@pytest.mark.skipif(not REAL_CASES, reason="docs/casos_de_teste.json ausente")
@pytest.mark.parametrize("case", REAL_CASES, ids=lambda c: f'{c["situacao_preco"]}-{c["contrato_id"][:8]}')
def test_real_cases_pass_through_api(client, monkeypatch, case):
    """Os casos reais do prever() (Samuel) passam no schema de saída e geram parecer."""
    _stub_prever(monkeypatch, case)
    r = client.post("/predict", json=PAYLOAD)
    assert r.status_code == 200, r.text
    assert client.post("/opinion", json=case).status_code == 200


def test_missing_model_returns_503(client, monkeypatch):
    def without_file(contract):
        raise FileNotFoundError
    monkeypatch.setattr(api, "prever", without_file)
    assert client.post("/predict", json=PAYLOAD).status_code == 503


# ---------- Decisões do analista (banco trocado por funções falsas) ----------

def _new_decision(situation="acima_do_justo", **extra):
    resultado = dict(BY_SITUATION[situation])
    resultado["parecer_ia"] = json.loads(json.dumps(api._opinion(resultado), default=str))
    return {"requisicao_id": "8f14e45f-ceea-467f-a8d9-1b4c2e6f0a11", "analista": "Yasmin",
            "decisao": "revisar_preco", "justificativa": "Preço sem justificativa de risco.",
            "taxa_proposta": 0.18, "resultado": resultado, **extra}


def _recorded_row(record_):
    from datetime import datetime, timezone
    columns_ = {k: v for k, v in record_.items() if k not in ("requisicao_id", "prever_json", "parecer_json")}
    return {"decisao_id": 1, "registrada_em": datetime(2026, 11, 6, 16, 0, tzinfo=timezone.utc),
            "origem": "simulacao", **columns_}


def test_decision_recorded_without_gender_or_age(client, monkeypatch):
    recorded = {}

    def fake(record_):
        recorded.update(record_)
        return _recorded_row(record_)
    monkeypatch.setattr(api.database, "record_decision", fake)
    r = client.post("/decisions", json=_new_decision())
    assert r.status_code == 201, r.text
    assert r.json()["decisao"] == "revisar_preco" and r.json()["origem"] == "simulacao"
    assert recorded["recomendacao_sistema"] == "revisar_preco" and recorded["origem_parecer"] == "template"
    assert recorded["juro_cobrado"] == BY_SITUATION["acima_do_justo"]["juro_cobrado"]
    text_ = json.dumps(recorded, default=str).lower()
    for decision_key in ('"genero"', '"idade"', '"gender"', '"age"'):
        assert decision_key not in text_
    assert "parecer_ia" not in recorded["prever_json"]


def test_proposed_rate_only_on_price_review(client, monkeypatch):
    recorded = {}
    monkeypatch.setattr(api.database, "record_decision", lambda record: (recorded.update(record), _recorded_row(record))[1])
    client.post("/decisions", json=_new_decision(decisao="manter_preco"))
    assert recorded["taxa_proposta"] is None


def test_manual_review_decision_stores_nulls(client, monkeypatch):
    """Desde 08/11 a tabela aceita revisão manual: PD, faixa e juros justos vão nulos, nunca zero."""
    recorded = {}
    monkeypatch.setattr(api.database, "record_decision", lambda record: (recorded.update(record), _recorded_row(record))[1])
    r = client.post("/decisions", json=_new_decision("revisao_manual", decisao="manter_preco"))
    assert r.status_code == 201, r.text
    for field in ("pd", "faixa", "juro_justo", "juro_justo_min", "juro_justo_max"):
        assert recorded[field] is None
    assert recorded["situacao_preco"] == "revisao_manual" and recorded["recomendacao_sistema"] == "revisao_manual"
    assert r.json()["pd"] is None


def test_blank_justification_is_rejected(client, monkeypatch):
    monkeypatch.setattr(api.database, "record_decision", lambda record: pytest.fail("não deveria gravar"))
    assert client.post("/decisions", json=_new_decision(justificativa="   ")).status_code == 422
    assert client.post("/decisions", json=_new_decision(justificativa=None)).status_code == 422
    assert client.post("/decisions", json=_new_decision(analista="")).status_code == 422


def test_invalid_fields_return_422_not_500(client, monkeypatch):
    monkeypatch.setattr(api.database, "record_decision", lambda record: pytest.fail("não deveria gravar"))
    assert client.post("/decisions", json=_new_decision(requisicao_id="nao-e-uuid")).status_code == 422
    assert client.post("/decisions", json=_new_decision(decisao="aprovar")).status_code == 422
    assert client.post("/decisions", json=_new_decision(taxa_proposta=18)).status_code == 422  # 18 = 1800%: vai em fração


def test_bc_rate_reaches_opinion(client, monkeypatch):
    """/predict busca pelo mês da data; /opinion busca pelo contrato. O código escreve o contexto."""
    requests_ = []

    def bc(contrato_id=None, data_emprestimo=None):
        requests_.append((contrato_id, data_emprestimo))
        return 126.2
    monkeypatch.setattr(api.database, "bc_rate", bc)
    _stub_prever(monkeypatch, BY_SITUATION["acima_do_justo"])
    r = client.post("/predict", json={**PAYLOAD, "data_emprestimo": "2016-03-15"})
    assert r.status_code == 200, r.text
    assert r.json()["bc_credito_pessoal_aa"] == 126.2
    assert "Referência de mercado" in r.json()["parecer_ia"]["contexto_mercado"]
    assert requests_[0] == (None, "2016-03-15")
    r = client.post("/opinion", json=BY_SITUATION["dentro_da_margem"])
    assert "Referência de mercado" in r.json()["contexto_mercado"]
    assert requests_[-1] == (BY_SITUATION["dentro_da_margem"]["contrato_id"], None)


def test_without_bc_rate_opinion_has_no_context(client, monkeypatch):
    _stub_prever(monkeypatch, BY_SITUATION["acima_do_justo"])
    body = client.post("/predict", json=PAYLOAD).json()
    assert body["parecer_ia"]["contexto_mercado"] is None
    assert body["parecer_ia"]["origem"] == "template"  # LLM desligado → template


def test_database_down_returns_503(client, monkeypatch):
    def outside(*a, **k):
        raise api.database.DatabaseUnavailable("conexão recusada")
    monkeypatch.setattr(api.database, "record_decision", outside)
    monkeypatch.setattr(api.database, "list_decisions", outside)
    assert client.post("/decisions", json=_new_decision()).status_code == 503
    assert client.get("/decisions").status_code == 503


def test_database_rule_returns_422(client, monkeypatch):
    def rejection(record):
        raise api.database.DecisionRejected("violates check constraint")
    monkeypatch.setattr(api.database, "record_decision", rejection)
    assert client.post("/decisions", json=_new_decision()).status_code == 422


def test_list_by_contract(client, monkeypatch):
    request_ = {}

    def fake(contrato_id, limit):
        request_.update(contrato_id=contrato_id, limit=limit)
        return []
    monkeypatch.setattr(api.database, "list_decisions", fake)
    assert client.get("/decisions", params={"contrato_id": "BO-1", "limit": 5}).json() == []
    assert request_ == {"contrato_id": "BO-1", "limit": 5}
