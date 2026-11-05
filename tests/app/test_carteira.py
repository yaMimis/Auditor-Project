"""Leitura e resumo da carteira (src/app/carteira.py), com dados sintéticos."""
import json

import pandas as pd
import pytest

from src.app import carteira as cart


def _linha(cid, faixa, situacao, cobrado, ano=2018, pais="EE", **extra):
    return {"contrato_id": cid, "ano": ano, "pais": pais, "pd": 0.3, "faixa": faixa,
            "juro_cobrado": cobrado, "juro_justo": 0.20, "juro_justo_min": 0.18,
            "juro_justo_max": 0.22, "situacao_preco": situacao, **extra}


@pytest.fixture
def pasta(tmp_path):
    df = pd.DataFrame([
        _linha("A1", "A", "acima_do_justo", 0.30, excesso_eur=100.0, rentabilidade_realizada=0.10),
        _linha("A2", "A", "dentro_da_margem", 0.20, excesso_eur=0.0, rentabilidade_realizada=0.05),
        _linha("B1", "B", "abaixo_do_justo", 0.10, perda_nao_coberta_eur=50.0, rentabilidade_realizada=-0.02),
        _linha("B2", "B", "acima_do_justo", 0.25, ano=2016, pais="ES", excesso_eur=30.0),
        _linha("R1", "B", "acima_do_justo", 0.40, fora_da_auditoria=True),  # reestruturado
        {**_linha("M1", None, "revisao_manual", 0.20), "pd": None, "juro_justo": None,
         "juro_justo_min": None, "juro_justo_max": None},
    ])
    df["fora_da_auditoria"] = df["fora_da_auditoria"].fillna(False).astype(bool)
    df.to_csv(tmp_path / cart.ARQ_CARTEIRA, index=False)
    (tmp_path / cart.ARQ_EQUIDADE).write_text(json.dumps([
        {"atributo": "Gênero", "comparacao": "f × m", "diferenca_pp": 0.3, "ic95_min": -0.1, "ic95_max": 0.7},
        {"atributo": "País", "comparacao": "ES × EE", "diferenca_pp": 5.0, "ic95_min": 4.0, "ic95_max": 6.0},
    ]), encoding="utf-8")
    return tmp_path


def test_sem_arquivos_devolve_none(tmp_path):
    assert cart.carregar_carteira(tmp_path) is None
    assert cart.carregar_equidade(tmp_path) is None


def test_reestruturados_saem_e_pais_nao_e_grupo(pasta):
    df = cart.carregar_carteira(pasta)
    assert "R1" not in set(df["contrato_id"])
    assert [e["atributo"] for e in cart.carregar_equidade(pasta)] == ["Gênero"]


def test_coluna_obrigatoria_faltando(tmp_path):
    pd.DataFrame([{"contrato_id": "X"}]).to_csv(tmp_path / cart.ARQ_CARTEIRA, index=False)
    with pytest.raises(ValueError, match="sem as colunas"):
        cart.carregar_carteira(tmp_path)


def test_resumo_e_filtros(pasta):
    df = cart.carregar_carteira(pasta)
    r = cart.resumo(df)
    assert r["auditados"] == 4 and r["revisao_manual"] == 1
    assert r["acima"] == 0.5 and r["abaixo"] == 0.25
    assert r["pago_a_mais_eur"] == 130.0 and r["perda_nao_coberta_eur"] == 50.0
    assert cart.resumo(cart.filtrar(df, pais="ES"))["auditados"] == 1
    assert cart.resumo(cart.filtrar(df, anos=(2017, 2021)))["auditados"] == 3


def test_por_faixa_soma_um(pasta):
    for linha in cart.por_faixa(cart.carregar_carteira(pasta)):
        assert sum(linha[s] for s in cart.SITUACOES_PRECO) == pytest.approx(1.0)


def test_fila_ordenada_pela_distancia(pasta):
    fila = cart.fila_revisao(cart.carregar_carteira(pasta))
    assert list(fila["distancia_pp"]) == [8.0, 8.0, 3.0]
    assert set(fila["contrato_id"][:2]) == {"A1", "B1"} and fila["contrato_id"].iloc[2] == "B2"


def test_backtest_por_faixa(pasta):
    bt = cart.backtest(cart.carregar_carteira(pasta))
    assert bt.loc["A", "acima_do_justo"] == pytest.approx(0.10)
    assert bt.loc["B", "abaixo_do_justo"] == pytest.approx(-0.02)