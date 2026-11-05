"""Testes da API sem o modelo real: o prever() é trocado por respostas de exemplo
(docs/exemplos_prever.json), então rodam na CI sem o .joblib."""
import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("xgboost")
from fastapi.testclient import TestClient  # noqa: E402

import src.api.main as api  # noqa: E402

EXEMPLOS = json.loads((Path(__file__).resolve().parents[2] / "docs" / "exemplos_prever.json")
                      .read_text(encoding="utf-8"))
POR_SITUACAO = {e["situacao_preco"]: e for e in EXEMPLOS}

PAYLOAD = {
    "loan_id": "EMP-TESTE", "amount": 5000, "income_total": 2500, "loan_duration": 36,
    "country": "EE(Estônia)", "interest_cobrado": 24.5, "liabilities_total": 450,
    "gender": 1, "age": 35,
}


@pytest.fixture
def cliente():
    return TestClient(api.app)


def _troca_prever(monkeypatch, saida, capturado=None):
    def falso(contrato):
        if capturado is not None:
            capturado.update(contrato)
        return saida
    monkeypatch.setattr(api, "prever", falso)


def test_contrato_enviado_ao_prever(cliente, monkeypatch):
    enviado = {}
    _troca_prever(monkeypatch, POR_SITUACAO["acima_do_justo"], enviado)
    assert cliente.post("/prever", json=PAYLOAD).status_code == 200
    assert enviado["pais"] == "EE"
    assert enviado["prazo_meses"] == 36
    assert enviado["juro_aa"] == 24.5          # em %, o prever() converte
    assert enviado["passivos_total"] == 450
    assert "genero" not in enviado and "idade" not in enviado
    for chave in ("passivos_existentes", "novo_cliente", "tipo_verificacao"):
        assert chave in enviado                 # as chaves precisam existir


@pytest.mark.parametrize("situacao", sorted(POR_SITUACAO))
def test_as_quatro_situacoes_passam_no_schema(cliente, monkeypatch, situacao):
    _troca_prever(monkeypatch, POR_SITUACAO[situacao])
    r = cliente.post("/prever", json=PAYLOAD)
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["situacao_preco"] == situacao
    assert corpo["parecer_ia"]["origem"] == "template"
    assert "juro_risco" not in corpo
    if situacao == "revisao_manual":
        assert corpo["pd"] is None and corpo["parecer_ia"]["recomendacao"] == "revisao_manual"


@pytest.mark.parametrize("situacao", sorted(POR_SITUACAO))
def test_parecer_de_saida_pronta(cliente, situacao):
    r = cliente.post("/parecer", json=POR_SITUACAO[situacao])
    assert r.status_code == 200, r.text
    esperado = {"acima_do_justo": "revisar_preco", "abaixo_do_justo": "revisar_preco",
                "dentro_da_margem": "manter_preco", "revisao_manual": "revisao_manual"}
    assert r.json()["recomendacao"] == esperado[situacao]


def test_sem_modelo_responde_503(cliente, monkeypatch):
    def sem_arquivo(contrato):
        raise FileNotFoundError
    monkeypatch.setattr(api, "prever", sem_arquivo)
    assert cliente.post("/prever", json=PAYLOAD).status_code == 503