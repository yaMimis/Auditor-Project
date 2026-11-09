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
_ARQ_CASOS = Path(__file__).resolve().parents[2] / "docs" / "casos_de_teste.json"
CASOS_REAIS = ([c for lista in json.loads(_ARQ_CASOS.read_text(encoding="utf-8")).values() for c in lista]
               if _ARQ_CASOS.exists() else [])

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


def test_data_padrao_hoje_e_sem_futuro(cliente, monkeypatch):
    from datetime import date, timedelta
    enviado = {}
    _troca_prever(monkeypatch, POR_SITUACAO["dentro_da_margem"], enviado)
    assert cliente.post("/prever", json=PAYLOAD).status_code == 200
    assert enviado["data_emprestimo"] == date.today().isoformat()
    futuro = (date.today() + timedelta(days=1)).isoformat()
    assert cliente.post("/prever", json={**PAYLOAD, "data_emprestimo": futuro}).status_code == 422


@pytest.mark.skipif(not CASOS_REAIS, reason="docs/casos_de_teste.json ausente")
@pytest.mark.parametrize("caso", CASOS_REAIS, ids=lambda c: f'{c["situacao_preco"]}-{c["contrato_id"][:8]}')
def test_casos_reais_passam_na_api(cliente, monkeypatch, caso):
    """Os casos reais do prever() (Samuel) passam no schema de saída e geram parecer."""
    _troca_prever(monkeypatch, caso)
    r = cliente.post("/prever", json=PAYLOAD)
    assert r.status_code == 200, r.text
    assert cliente.post("/parecer", json=caso).status_code == 200


def test_sem_modelo_responde_503(cliente, monkeypatch):
    def sem_arquivo(contrato):
        raise FileNotFoundError
    monkeypatch.setattr(api, "prever", sem_arquivo)
    assert cliente.post("/prever", json=PAYLOAD).status_code == 503


# ---------- Decisões do analista (banco trocado por funções falsas) ----------

def _nova_decisao(situacao="acima_do_justo", **extra):
    resultado = dict(POR_SITUACAO[situacao])
    resultado["parecer_ia"] = json.loads(json.dumps(api._parecer(resultado), default=str))
    return {"requisicao_id": "8f14e45f-ceea-467f-a8d9-1b4c2e6f0a11", "analista": "Yasmin",
            "decisao": "revisar_preco", "justificativa": "Preço sem justificativa de risco.",
            "taxa_proposta": 0.18, "resultado": resultado, **extra}


def _linha_gravada(registro):
    from datetime import datetime, timezone
    colunas = {k: v for k, v in registro.items() if k not in ("requisicao_id", "prever_json", "parecer_json")}
    return {"decisao_id": 1, "registrada_em": datetime(2026, 11, 6, 16, 0, tzinfo=timezone.utc),
            "origem": "simulacao", **colunas}


def test_decisao_gravada_sem_genero_nem_idade(cliente, monkeypatch):
    gravado = {}

    def falso(registro):
        gravado.update(registro)
        return _linha_gravada(registro)
    monkeypatch.setattr(api.banco, "registrar_decisao", falso)
    r = cliente.post("/decisoes", json=_nova_decisao())
    assert r.status_code == 201, r.text
    assert r.json()["decisao"] == "revisar_preco" and r.json()["origem"] == "simulacao"
    assert gravado["recomendacao_sistema"] == "revisar_preco" and gravado["origem_parecer"] == "template"
    assert gravado["juro_cobrado"] == POR_SITUACAO["acima_do_justo"]["juro_cobrado"]
    texto = json.dumps(gravado, default=str).lower()
    for chave in ('"genero"', '"idade"', '"gender"', '"age"'):
        assert chave not in texto
    assert "parecer_ia" not in gravado["prever_json"]


def test_taxa_proposta_so_vale_ao_revisar(cliente, monkeypatch):
    gravado = {}
    monkeypatch.setattr(api.banco, "registrar_decisao", lambda reg: (gravado.update(reg), _linha_gravada(reg))[1])
    cliente.post("/decisoes", json=_nova_decisao(decisao="manter_preco"))
    assert gravado["taxa_proposta"] is None


def test_decisao_em_revisao_manual_e_recusada(cliente, monkeypatch):
    monkeypatch.setattr(api.banco, "registrar_decisao", lambda reg: pytest.fail("não deveria gravar"))
    r = cliente.post("/decisoes", json=_nova_decisao("revisao_manual"))
    assert r.status_code == 422 and "revisão manual" in r.json()["detail"]


def test_justificativa_em_branco_e_recusada(cliente):
    assert cliente.post("/decisoes", json=_nova_decisao(justificativa="   ")).status_code == 422


def test_banco_fora_responde_503(cliente, monkeypatch):
    def fora(*a, **k):
        raise api.banco.BancoIndisponivel("conexão recusada")
    monkeypatch.setattr(api.banco, "registrar_decisao", fora)
    monkeypatch.setattr(api.banco, "listar_decisoes", fora)
    assert cliente.post("/decisoes", json=_nova_decisao()).status_code == 503
    assert cliente.get("/decisoes").status_code == 503


def test_regra_do_banco_vira_422(cliente, monkeypatch):
    def recusa(reg):
        raise api.banco.DecisaoRecusada("violates check constraint")
    monkeypatch.setattr(api.banco, "registrar_decisao", recusa)
    assert cliente.post("/decisoes", json=_nova_decisao()).status_code == 422


def test_listar_por_contrato(cliente, monkeypatch):
    pedido = {}

    def falso(contrato_id, limite):
        pedido.update(contrato_id=contrato_id, limite=limite)
        return []
    monkeypatch.setattr(api.banco, "listar_decisoes", falso)
    assert cliente.get("/decisoes", params={"contrato_id": "BO-1", "limite": 5}).json() == []
    assert pedido == {"contrato_id": "BO-1", "limite": 5}
