"""prever() com um modelo pequeno treinado aqui mesmo: as 4 situações saem
quando devem, com bootstrap e pares, e todas respeitam o contrato da Maria."""
import numpy as np
import pandas as pd
import pytest

from src.modelos.incerteza import treinar_bootstrap
from src.modelos.prever import montar_pacote, prever
from src.modelos.variaveis import criar_variaveis
from src.modelos.xgb import treinar_final_completo
from tests.modelos.test_contrato_prever import validar_saida_prever
from tests.modelos.test_treino import _base_sintetica

PARAMS = {"max_depth": 3, "min_child_weight": 5, "reg_lambda": 1}


@pytest.fixture(scope="module")
def pacote():
    treino = _base_sintetica(900)
    var = criar_variaveis(treino)
    euribor = pd.Series([1.0, 0.2], index=pd.to_datetime(["2013-01-01", "2016-01-01"]))
    pac = montar_pacote(treinar_final_completo(var, PARAMS, 50), treino, euribor)
    pac["bootstrap"] = treinar_bootstrap(var, PARAMS, 50, n_reamostras=5)
    pac["pares"] = pd.DataFrame({"pais": ["EE"] * 5, "faixa": list("ABCDE"), "ano": [2015] * 5,
                                 "juro_pares_mediana": [0.2, 0.25, 0.3, 0.35, 0.4], "n": [40] * 5})
    return pac


@pytest.fixture(scope="module")
def contrato():
    c = _base_sintetica(1, semente=7).iloc[0].drop("ano").to_dict()
    c.update(loan_id="T-1", pais="EE", data_emprestimo=pd.Timestamp("2019-05-10"),
             renda_total=1200.0, valor_concedido=2000.0, prazo_meses=36, juro_aa=30.0)
    return c


def _com_juro(contrato, juro_fracao):
    return {**contrato, "juro_aa": round(juro_fracao * 100, 4)}


def test_quatro_situacoes(pacote, contrato):
    base = prever(contrato, pacote)
    assert base["pd"] is not None and base["juro_justo_min"] < base["juro_justo_max"]

    casos = {
        "acima_do_justo": _com_juro(contrato, base["juro_justo_max"] + 0.05),
        "abaixo_do_justo": _com_juro(contrato, max(base["juro_justo_min"] - 0.05, 0.001)),
        "dentro_da_margem": _com_juro(contrato, base["juro_justo"]),
        "revisao_manual": {**contrato, "renda_total": 1e9},     # fora da faixa do treino
    }
    if base["juro_justo_min"] <= 0.05:
        pytest.skip("margem encosta no zero: não há juro abaixo dela")
    for esperado, c in casos.items():
        saida = prever(c, pacote)
        assert saida["situacao_preco"] == esperado
        validar_saida_prever(saida)
        if esperado == "revisao_manual":
            assert saida["alerta_dados"] and saida["pd"] is None
            assert saida["pd_ic95"] is None and saida["juro_pares_mediana"] is None
        else:
            lo, hi = saida["pd_ic95"]
            assert lo <= saida["pd"] <= hi
            assert saida["juro_pares_mediana"] is not None          # 2019 → último ano (2015)
            assert saida["juro_justo"] == base["juro_justo"]        # o juro cobrado não muda o justo


def test_sem_bootstrap_volta_para_2pp(pacote, contrato):
    sem = {k: v for k, v in pacote.items() if k != "bootstrap"}
    s = prever(contrato, sem)
    assert s["pd_ic95"] is None
    assert s["juro_justo_max"] - s["juro_justo"] == pytest.approx(0.02, abs=1e-4)
    validar_saida_prever(s)
