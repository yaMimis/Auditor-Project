"""Lote da carteira: mesmo resultado do prever() e formato que o painel lê."""
import numpy as np
import pandas as pd
import pytest

from src.app.carteira import OBRIGATORIAS, carregar_carteira, resumo
from src.modelos.carteira import juro_justo_vetor, pontuar_lote, selecionar
from src.modelos.prever import juro_justo, montar_pacote, prever
from src.modelos.variaveis import criar_variaveis
from src.modelos.xgb import treinar_final_completo
from tests.modelos.test_treino import _base_sintetica


@pytest.fixture(scope="module")
def pacote():
    treino = _base_sintetica(900)
    modelo = treinar_final_completo(criar_variaveis(treino),
                                    {"max_depth": 3, "min_child_weight": 5, "reg_lambda": 1}, 50)
    euribor = pd.Series([1.2, 0.5, 0.1, -0.2],
                        index=pd.to_datetime(["2013-01-01", "2015-01-01", "2016-01-01", "2017-01-01"]))
    return montar_pacote(modelo, treino, euribor)


@pytest.fixture(scope="module")
def carteira():
    b = _base_sintetica(80, semente=5)
    r = np.random.default_rng(5)
    b["ano"] = r.choice([2016, 2018, 2020], len(b))
    b["data_emprestimo"] = pd.to_datetime(b["ano"].astype(str) + "-06-15")
    b["loan_id"] = [f"L{i}" for i in range(len(b))]
    b["juro_aa"] = r.uniform(10, 90, len(b))
    b.loc[:4, "renda_total"] = 1e9          # fora da faixa do treino → revisão manual
    b["principal_pago"] = b["valor_concedido"] * r.uniform(0.3, 1, len(b))
    b["juros_multas_pagos"] = r.uniform(0, 800, len(b))
    return b


def test_vetor_igual_ao_escalar():
    prazos, pds, lgds, custos = [12, 36, 60, 1], [0.1, 0.4, 0.8, 0.3], [0.34, 0.76, 0.55, 0.6], [0.15, 0.2, 0.32, 0.1]
    v = juro_justo_vetor(prazos, pds, lgds, custos)
    for k in range(4):
        assert v[k] == pytest.approx(juro_justo(prazos[k], pds[k], lgds[k], custos[k]), abs=1e-5)


def test_lote_igual_ao_prever(pacote, carteira):
    lote = pontuar_lote(carteira, pacote).set_index("contrato_id")
    for _, linha in carteira.iterrows():
        um = prever(linha.drop("ano").to_dict(), pacote)
        l = lote.loc[um["contrato_id"]]
        assert l["situacao_preco"] == um["situacao_preco"]
        if um["pd"] is not None:
            assert l["pd"] == pytest.approx(um["pd"], abs=1e-4)
            assert l["juro_justo"] == pytest.approx(um["juro_justo"], abs=1e-4)
            assert l["faixa"] == um["faixa"]
    assert (lote["situacao_preco"] == "revisao_manual").sum() >= 5


def test_colunas_e_regras(pacote, carteira, tmp_path):
    lote = pontuar_lote(carteira, pacote)
    acima = lote["situacao_preco"] == "acima_do_justo"
    assert (lote.loc[acima, "excesso_eur"] > 0).all()
    assert lote.loc[~acima, "excesso_eur"].isna().all()
    assert lote.loc[lote["ano"] > 2016, "rentabilidade_realizada"].isna().all()
    assert lote.loc[lote["ano"] == 2016, "rentabilidade_realizada"].notna().all()
    assert (lote["perda_nao_coberta_eur"].dropna() >= 0).all()

    lote.to_csv(tmp_path / "carteira_auditoria.csv", index=False)
    df = carregar_carteira(tmp_path)
    assert set(OBRIGATORIAS) <= set(df.columns)
    assert resumo(df)["auditados"] > 0


def test_selecionar():
    bruto = pd.DataFrame({
        "data_emprestimo": pd.to_datetime(["2015-03-01", "2016-03-01", "2016-03-01", "2019-03-01", "2019-03-01"]),
        "status": ["Repaid", "Repaid", "Current", "Current", "Current"],
        "data_default": [pd.NaT] * 5,
        "pais": ["EE", "EE", "EE", "FI", "SK"],
        "reestruturado": [False, True, False, None, False],
    })
    s = selecionar(bruto)
    assert list(s["ano"]) == [2016, 2019]
    assert list(s["fora_da_auditoria"]) == [True, False]


def test_calibracao_pela_mediana_divide_a_safra(pacote, carteira):
    from src.modelos.carteira import calibrar_margem_mediana
    margens = calibrar_margem_mediana(carteira, pacote)
    assert set(margens) == {2016, 2018, 2020}
    lote = pontuar_lote(carteira, pacote, margens=margens)
    lote = lote[lote["pd"].notna()]
    for ano, g in lote.groupby("ano"):
        assert abs((g["juro_cobrado"] - g["juro_justo"]).median()) < 0.002, ano
