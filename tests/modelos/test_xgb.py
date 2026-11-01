"""XGBoost: roda ponta a ponta, sem 2016, e motivos no formato da Maria."""
import numpy as np
import pandas as pd

from src.modelos.treino import _para_modelo
from src.modelos.variaveis import criar_variaveis
from src.modelos.xgb import GRADE, buscar_parametros, motivos, treinar_final
from tests.modelos.test_treino import _base_sintetica


def _base():
    b = _base_sintetica(900)
    b["ano"] = np.random.default_rng(2).choice([2013, 2014, 2015], len(b))
    # como no banco: inteiros "Int64" com pd.NA
    b["passivos_existentes"] = b["passivos_existentes"].astype("Int64")
    b.loc[:5, "passivos_existentes"] = pd.NA
    return criar_variaveis(b)


def test_xgb_ponta_a_ponta():
    base = _base()
    grade = buscar_parametros(base)
    assert len(grade) == np.prod([len(v) for v in GRADE.values()])
    melhor = grade.iloc[0]
    params = {k: int(melhor[k]) for k in GRADE}
    m = treinar_final(base, params, int(melhor["n_arvores"]))
    p = m.predict_proba(_para_modelo(base))[:, 1]
    assert ((p >= 0) & (p <= 1)).all() and m.calibrador is not None

    mot = motivos(m, _para_modelo(base.head(3)))
    assert len(mot) == 3
    for lista in mot:
        assert all(x["variavel"] != "pais" for x in lista)
        assert all(x["efeito"] in ("aumenta_risco", "reduz_risco") for x in lista)
        pesos = [x["peso"] for x in lista]
        assert pesos == sorted(pesos, reverse=True)


def test_xgb_completo():
    from src.modelos.xgb import treinar_final_completo
    base = _base()
    m = treinar_final_completo(base, {"max_depth": 3, "min_child_weight": 5, "reg_lambda": 1}, 50)
    p = m.predict_proba(_para_modelo(base))[:, 1]
    assert ((p >= 0) & (p <= 1)).all() and m.calibrador is not None